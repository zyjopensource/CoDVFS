# -*- coding: utf-8 -*-
import subprocess

def set_app_clocks(mem_mhz: int, graphics_mhz: int, rawfile=None):
    # 设置 V100 应用频率（显存固定 810MHz，图形频率按需）
    cmd = f"sudo nvidia-smi --applications-clocks={mem_mhz},{graphics_mhz}"
    _run(cmd, rawfile)

def reset_app_clocks(rawfile=None):
    # 恢复默认频率
    cmd = "sudo nvidia-smi -rac"
    _run(cmd, rawfile)

def _run(cmd: str, rawfile=None):
    p = subprocess.Popen(cmd, stdout=(rawfile or subprocess.PIPE),
                             stderr=(rawfile or subprocess.STDOUT), shell=True)
    p.wait()
