# -*- coding: utf-8 -*-
import os
from pathlib import Path

# ---- 路径与输出 ----
OUTPUT_DIR = Path(os.getenv("CODVFS_OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- DGX V100 服务器与功率计配置 ----
# 两个 PDU（功率计）IP
PDU_IPS = ["192.168.242.38", "192.168.242.39"]
SNMP_COMMUNITY = "public"
POWER_OID = "1.3.6.1.4.1.23273.4.4.0"
# 采样周期（秒）
POWER_SAMPLING_INTERVAL = 0.5

# ---- CPU/GPU 频率范围（GHz） ----
CPU_FREQ_MIN_GHZ = 1.2
CPU_FREQ_MAX_GHZ = 2.2
GPU_FREQ_MIN_GHZ = 0.135
GPU_FREQ_MAX_GHZ = 1.440
GPU_MEM_APP_CLOCK_MHZ = 810  # V100 application clocks 的固定显存频率

# 生成 CPU 合法频点（0.1GHz 递增）
CPU_FREQS_GHZ = [x / 10.0 for x in range(int(CPU_FREQ_MIN_GHZ * 10), int(CPU_FREQ_MAX_GHZ * 10) + 1)]
# 生成 GPU 合法频点（按 15MHz 间隔等效的 0.007/0.008GHz 交替）
def build_gpu_freqs_ghz():
    f = GPU_FREQ_MIN_GHZ
    seven = True
    freqs = [f]
    while f <= GPU_FREQ_MAX_GHZ:
        f += 0.007 if seven else 0.008
        seven = not seven
        if f <= GPU_FREQ_MAX_GHZ:
            freqs.append(round(f, 3))
    return freqs
GPU_FREQS_GHZ = build_gpu_freqs_ghz()

# ---- HPL-AI/HPL 输出解析相关 ----
HPL_TIMING_LINE_PREFIX = "2021-12-"
HPLAI_RESULT_LINE_PREFIX = "HPL_AI"
HPL_RESULT_LINE_PREFIX = "WR03L2L2"

# HPL-AI 参数
HPL_N = 204800
HPL_NB = 896

# NGC HPL-AI 镜像
HPLAI_CONTAINER_IMAGE = os.getenv("HPLAI_IMAGE", "nvcr.io/nvidia/hpc-benchmarks:21.4-hpl")
HPL_CONTAINER_IMAGE   = os.getenv("HPL_IMAGE",   "nvcr.io/nvidia/hpc-benchmarks:21.4-hpl")
HPCG_CONTAINER_IMAGE   = os.getenv("HPCG_IMAGE",   "nvcr.io/nvidia/hpc-benchmarks:21.4-hpcg")
DOCKER_MOUNT_OUTPUT = True
