from unittest.mock import patch
import pytest
import os
from datetime import datetime

from lwe.core.util import (
    introspect_commands,
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
    get_class_method,
    output_response,
    write_temp_file,
    get_package_root,
    NoneAttrs,
    introspect_command_actions,
    dict_to_pretty_json,
    get_file_directory,
    snake_to_class,
    remove_and_create_dir,
    create_file,
    current_datetime,
    filepath_replacements,
    get_environment_variable,
    get_environment_variable_list,
    split_on_delimiter,
    remove_prefix,
    # get_ansible_module_doc,
    # ansible_doc_to_markdown,
    is_valid_url,
    list_to_markdown_list,
    clean_directory,
    transform_messages_to_chat_messages,
    extract_preset_configuration_from_request_overrides,
    get_preset_name,
)
import lwe.core.constants as constants
from lwe.core.error import NoInputError
from lwe.core.config import Config


class TestClass:
    class DummyClass:
        def command_command1(self):
            pass

        def command_command2(self):
            pass

    def test_introspect_commands(self):
        result = introspect_commands(self.DummyClass)
        assert result == ["command1", "command2"]

    def test_command_with_leader(self):
        result = command_with_leader("test_command")
        assert result == f"{constants.COMMAND_LEADER}test_command"

    def test_merge_dicts(self):
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        expected = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        assert merge_dicts(dict1, dict2) == expected

    def test_underscore_to_dash(self):
        assert underscore_to_dash("some_text") == "some-text"

    def test_dash_to_underscore(self):
        assert dash_to_underscore("some-text") == "some_text"

    def test_list_to_completion_hash(self):
        assert list_to_completion_hash([1, 2, 3]) == {"1": None, "2": None, "3": None}

    def test_float_range_to_completions(self):
        assert float_range_to_completions(0, 1) == {
            "0.0": None,
            "0.1": None,
            "0.2": None,
            "0.3": None,
            "0.4": None,
            "0.5": None,
            "0.6": None,
            "0.7": None,
            "0.8": None,
            "0.9": None,
            "1.0": None,
        }

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
        with patch("pyperclip.paste", return_value="test_value"):
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
            {"role": "system", "message": "Hello"},
            {"role": "user", "message": "Hi"},
            {"role": "assistant", "message": "How can I help you?"},
        ]
        conversation_parts = conversation_from_messages(messages)
        assert conversation_parts[0]["role"] == "system"
        assert conversation_parts[0]["display_role"] == "**System**:"
        assert conversation_parts[0]["message"] == "Hello"
        assert conversation_parts[1]["role"] == "user"
        assert conversation_parts[1]["display_role"] == "**User**:"
        assert conversation_parts[1]["message"] == "Hi"
        assert conversation_parts[2]["role"] == "assistant"
        assert conversation_parts[2]["display_role"] == "**Assistant**:"
        assert conversation_parts[2]["message"] == "How can I help you?"

    def test_parse_shell_input(self):
        with pytest.raises(EOFError):
            parse_shell_input("/exit")
        with pytest.raises(EOFError):
            parse_shell_input("/quit")
        with pytest.raises(NoInputError):
            parse_shell_input("")
        assert parse_shell_input("?") == ("help", "")
        assert parse_shell_input("Hello") == (constants.DEFAULT_COMMAND, "Hello")
        assert parse_shell_input("/command argument") == ("command", "argument")

    class SampleClass:
        def sample_method(self):
            pass

    def test_get_class_method(self):
        method = get_class_method(self.SampleClass, "sample_method")
        assert method == self.SampleClass.sample_method

    @patch("lwe.core.util.print_markdown")
    def test_output_response_message(self, mock_print_markdown):
        output_response("Test message")
        mock_print_markdown.assert_called_once_with("Test message")

    @patch("lwe.core.util.print_status_message")
    def test_output_response_success(self, mock_print_status_message):
        output_response((True, None, "Success message"))
        mock_print_status_message.assert_called_once_with(True, "Success message")

    @patch("lwe.core.util.print_status_message")
    def test_output_response_failure(self, mock_print_status_message):
        output_response((False, None, "Failure message"))
        mock_print_status_message.assert_called_once_with(False, "Failure message")

    def test_write_temp_file(self):
        input_data = "test content"
        temp_path = write_temp_file(input_data=input_data, suffix="txt")
        with open(temp_path, "r") as f:
            content = f.read()
        assert content == input_data
        os.remove(temp_path)

    def test_get_package_root(self):
        config = Config(profile="test")
        package_root = get_package_root(config)
        assert package_root.endswith("lwe")

    def test_NoneAttrs(self):
        none_attrs = NoneAttrs()
        assert none_attrs.any_attribute is None

    def test_introspect_command_actions(self):
        class DummyClass:
            def action_command1_action1(self):
                pass

            def action_command1_action2(self):
                pass

            def action_command2_action3(self):
                pass

        result = introspect_command_actions(DummyClass, "command1")
        assert result == ["action1", "action2"]

    def test_dict_to_pretty_json(self):
        dict_obj = {"key": "value"}
        result = dict_to_pretty_json(dict_obj)
        assert result == '```json\n{\n    "key": "value"\n}\n```'

    def test_get_file_directory(self):
        result = get_file_directory()
        assert os.path.isdir(result)

    def test_snake_to_class(self):
        result = snake_to_class("some_class")
        assert result == "SomeClass"

    def test_remove_and_create_dir(self, tmpdir):
        directory_path = os.path.join(tmpdir, "test_dir")
        remove_and_create_dir(directory_path)
        assert os.path.isdir(directory_path)
        os.rmdir(directory_path)

    def test_create_file(self, tmpdir):
        directory = tmpdir
        filename = "test_file.txt"
        content = "test content"
        filepath = create_file(directory, filename, content)
        assert filepath == os.path.join(directory, filename)
        assert os.path.isfile(filepath)
        with open(os.path.join(directory, filename), "r") as f:
            assert f.read() == content
        os.remove(filepath)

    def test_current_datetime(self):
        result = current_datetime()
        assert isinstance(result, datetime)

    def test_filepath_replacements(self):
        config = Config(profile="test")
        filepath = "$HOME/$CONFIG_DIR/$DATA_DIR/$PROFILE"
        result = filepath_replacements(filepath, config)
        assert result == f"{os.path.expanduser('~user')}/{config.config_dir}/{config.data_dir}/test"

    def test_get_environment_variable(self, monkeypatch):
        monkeypatch.setenv("LWE_TEST_VAR", "test_value")
        assert get_environment_variable("test_var") == "test_value"
        assert get_environment_variable("non_existent_var") is None
        assert (
            get_environment_variable("non_existent_var", default="default_value") == "default_value"
        )

    def test_get_environment_variable_list(self, monkeypatch):
        monkeypatch.setenv("LWE_TEST_VAR", "value1:value2:value3")
        assert get_environment_variable_list("test_var") == ["value1", "value2", "value3"]

    def test_split_on_delimiter(self):
        assert split_on_delimiter("value1, value2, value3") == ["value1", "value2", "value3"]
        assert split_on_delimiter("value1:value2:value3", delimiter=":") == [
            "value1",
            "value2",
            "value3",
        ]

    def test_remove_prefix(self):
        assert remove_prefix("prefix_text", "prefix_") == "text"

    def test_is_valid_url(self):
        assert is_valid_url("http://example.com")
        assert not is_valid_url("invalid_url")

    def test_list_to_markdown_list(self):
        assert (
            list_to_markdown_list(["value1", "value2", "value3"])
            == "  * value1\n  * value2\n  * value3"
        )
        assert (
            list_to_markdown_list(["value1", "value2", "value3"], indent=4)
            == "    * value1\n    * value2\n    * value3"
        )

    def test_clean_directory(self, tmpdir):
        filepath = os.path.join(tmpdir, "test_file.txt")
        filepath2 = os.path.join(tmpdir, "test_file2.txt")
        with open(filepath, "w") as f:
            f.write("test content")
        with open(filepath2, "w") as f:
            f.write("test content2")
        clean_directory(tmpdir)
        assert not os.path.isfile(filepath)
        assert not os.path.isfile(filepath2)

    def test_transform_messages_to_chat_messages(self):

        messages = [
            {"role": "user", "message": "Hello", "message_type": "content"},
            {"role": "assistant", "message": "Hi", "message_type": "content"},
            {
                "role": "assistant",
                "message": [
                    {"name": "tool_name", "args": {}, "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"}
                ],
                "message_type": "tool_call",
            },
            {
                "role": "tool",
                "message": {"word": "foo", "repeats": 2},
                "message_type": "tool_response",
                "message_metadata": {"name": "tool_name", "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"},
            },
        ]
        result = transform_messages_to_chat_messages(messages)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi"
        assert result[2]["role"] == "assistant"
        assert result[2]["content"] == ""
        assert result[2]["tool_calls"] == [
            {
                "name": "tool_name",
                "args": {},
                "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
            }
        ]
        assert result[3]["role"] == "tool"
        assert result[3]["content"] == '{"word": "foo", "repeats": 2}'
        assert result[3]["name"] == "tool_name"
        assert result[3]["tool_call_id"] == "call_4MqKEs9ZWh0qTh0xCFcb9IOI"

    def test_extract_preset_configuration_from_request_overrides(self):
        request_overrides = {
            "preset": "preset1",
            "preset_overrides": {"key": "value"},
            "activate_preset": True,
        }
        success, response, _user_message = extract_preset_configuration_from_request_overrides(
            request_overrides
        )
        assert success
        assert response[0] == "preset1"
        assert response[1] == {"key": "value"}
        assert response[2] is True

    def test_get_preset_name(self):
        preset = ({"name": "preset1"}, {"key": "value"})
        assert get_preset_name(preset) == "preset1"
        assert get_preset_name(None) is None
