"""Server-owned command registry. Never accept executable paths from clients."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


@dataclass(frozen=True)
class Command:
    id: str
    key: str
    label: str
    description: str
    script: Path
    timeout_seconds: int = 12
    risk: str = "read_only"


COMMANDS = {
    "system.status": Command("system.status", "01", "System status", "CPU, memory and macOS summary", SCRIPTS / "system_status.py"),
    "system.disk": Command("system.disk", "02", "Disk usage", "Storage capacity and free space", SCRIPTS / "disk_status.py"),
    "system.network": Command("system.network", "03", "Network status", "Local network interfaces", SCRIPTS / "network_status.py"),
}
KEYS = {command.key: command.id for command in COMMANDS.values()}


def get_command(command_id):
    return COMMANDS.get(command_id)


def get_command_by_key(key):
    command_id = KEYS.get(key)
    return COMMANDS.get(command_id) if command_id else None


def public_commands():
    return [
        {"id": item.id, "key": item.key, "label": item.label,
         "description": item.description, "risk": item.risk,
         "enabled": True, "timeout_seconds": item.timeout_seconds}
        for item in COMMANDS.values()
    ]
