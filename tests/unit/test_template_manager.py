from unittest.mock import Mock, patch

import os
import yaml

from jinja2 import Environment, Template

from ..base import (
    make_template_file,
)

from lwe.core.template_manager import TemplateManager


def remove_template_file(template_manager, template_name):
    template_dir = template_manager.user_template_dirs[0]
    filepath = os.path.join(template_dir, template_name)
    os.remove(filepath)
    return filepath


def test_init(template_manager):
    assert isinstance(template_manager, TemplateManager)
    assert len(template_manager.user_template_dirs) > 0
    assert len(template_manager.templates) > 0


def test_template_builtin_variables(template_manager):
    builtins = template_manager.template_builtin_variables()
    assert "clipboard" in builtins
    assert callable(builtins["clipboard"])


def test_ensure_template(template_manager):
    template_name = "existent_template.md"
    make_template_file(template_manager, template_name)
    success, name, user_message = template_manager.ensure_template(template_name)
    remove_template_file(template_manager, template_name)
    assert success is True
    assert name == template_name
    assert "exists" in user_message

    template_name = "nonexistent_template.md"
    success, name, user_message = template_manager.ensure_template(template_name)
    assert success is False
    assert name == template_name
    assert "not found" in user_message


def test_get_raw_template(template_manager):
    template_name = "raw_template.md"
    content = "test {{ variable }}"
    make_template_file(template_manager, template_name, content)
    success, raw_content, user_message = template_manager.get_raw_template(template_name)
    remove_template_file(template_manager, template_name)
    assert success is True
    assert raw_content == content


def test_extract_metadata_keys(template_manager):
    metadata = {"title": "Test Title", "description": "Test Description", "custom": "Custom Value"}
    keys = ["title", "custom"]
    metadata, extracted_keys = template_manager.extract_metadata_keys(keys, metadata)
    assert metadata == {"description": "Test Description"}
    assert extracted_keys == {"title": "Test Title", "custom": "Custom Value"}


def test_extract_template_run_overrides(template_manager):
    metadata = {
        "description": "Test Description",
        "request_overrides": {
            "title": "Test Title",
            "option": "value",
        },
        "custom": "Custom Value",
    }
    metadata, overrides = template_manager.extract_template_run_overrides(metadata)
    assert metadata == {"custom": "Custom Value"}
    assert overrides == {"request_overrides": {"title": "Test Title", "option": "value"}}


def test_build_message_from_template(template_manager):
    template_name = "hello.md"
    template_content = """
---
request_overrides:
  title: Existent Template
---
Hello, {{ name }}
"""
    make_template_file(template_manager, template_name, template_content)
    message, overrides = template_manager.build_message_from_template(
        template_name, {"name": "John Doe"}
    )
    remove_template_file(template_manager, template_name)
    assert "Hello, John Doe" in message
    assert overrides == {"request_overrides": {"title": "Existent Template"}}


def test_process_template_builtin_variables(template_manager):
    variables = ["clipboard"]
    with patch("pyperclip.paste", return_value="test_value"):
        substitutions = template_manager.process_template_builtin_variables(
            "existent_template.md", variables
        )
        assert substitutions == {"clipboard": "test_value"}


def test_make_user_template_dirs(template_manager, tmpdir):
    template_manager.config.config_dir = str(tmpdir)
    template_manager.config.config_profile_dir = str(tmpdir)
    template_manager.make_user_template_dirs()
    for template_dir in template_manager.user_template_dirs:
        assert os.path.exists(template_dir)


def test_load_templates(template_manager):
    template_manager.load_templates()
    assert isinstance(template_manager.templates_env, Environment)
    assert isinstance(template_manager.templates, list)


def test_get_template_and_variables_found(template_manager):
    template_name = "test.md"
    template_content = "Test {{ some_variable }}"
    make_template_file(template_manager, template_name, template_content)
    template, variables = template_manager.get_template_and_variables(template_name)
    remove_template_file(template_manager, template_name)
    assert isinstance(template, Template)
    assert "some_variable" in variables


def test_get_template_and_variables_not_found(template_manager):
    template_name = "non_existent_template.md"
    template, variables = template_manager.get_template_and_variables(template_name)
    assert template is None
    assert variables is None


