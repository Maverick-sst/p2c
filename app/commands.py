"""Explicit allowlist of local tasks. Never accept a command string from a caller."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


@dataclass(frozen=True)
class Command:
    key: str
    label: str
    script: Path


COMMANDS: dict[str, Command] = {
    "1": Command("1", "system summary", SCRIPTS_DIR / "system_status.py"),
    "2": Command("2", "disk usage", SCRIPTS_DIR / "disk_status.py"),
    "3": Command("3", "network summary", SCRIPTS_DIR / "network_status.py"),
}


def get_command(key: str) -> Command | None:
    return COMMANDS.get(key)
