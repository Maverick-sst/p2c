"""Print read-only disk usage for the root volume."""
import shutil

disk = shutil.disk_usage("/")
total = disk.total / (1024 ** 3)
used = disk.used / (1024 ** 3)
free = disk.free / (1024 ** 3)
print(f"Total storage: {total:.1f} GB")
print(f"Used storage: {used:.1f} GB")
print(f"Free storage: {free:.1f} GB")
print(f"Usage: {(used / total * 100):.0f}%")
