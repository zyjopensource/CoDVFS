# -*- coding: utf-8 -*-
import os
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

from codvfs import config
from codvfs.control import cpu as cpu_ctl
from codvfs.control import gpu as gpu_ctl
from codvfs.monitor.power import DualPDUPowerLogger
from codvfs.workload.hpl import hplai_command, hpl_command, parse_hpl_output_lines
from codvfs.optim import bayes

def bayes_search(app: str = "hplai", iterations: int = 32, quicktest: bool = False):
    """
    app: 'hplai' 或 'hpl'
    iterations: 贝叶斯优化迭代次数
    quicktest: True 时跳过实际跑任务，用于打通流程
    """
    OUTPUT = config.OUTPUT_DIR
    OUTPUT.mkdir(parents=True, exist_ok=True)

    resultfilename = f"bayes_{app}.csv"
    rawfilename = f"bayes_{app}_raw.out"
    timingStartswith = config.HPL_TIMING_LINE_PREFIX

    powerfiles = [f"power_bayes_{app}_0.out", f"power_bayes_{app}_1.out"]
    pfile0 = OUTPUT / powerfiles[0]
    pfile1 = OUTPUT / powerfiles[1]

    print("Starting CoDVFS..")
    start = time.time()
    rawfile = open(OUTPUT / rawfilename, "w")
    resultfile = open(OUTPUT / resultfilename, "w")
    resultfile.write("cpufreq(GHz),gpufreq(MHz),Gflops,power(W),GflopsPerW,exetime(s),N,NB\n")

    # 启动功率监测（持续记录到 power_bayes_{app}_*.out）
    power_logger = DualPDUPowerLogger(
        ip0=config.PDU_IPS[0], ip1=config.PDU_IPS[1],
        community=config.SNMP_COMMUNITY, oid=config.POWER_OID,
        outfile0=pfile0, outfile1=pfile1,
        interval_sec=config.POWER_SAMPLING_INTERVAL
    )
    power_logger.start()

    # CPU governor -> userspace
    rawfile.write("Setting cpufreq governor to userspace.\n"); rawfile.flush()
    cpu_ctl.set_userspace_governor(rawfile)

    # 预热一次
    if not quicktest:
        print("Warm-up run..")
        appcmd = hplai_command(config.HPL_N, config.HPL_NB) if app == "hplai" else hpl_command(config.HPL_N, config.HPL_NB)
        apprun = subprocess.Popen(appcmd, stdout=rawfile, stderr=rawfile, shell=True)
        apprun.wait(); rawfile.flush()

    # 频率边界（GHz）
    freq_bounds = np.array([[config.CPU_FREQ_MIN_GHZ, config.CPU_FREQ_MAX_GHZ],
                            [config.GPU_FREQ_MIN_GHZ, config.GPU_FREQ_MAX_GHZ]])

    # 合法频点白名单（CPU 0.1GHz 步长；GPU 15MHz 等价）
    freqlists = (config.CPU_FREQS_GHZ, config.GPU_FREQS_GHZ)

    # 初始点（四角）
    init = [(config.CPU_FREQ_MAX_GHZ, config.GPU_FREQ_MAX_GHZ),
            (config.CPU_FREQ_MAX_GHZ, config.GPU_FREQ_MIN_GHZ),
            (config.CPU_FREQ_MIN_GHZ, config.GPU_FREQ_MAX_GHZ),
            (config.CPU_FREQ_MIN_GHZ, config.GPU_FREQ_MIN_GHZ)]

    # 内部评估函数：设置频点 -> 运行 workload -> 解析输出 + 区间平均功率 -> 返回目标（Gflops/W）
    def sample_loss(freqs_ghz: np.ndarray) -> float:
        cpu_ghz = float(freqs_ghz[0])
        gpu_ghz = float(freqs_ghz[1])
        gpu_mhz = int(round(gpu_ghz * 1000))

        if quicktest:
            # 快速连通性测试：返回一个稳定的假值（例如线性插值）
            val = (cpu_ghz - config.CPU_FREQ_MIN_GHZ) / (config.CPU_FREQ_MAX_GHZ - config.CPU_FREQ_MIN_GHZ + 1e-9) \
                  + (gpu_ghz - config.GPU_FREQ_MIN_GHZ) / (config.GPU_FREQ_MAX_GHZ - config.GPU_FREQ_MIN_GHZ + 1e-9)
            print(f"[QuickTest] CPU {cpu_ghz:.1f} GHz, GPU {gpu_mhz} MHz -> {val:.3f}")
            return float(val)

        # 1) 设频
        cpu_ctl.set_cpu_freq_ghz(cpu_ghz, rawfile)
        gpu_ctl.set_app_clocks(config.GPU_MEM_APP_CLOCK_MHZ, gpu_mhz, rawfile)
        rawfile.flush()

        # 2) 跑 workload，抓 stdout 到临时文件，便于解析时间戳与 Gflops
        temp_out = config.OUTPUT_DIR / "bayes_temp.out"
        if app == "hplai":
            appcmd = hplai_command(config.HPL_N, config.HPL_NB)
        else:
            appcmd = hpl_command(config.HPL_N, config.HPL_NB)

        with open(temp_out, "w") as tmpf:
            apprun = subprocess.Popen(appcmd, stdout=tmpf, stderr=tmpf, shell=True)
            apprun.wait()
            # 稍等片刻，确保功率日志落盘更完整
            time.sleep(3)

        with open(temp_out, "r") as tmpf:
            lines = tmpf.readlines()

        # 3) 解析性能与时间窗口
        Gflops, exetime, lasttime, thistime = parse_hpl_output_lines(app, lines)
        if any(x is None or x == -1 for x in (Gflops, exetime, lasttime, thistime)):
            print("Warning: failed to parse output; returning 0.")
            GflopsPerW = 0.0
            power = float("nan")
        else:
            # 4) 读取两路功率日志，按 [lasttime, thistime] 区间取平均后求和
            power = _compute_interval_avg_power(pfile0, pfile1, lasttime, thistime)
            GflopsPerW = float(Gflops) / float(power) if (power and power == power and power > 0) else 0.0

        # 5) 写入结果
        resultfile.write(f"{cpu_ghz:.1f},{gpu_mhz:d},{Gflops:.0f},{power:.1f},{GflopsPerW:.2f},{exetime:.2f},{config.HPL_N:d},{config.HPL_NB:d}\n")
        resultfile.flush()
        print(f"Test CPU {cpu_ghz:.1f} GHz & GPU {gpu_mhz} MHz -> {GflopsPerW:.2f} Gflops/W")
        return GflopsPerW

    try:
        print("Bayesian optimization start..")
        xp, yp = bayes.bayesian_optimisation(
            n_iters=iterations,
            sample_loss=sample_loss,
            bounds=freq_bounds,
            x0=init,
            n_pre_samples=0,
            gp_params=None,
            random_search=False,
            alpha=1e-5,
            epsilon=1e-7,
            paras=(config.CPU_FREQS_GHZ, config.GPU_FREQS_GHZ)
        )
    finally:
        print("Experiment finished. Re-setting cpu/gpu frequency.")
        cpu_ctl.set_ondemand_governor(rawfile)
        gpu_ctl.reset_app_clocks(rawfile)
        power_logger.stop()
        rawfile.close()
        resultfile.close()
        end = time.time()
        print(f"Finished in {end - start:.0f} seconds.")

def _compute_interval_avg_power(pfile0: Path, pfile1: Path, t_start, t_end) -> float:
    """
    读取两路 PDU 日志，截取 [t_start, t_end] 区间内的功率样本，做平均后求和。
    文件格式：'YYYY-mm-dd HH:MM:SS.ffffff,<powerW>'
    """
    def read_file(pfile: Path):
        if not pfile.exists():
            return []
        with pfile.open("r") as f:
            lines = f.readlines()
        vals = []
        # 用简单的跳读法加速：因为有时间窗，可按需过滤
        for line in lines:
            parts = line.strip().split(",")
            if len(parts) != 2:
                continue
            try:
                ts = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S.%f")
                if ts < t_start:
                    continue
                if ts > t_end:
                    break
                val = float(parts[1])
                vals.append(val)
            except Exception:
                continue
        return vals

    vals0 = read_file(pfile0)
    vals1 = read_file(pfile1)
    avg0 = sum(vals0) / len(vals0) if vals0 else 0.0
    avg1 = sum(vals1) / len(vals1) if vals1 else 0.0
    return avg0 + avg1