def test_get_template_variables_substitutions(template_manager):
    template_name = "non_existent_template.md"
    success, source, user_message = template_manager.get_template_source(template_name)
    assert success is False
    template_name = "existent_template.md"
    template, variables, substitutions = "test content", ["variable1"], {"variable2": "value2"}
    template_manager.get_template_and_variables = Mock(return_value=(template, variables))
    template_manager.process_template_builtin_variables = Mock(return_value=substitutions)
    make_template_file(template_manager, template_name)
    success, response, user_message = template_manager.get_template_variables_substitutions(
        template_name
    )
    remove_template_file(template_manager, template_name)
    assert success is True
    assert response == (template, variables, substitutions)
    assert "Loaded template substitutions" in user_message
    template_manager.get_template_and_variables.assert_called_once_with(template_name)
    template_manager.process_template_builtin_variables.assert_called_once_with(
        template_name, variables
    )


def test_render_template(template_manager):
    template_name = "existent_template.md"
    make_template_file(template_manager, template_name)
    success, message, user_message = template_manager.render_template(template_name)
    remove_template_file(template_manager, template_name)
    assert success is True
    assert "Rendered template" in user_message


def test_get_template_source(template_manager):
    template_name = "non_existent_template.md"
    success, source, user_message = template_manager.get_template_source(template_name)
    assert success is False
    template_name = "existent_template.md"
    front_matter = yaml.dump({"value": "one", "key": "two"})
    front_matter = f"---\n{front_matter}\n---\n"
    make_template_file(template_manager, template_name, content=front_matter)
    success, source, user_message = template_manager.get_template_source(template_name)
    remove_template_file(template_manager, template_name)
    assert success is True
    assert source["value"] == "one"
    assert "Loaded template source" in user_message


def test_get_template_editable_filepath(template_manager):
    success, filename, user_message = template_manager.get_template_editable_filepath("")
    assert success is False
    template_name = "missing_template.md"
    success, filename, user_message = template_manager.get_template_editable_filepath(template_name)
    assert success is True
    assert template_name in filename
    assert "can be edited" in user_message
    template_name = "existent_template.md"
    make_template_file(template_manager, template_name)
    success, filename, user_message = template_manager.get_template_editable_filepath(template_name)
    remove_template_file(template_manager, template_name)
    assert success is True
    assert template_name in filename
    assert "can be edited" in user_message
    template_name = "workflow-generator.md"
    success, filename, user_message = template_manager.get_template_editable_filepath(template_name)
    assert success is False
    assert "is a system template, and cannot be edited" in user_message


def test_copy_template(template_manager):
    old_name = "existent_template.md"
    new_name = "new_template.md"
    make_template_file(template_manager, old_name)
    success, new_filepath, user_message = template_manager.copy_template(old_name, new_name)
    remove_template_file(template_manager, old_name)
    remove_template_file(template_manager, new_name)
    assert success is True
    assert new_name in new_filepath
    assert "Copied template" in user_message


def test_template_can_delete(template_manager):
    success, filename, user_message = template_manager.template_can_delete("")
    assert success is False
    template_name = "missing_template.md"
    success, filename, user_message = template_manager.template_can_delete(template_name)
    assert success is False
    assert template_name in filename
    assert "does not exist" in user_message
    template_name = "existent_template.md"
    make_template_file(template_manager, template_name)
    success, filename, user_message = template_manager.template_can_delete(template_name)
    remove_template_file(template_manager, template_name)
    assert success is True
    assert "can be deleted" in user_message
    template_name = "workflow-generator.md"
    success, filename, user_message = template_manager.template_can_delete(template_name)
    assert success is False
    assert "is a system template, and cannot be deleted" in user_message


def test_template_delete(template_manager):
    template_name = "existent_template.md"
    filepath = make_template_file(template_manager, template_name)
    success, filename, user_message = template_manager.template_delete(filepath)
    assert success is True
    assert "Deleted" in user_message


def test_make_temp_template(template_manager):
    template_contents = "Hello, "
    basename, filepath = template_manager.make_temp_template(template_contents)
    assert os.path.exists(filepath)
    template_manager.remove_temp_template(basename)


def test_remove_temp_template(template_manager):
    template_contents = "Hello, "
    basename, filepath = template_manager.make_temp_template(template_contents)
    template_manager.remove_temp_template(basename)
    assert not os.path.exists(filepath)


def test_is_system_template(template_manager):
    system_template_filepath = os.path.join(
        template_manager.system_template_dirs[0], "existent_template.md"
    )
    assert template_manager.is_system_template(system_template_filepath) is True
    user_template_filepath = os.path.join(
        template_manager.user_template_dirs[0], "existent_template.md"
    )
    assert template_manager.is_system_template(user_template_filepath) is False
