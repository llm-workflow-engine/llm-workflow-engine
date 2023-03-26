import pytest
import pyperclip
import os

from chatgpt_wrapper.core.util import (introspect_commands,
                                       command_with_leader,
                                       merge_dicts,
                                       underscore_to_dash,
                                       dash_to_underscore,
                                       list_to_completion_hash,
                                       float_range_to_completions,
                                       validate_int,
                                       validate_float,
                                       validate_str,
                                       paste_from_clipboard,
                                       print_status_message,
                                       print_markdown,
                                       parse_conversation_ids,
                                       conversation_from_messages,
                                       parse_shell_input,
                                       get_class_command_method,
                                       output_response,
                                       open_temp_file,
                                       get_package_root,
                                       )
import chatgpt_wrapper.core.constants as constants
from chatgpt_wrapper.core.error import NoInputError, LegacyCommandLeaderError
from chatgpt_wrapper.core.config import Config

class TestClass:
    class DummyClass:
        def do_command1(self):
            pass

        def do_command2(self):
            pass

    def test_introspect_commands(self):
        result = introspect_commands(self.DummyClass)
        assert result == ["command1", "command2"]

    def test_command_with_leader(self):
        result = command_with_leader("test_command")
        assert result == f"{constants.COMMAND_LEADER}test_command"

    def test_merge_dicts(self):
        dict1 = {'a': 1, 'b': {'c': 2}}
        dict2 = {'b': {'d': 3}, 'e': 4}
        expected = {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}
        assert merge_dicts(dict1, dict2) == expected

    def test_underscore_to_dash(self):
        assert underscore_to_dash("some_text") == "some-text"

    def test_dash_to_underscore(self):
        assert dash_to_underscore("some-text") == "some_text"

    def test_list_to_completion_hash(self):
        assert list_to_completion_hash([1, 2, 3]) == {'1': None, '2': None, '3': None}

    def test_float_range_to_completions(self):
        assert float_range_to_completions(0, 1) == {'0.0': None, '0.1': None, '0.2': None, '0.3': None, '0.4': None, '0.5': None, '0.6': None, '0.7': None, '0.8': None, '0.9': None, '1.0': None}

    def test_validate_int(self):
        assert validate_int(5) == 5
        assert validate_int("5") == 5
        assert validate_int("5.5") is False
        assert validate_int("a") is False
        assert validate_int(5, min=3, max=7) == 5
        assert validate_int(5, min=6) is False
        assert validate_int(5, max=4) is False

    def test_validate_float(self):
        assert validate_float(5.0) == 5.0
        assert validate_float("5.0") == 5.0
        assert validate_float("5.5") == 5.5
        assert validate_float("a") is False
        assert validate_float(5.5, min=3.0, max=7.0) == 5.5
        assert validate_float(5.5, min=6.0) is False
        assert validate_float(5.5, max=4.0) is False

    def test_validate_str(self):
        assert validate_str("test") == "test"
        assert validate_str(123) == "123"
        assert validate_str("test", min=3, max=5) == "test"
        assert validate_str("test", min=5) is False
        assert validate_str("test", max=3) is False

    def test_paste_from_clipboard(self):
        pyperclip.copy("test_value")
        assert paste_from_clipboard() == "test_value"

    def test_print_status_message(self, capsys):
        print_status_message(True, "Success message")
        captured = capsys.readouterr()
        assert "Success message" in captured.out

        print_status_message(False, "Failure message")
        captured = capsys.readouterr()
        assert "Failure message" in captured.out

    def test_print_markdown(self, capsys):
        print_markdown("# Heading")
        captured = capsys.readouterr()
        assert "Heading" in captured.out

    def test_parse_conversation_ids(self):
        assert parse_conversation_ids("1,2,3") == [1, 2, 3]
        assert parse_conversation_ids("1-3") == [1, 2, 3]
        assert parse_conversation_ids("1,2-4") == [1, 2, 3, 4]
        assert parse_conversation_ids("1, 2-4") == [1, 2, 3, 4]
        assert parse_conversation_ids("1 - 3") == [1, 2, 3]
        assert parse_conversation_ids("1, 2, 3-5, 7") == [1, 2, 3, 4, 5, 7]
        assert "Error: Invalid range" in parse_conversation_ids("a")
        assert "Error: Invalid range" in parse_conversation_ids("1-a")
        assert "Error: Invalid range" in parse_conversation_ids("1-2-3")

    def test_conversation_from_messages(self):
        messages = [
            {'role': 'system', 'message': 'Hello'},
            {'role': 'user', 'message': 'Hi'},
            {'role': 'assistant', 'message': 'How can I help you?'}
        ]
        content = conversation_from_messages(messages)
        assert "**System**:" in content
        assert "**User**:" in content
        assert "**Assistant**:" in content
        assert "Hello" in content
        assert "Hi" in content
        assert "How can I help you?" in content

    def test_parse_shell_input(self):
        with pytest.raises(EOFError):
            parse_shell_input("/exit")
        with pytest.raises(EOFError):
            parse_shell_input("/quit")
        with pytest.raises(LegacyCommandLeaderError):
            parse_shell_input("!exit")
        with pytest.raises(NoInputError):
            parse_shell_input("")
        assert parse_shell_input("?") == ('help', '')
        assert parse_shell_input("Hello") == (constants.DEFAULT_COMMAND, 'Hello')
        assert parse_shell_input("/command argument") == ('command', 'argument')

    class SampleClass:
        def sample_method(self):
            pass

    def test_get_class_command_method(self):
        method = get_class_command_method(self.SampleClass, 'sample_method')
        assert method == self.SampleClass.sample_method

    def test_output_response(self, capsys):
        output_response("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

        output_response((True, None, "Success message"))
        captured = capsys.readouterr()
        assert "Success message" in captured.out

        output_response((False, None, "Failure message"))
        captured = capsys.readouterr()
        assert "Failure message" in captured.out

    def test_open_temp_file(self):
        input_data = "test content"
        temp_path = open_temp_file(input_data=input_data, suffix='txt')
        with open(temp_path, 'r') as f:
            content = f.read()
        assert content == input_data
        os.remove(temp_path)

    def test_get_package_root(self):
        config = Config(profile='test')
        package_root = get_package_root(config)
        assert package_root.endswith("chatgpt_wrapper")
