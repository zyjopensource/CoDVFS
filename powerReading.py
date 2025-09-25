from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.entity import engine
import time
from datetime import datetime

snmpEngine = engine.SnmpEngine()
cg = cmdgen.CommandGenerator(snmpEngine)

def get_power(dev_ip):
    errI, errS, errId, varBinds = cg.getCmd(
        cmdgen.CommunityData('pudinfo', 'public', 0),
        cmdgen.UdpTransportTarget((dev_ip, 161)),
        '1.3.6.1.4.1.23273.4.4.0'
    )
    return float(varBinds[0][1]) / 10

while True:
    t0 = time.time()
    p0 = get_power('192.168.242.38')
    p1 = get_power('192.168.242.39')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print '%s,%.1f' % (ts, p0 + p1)
    time.sleep(max(0, 1 - (time.time()-t0)))