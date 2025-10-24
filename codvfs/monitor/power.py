# -*- coding: utf-8 -*-
import time
import threading
from datetime import datetime
from pathlib import Path
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.entity import engine as snmp_engine

class PowerMeterClient:
    def __init__(self, ip: str, community: str, oid: str):
        self.ip = ip
        self.community = community
        self.oid = oid
        self.snmpEngine = snmp_engine.SnmpEngine()
        self.cg = cmdgen.CommandGenerator(self.snmpEngine)

    def read_watts(self) -> float:
        errI, errS, errId, varBinds = self.cg.getCmd(
            cmdgen.CommunityData('pudinfo', self.community, 0),
            cmdgen.UdpTransportTarget((self.ip, 161)),
            self.oid
        )
        return float(varBinds[0][1]) / 10.0

class DualPDUPowerLogger:
    """
    每 0.5s 记录一行："YYYY-mm-dd HH:MM:SS.ffffff,<powerW>"
    """
    def __init__(self, ip0: str, ip1: str, community: str, oid: str,
                 outfile0: Path, outfile1: Path, interval_sec: float = 0.5):
        self.client0 = PowerMeterClient(ip0, community, oid)
        self.client1 = PowerMeterClient(ip1, community, oid)
        self.outfile0 = Path(outfile0)
        self.outfile1 = Path(outfile1)
        self.interval = interval_sec
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self.outfile0.parent.mkdir(parents=True, exist_ok=True)
        self.outfile1.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        # 以追加模式持续写入
        with self.outfile0.open("a") as f0, self.outfile1.open("a") as f1:
            while not self._stop.is_set():
                t0 = time.time()
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                try:
                    p0 = self.client0.read_watts()
                except Exception:
                    p0 = float("nan")
                try:
                    p1 = self.client1.read_watts()
                except Exception:
                    p1 = float("nan")
                f0.write(f"{ts},{p0:.1f}\n")
                f1.write(f"{ts},{p1:.1f}\n")
                f0.flush()
                f1.flush()
                # 固定采样周期
                elapsed = time.time() - t0
                time.sleep(max(0.0, self.interval - elapsed))
