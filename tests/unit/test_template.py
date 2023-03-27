import os
import pytest
from unittest.mock import MagicMock

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.template import TemplateManager
import chatgpt_wrapper.core.util as util

TEST_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'test_templates')


@pytest.fixture
def test_config():
    config = Config()
    config.config_dir = TEST_TEMPLATE_DIR
    config.config_profile_dir = TEST_TEMPLATE_DIR
    return config


@pytest.fixture
def template_manager(test_config):
    return TemplateManager(config=test_config)


def test_init(template_manager):
    assert isinstance(template_manager, TemplateManager)
    assert len(template_manager.template_dirs) == 2
    assert template_manager.templates == []


def test_template_builtin_variables(template_manager):
    builtins = template_manager.template_builtin_variables()
    assert 'clipboard' in builtins
    assert callable(builtins['clipboard'])


def test_ensure_template(template_manager):
    template_name = "existent_template.md"
    result = template_manager.ensure_template(template_name)
    assert result[0] is True
    assert result[1] == template_name
    assert "exists" in result[2]

    template_name = "nonexistent_template.md"
    result = template_manager.ensure_template(template_name)
    assert result[0] is False
    assert result[1] == template_name
    assert "not found" in result[2]


def test_extract_metadata_keys(template_manager):
    metadata = {
        'title': 'Test Title',
        'description': 'Test Description',
        'custom': 'Custom Value'
    }
    keys = ['title', 'custom']
    result = template_manager.extract_metadata_keys(keys, metadata)
    assert result[0] == {'description': 'Test Description'}
    assert result[1] == {'title': 'Test Title', 'custom': 'Custom Value'}


def test_extract_template_run_overrides(template_manager):
    metadata = {
        'title': 'Test Title',
        'description': 'Test Description',
        'model_customizations': {'option': 'value'},
        'custom': 'Custom Value'
    }
    result = template_manager.extract_template_run_overrides(metadata)
    assert result[0] == {'custom': 'Custom Value'}
    assert result[1] == {'title': 'Test Title', 'model_customizations': {'option': 'value'}}


def test_build_message_from_template(template_manager):
    template_name = "existent_template.md"
    result = template_manager.build_message_from_template(template_name, {'name': 'John Doe'})
    assert 'Hello, John Doe' in result[0]
    assert result[1] == {'title': 'Existent Template'}


def test_process_template_builtin_variables(template_manager, monkeypatch):
    util.paste_from_clipboard = MagicMock(return_value="clipboard_text")
    monkeypatch.setattr(template_manager, 'template_builtin_variables', util.paste_from_clipboard)

    variables = ['clipboard']
    result = template_manager.process_template_builtin_variables("existent_template.md", variables)
    assert result == {'clipboard': 'clipboard_text'}


def test_make_template_dirs(template_manager, tmpdir):
    template_manager.config.config_dir = str(tmpdir)
    template_manager.config.config_profile_dir = str(tmpdir)
    template_dirs = template_manager.make_template_dirs()

    assert len(template_dirs) == 2
    for template_dir in template_dirs:
        assert os.path.exists(template_dir)

def test_load_templates(template_manager):
    template_manager.load_templates()
    assert isinstance(template_manager.templates_env, Environment)
    assert isinstance(template_manager.templates, list)

def test_get_template_and_variables_found(template_manager):
    template_name = "test_template.jinja"
    template_content = "{{ some_variable }}"

    # Mock template environment
    mock_env = MagicMock()
    mock_env.get_template.return_value = Template(template_content)
    mock_env.loader.get_source.return_value = template_content
    mock_env.parse.return_value = meta.parse(template_content)

    template_manager.templates_env = mock_env

    template, variables = template_manager.get_template_and_variables(template_name)

    assert isinstance(template, Template)
    assert "some_variable" in variables

def test_get_template_and_variables_not_found(template_manager):
    template_name = "non_existent_template.jinja"

    # Mock template environment
    mock_env = MagicMock()
    mock_env.get_template.side_effect = TemplateNotFound(template_name)
    template_manager.templates_env = mock_env

    template, variables = template_manager.get_template_and_variables(template_name)

    assert template is None
    assert variables is None
