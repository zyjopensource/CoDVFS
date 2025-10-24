# -*- coding: utf-8 -*-
import subprocess

def set_userspace_governor(rawfile=None):
    cmd = "sudo cpupower frequency-set --governor userspace"
    run(cmd, rawfile)

def set_ondemand_governor(rawfile=None):
    cmd = "sudo cpupower frequency-set --governor ondemand"
    run(cmd, rawfile)

def set_cpu_freq_ghz(freq_ghz: float, rawfile=None):
    cmd = f"sudo cpupower --cpu all frequency-set --freq {freq_ghz:.1f}GHz"
    run(cmd, rawfile)

def run(cmd: str, rawfile=None):
    p = subprocess.Popen(cmd, stdout=(rawfile or subprocess.PIPE),
                             stderr=(rawfile or subprocess.STDOUT), shell=True)
    p.wait()
