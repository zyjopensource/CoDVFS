# CoDVFS

A lightweight, modular framework for **Coordinated CPU–GPU DVFS** using **Bayesian Optimization**.
CoDVFS efficiently finds energy-efficient frequency pairs `(f_CPU, f_GPU)` for a target workload (e.g., HPL-MxP / HPL) while measuring **real server power** via external PDUs.

---

## Key Features

* **End-to-end pipeline**: set CPU/GPU frequencies → run workload → parse performance → align with power window → compute GFlops/W → update BO.
* **Modular design**:

  * `optim/` — Bayesian optimizer (Gaussian Processes).
  * `control/` — CPU & GPU frequency control (`cpupower`, `nvidia-smi`).
  * `monitor/` — dual-PDU SNMP power logging (0.5 s sampling).
  * `workload/` — workload commands & log parsers (HPL-MxP/HPL).
  * `config.py` — all tunables in one place.
* **Discrete frequency support**: CPU (0.1 GHz steps), GPU (V100 application clocks; ~15 MHz granularity).
* **Warm-up run** and **quick test** mode for dry runs.

---

## Repository Layout

```
codvfs/
  config.py
  main.py
  control/
    cpu.py
    gpu.py
  monitor/
    power.py
  optim/
    bayes.py
    search.py
  workload/
    hpl.py
output/              # results & logs
powerReading.py      # standalone power reading script
README.md
```

---

## Requirements

* **Hardware/OS**: Linux server with NVIDIA GPUs (e.g., DGX V100).
* **Privileges**: ability to run `sudo cpupower` and `sudo nvidia-smi --applications-clocks`.
* **Power meters**: two SNMP-enabled PDUs exposing total power at OID `1.3.6.1.4.1.23273.4.4.0` (adjust in `config.py` if different).
* **Python 3** with:

  ```bash
  pip install pysnmp numpy scikit-learn scipy
  ```

> If you use containers for HPL-MxP/HPL, set correct images/entrypoints in `config.py`.

---

## Configuration

Edit `codvfs/config.py`:

* **Power meters**: `PDU_IPS`, `SNMP_COMMUNITY`, `POWER_OID`, `POWER_SAMPLING_INTERVAL`.
* **Frequency ranges**: `CPU_FREQ_MIN_GHZ/CPU_FREQ_MAX_GHZ`, `GPU_FREQ_MIN_GHZ/GPU_FREQ_MAX_GHZ`.
* **Workloads**: `HPLAI_CONTAINER_IMAGE`, `HPL_CONTAINER_IMAGE`, and command templates in `workload/hpl.py`.
* **HPL-MxP params**: `HPL_N`, `HPL_NB` (default `204800` and `896`).

---

## Outputs

* `output/bayes_<app>.csv` — final results (one row per trial):

  ```
  cpufreq(GHz),gpufreq(MHz),Gflops,power(W),GflopsPerW,exetime(s),N,NB
  ```
* `output/bayes_<app>_raw.out` — raw console log.
* `output/power_bayes_<app>_0.out`, `output/power_bayes_<app>_1.out` — PDU logs:

  ```
  YYYY-mm-dd HH:MM:SS.ffffff,<powerW>
  ```

---

## How It Works (Brief)

1. Set CPU governor to `userspace`, apply `(f_CPU, f_GPU)` via `cpupower` & `nvidia-smi --applications-clocks`.
2. Run workload; capture stdout to parse:

   * **Performance**: GFlops, execution time.
   * **Timestamps**: `[lasttime, thistime]` window bracketing the run.
3. Read both PDU logs, average power over the window, sum two PDUs → server power.
4. Objective = **GFlops / W**; update Gaussian-Process model; propose next pair.
5. After search, restore CPU governor and reset GPU application clocks.

---

## Extending

* **Different workloads**: add a module in `workload/` and a parser returning `(Gflops, exetime, lasttime, thistime)`.
* **Different power meters**: implement a reader in `monitor/` and plug into `DualPDUPowerLogger`.
* **Different GPUs**: adjust frequency whitelist logic (GPU discrete steps) and `nvidia-smi` commands.

---

## Notes

* CoDVFS assumes voltage scales with selected frequency per platform defaults.
* Use at your own risk when changing system frequencies on production machines.

---

## License

MIT License.
