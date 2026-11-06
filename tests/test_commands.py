from app.commands import COMMANDS, get_command


def test_only_expected_keys_are_registered():
    assert set(COMMANDS) == {"1", "2", "3"}


def test_unknown_or_shell_like_input_is_rejected():
    assert get_command("9") is None
    assert get_command("1; rm -rf /") is None
    assert get_command("whoami") is None


def test_registered_scripts_are_inside_scripts_directory():
    for command in COMMANDS.values():
        assert command.script.parent.name == "scripts"
        assert command.script.suffix == ".py"
