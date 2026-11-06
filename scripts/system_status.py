"""Print a concise, read-only system summary."""
import platform
import os
import psutil

print(f"macOS host: {platform.node()}")
print(f"Operating system: {platform.system()} {platform.release()}")
print(f"Architecture: {platform.machine()}")
print(f"CPU cores: {os.cpu_count() or 'unknown'}")
memory = psutil.virtual_memory()
print(f"Memory used: {memory.percent:.0f}%")
print(f"Memory available: {memory.available / (1024 ** 3):.1f} GB")
print(f"CPU utilization: {psutil.cpu_percent(interval=0.5):.0f}%")
