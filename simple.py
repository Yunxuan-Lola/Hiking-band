from bluepy.btle import Scanner
sc = Scanner()
dev = sc.scan(10.0)
for d in dev:
	printf(f"Dev {d.addr} ({d.addrType}), RSSI={d.rssi}")s