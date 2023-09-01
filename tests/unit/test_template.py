import os
import pyperclip

from jinja2 import Environment, Template

from lwe.core.template import TemplateManager
import lwe.core.util as util
from ..base import test_config, template_manager  # noqa: F401


def make_template_file(template_manager, template_name, content=None):  # noqa: F811
    template_dir = template_manager.user_template_dirs[0]
    util.create_file(template_dir, template_name, content)
    template_manager.load_templates()


def remove_template_file(template_manager, template_name):  # noqa: F811
    template_dir = template_manager.user_template_dirs[0]
    os.remove(os.path.join(template_dir, template_name))


def test_init(template_manager):  # noqa: F811
    assert isinstance(template_manager, TemplateManager)
    assert len(template_manager.user_template_dirs) > 0
    assert len(template_manager.templates) > 0


def test_template_builtin_variables(template_manager):  # noqa: F811
    builtins = template_manager.template_builtin_variables()
    assert 'clipboard' in builtins
    assert callable(builtins['clipboard'])


def test_ensure_template(template_manager):  # noqa: F811
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


def test_extract_metadata_keys(template_manager):  # noqa: F811
    metadata = {
        'title': 'Test Title',
        'description': 'Test Description',
        'custom': 'Custom Value'
    }
    keys = ['title', 'custom']
    metadata, extracted_keys = template_manager.extract_metadata_keys(keys, metadata)
    assert metadata == {'description': 'Test Description'}
    assert extracted_keys == {'title': 'Test Title', 'custom': 'Custom Value'}


def test_extract_template_run_overrides(template_manager):  # noqa: F811
    metadata = {
        'description': 'Test Description',
        'request_overrides': {
            'title': 'Test Title',
            'option': 'value',
        },
        'custom': 'Custom Value'
    }
    metadata, overrides = template_manager.extract_template_run_overrides(metadata)
    assert metadata == {'custom': 'Custom Value'}
    assert overrides == {'request_overrides': {'title': 'Test Title', 'option': 'value'}}


def test_build_message_from_template(template_manager):  # noqa: F811
    template_name = "hello.md"
    template_content = """
---
request_overrides:
  title: Existent Template
---
Hello, {{ name }}
"""
    make_template_file(template_manager, template_name, template_content)
    message, overrides = template_manager.build_message_from_template(template_name, {'name': 'John Doe'})
    remove_template_file(template_manager, template_name)
    assert 'Hello, John Doe' in message
    assert overrides == {'request_overrides': {'title': 'Existent Template'}}


def test_process_template_builtin_variables(template_manager):  # noqa: F811
    pyperclip.copy("clipboard_text")
    variables = ['clipboard']
    substitutions = template_manager.process_template_builtin_variables("existent_template.md", variables)
    assert substitutions == {'clipboard': 'clipboard_text'}


def test_make_user_template_dirs(template_manager, tmpdir):  # noqa: F811
    template_manager.config.config_dir = str(tmpdir)
    template_manager.config.config_profile_dir = str(tmpdir)
    template_manager.make_user_template_dirs()
    for template_dir in template_manager.user_template_dirs:
        assert os.path.exists(template_dir)


def test_load_templates(template_manager):  # noqa: F811
    template_manager.load_templates()
    assert isinstance(template_manager.templates_env, Environment)
    assert isinstance(template_manager.templates, list)


def test_get_template_and_variables_found(template_manager):  # noqa: F811
    template_name = "test.md"
    template_content = "Test {{ some_variable }}"
    make_template_file(template_manager, template_name, template_content)
    template, variables = template_manager.get_template_and_variables(template_name)
    remove_template_file(template_manager, template_name)
    assert isinstance(template, Template)
    assert "some_variable" in variables


def test_get_template_and_variables_not_found(template_manager):  # noqa: F811
    template_name = "non_existent_template.md"
    template, variables = template_manager.get_template_and_variables(template_name)
    assert template is None
    assert variables is None
