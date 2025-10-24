# -*- coding: utf-8 -*-
import os
from pathlib import Path
from datetime import datetime, timedelta

from codvfs.config import (
    HPL_TIMING_LINE_PREFIX, HPLAI_RESULT_LINE_PREFIX, HPL_RESULT_LINE_PREFIX,
    DOCKER_MOUNT_OUTPUT, OUTPUT_DIR,
    HPLAI_CONTAINER_IMAGE, HPL_CONTAINER_IMAGE
)

def hplai_command(N: int, NB: int) -> str:
    """
    返回一个可执行的 shell 命令字符串，用于运行 HPL-AI（HPL-MxP）
    """
    mount = f"-v {OUTPUT_DIR.resolve()}:/out" if DOCKER_MOUNT_OUTPUT else ""
    # 注意：具体命令请参考镜像说明文档并按实际环境修改
    cmd = (
        f"docker run --rm --gpus all {mount} "
        f"{HPLAI_CONTAINER_IMAGE} "
        f"/opt/nvidia/hpl_mxp/xhpl_mxp -n {N} -b {NB}"
    )
    return cmd

def hpl_command(N: int, NB: int) -> str:
    """
    返回一个运行传统 HPL 的命令字符串（需要按镜像/脚本调整）
    """
    mount = f"-v {OUTPUT_DIR.resolve()}:/out" if DOCKER_MOUNT_OUTPUT else ""
    # 注意：具体命令请参考镜像说明文档并按实际环境修改
    cmd = (
        f"docker run --rm --gpus all {mount} "
        f"{HPL_CONTAINER_IMAGE} "
        f"/opt/nvidia/hpl/xhpl -n {N} -b {NB}"
    )
    return cmd

def parse_hpl_output_lines(app: str, lines):
    """
    解析 HPL/HPL-AI 的标准输出文本行，返回：
      (Gflops, exetime_s, lasttime, thistime)
    其中 lasttime 与 thistime 用于界定功率积分区间。
    按 HPL_TIMING_LINE_PREFIX 找时间，
    对 HPL-AI 结果行用 'HPL_AI' 开头，对 HPL 用 'WR03L2L2' 开头。
    """
    result_prefix = HPLAI_RESULT_LINE_PREFIX if app == "hplai" else HPL_RESULT_LINE_PREFIX
    lasttime = -1
    thistime = -1
    Gflops = None
    exetime = None

    for line in lines:
        if line.startswith(HPL_TIMING_LINE_PREFIX):
            lasttime = thistime
            # HPL/HPL-AI 输出时区不同，这里按原逻辑 +8 小时
            thistime = datetime.strptime(line.strip(), '%Y-%m-%d %H:%M:%S.%f') + timedelta(hours=8)
        if line.startswith(result_prefix):
            parts = line.split()
            if app == 'hplai':
                # 第 8 列是 Gflops，第 7 列是 exetime
                Gflops = float(parts[7])
                exetime = float(parts[6])
            else:
                # 第 7 列是 Gflops，第 6 列是 exetime
                Gflops = float(parts[6])
                exetime = float(parts[5])
        if "End of Tests" in line:
            # 结束标记，仅用于配合外层功率计算的区间截取
            pass

    return Gflops, exetime, lasttime, thistime
