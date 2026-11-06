"""Print local network interface summaries without probing external hosts."""
import psutil

for name, addresses in sorted(psutil.net_if_addrs().items()):
    ipv4 = [item.address for item in addresses if item.family.name == "AF_INET"]
    if ipv4:
        print(f"{name}: {', '.join(ipv4)}")
