from app.commands import COMMANDS, get_command, get_command_by_key


def test_registry_has_only_three_read_only_commands():
    assert set(COMMANDS) == {"system.status", "system.disk", "system.network"}
    assert all(command.risk == "read_only" for command in COMMANDS.values())


def test_dashboard_and_keypad_resolve_same_commands():
    for command in COMMANDS.values():
        assert get_command(command.id) == get_command_by_key(command.key)


def test_unknown_ids_and_codes_are_rejected():
    assert get_command("whoami") is None
    assert get_command("../scripts/system_status.py") is None
    assert get_command_by_key("1; rm -rf /") is None
    assert get_command_by_key("99") is None
