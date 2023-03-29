import os
import tempfile
import pytest
import pyperclip

from jinja2 import Environment, Template

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.template import TemplateManager
import chatgpt_wrapper.core.util as util

TEST_DIR = os.path.join(tempfile.gettempdir(), 'chatgpt_wrapper_test')
TEST_CONFIG_DIR = os.path.join(TEST_DIR, 'config')
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data')
TEST_PROFILE = 'test'


@pytest.fixture
def test_config():
    util.remove_and_create_dir(TEST_CONFIG_DIR)
    util.remove_and_create_dir(TEST_DATA_DIR)
    config = Config(TEST_CONFIG_DIR, TEST_DATA_DIR, profile=TEST_PROFILE)
    return config


@pytest.fixture
def template_manager(test_config):
    template_manager = TemplateManager(config=test_config)
    template_manager.load_templates()
    return template_manager

def make_template_file(template_manager, template_name, content=None):
    template_dir = template_manager.template_dirs[0]
    util.create_file(template_dir, template_name, content)
    template_manager.load_templates()

def remove_template_file(template_manager, template_name):
    template_dir = template_manager.template_dirs[0]
    os.remove(os.path.join(template_dir, template_name))

def test_init(template_manager):
    assert isinstance(template_manager, TemplateManager)
    assert len(template_manager.template_dirs) > 0
    assert template_manager.templates == []


def test_template_builtin_variables(template_manager):
    builtins = template_manager.template_builtin_variables()
    assert 'clipboard' in builtins
    assert callable(builtins['clipboard'])


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


def test_extract_metadata_keys(template_manager):
    metadata = {
        'title': 'Test Title',
        'description': 'Test Description',
        'custom': 'Custom Value'
    }
    keys = ['title', 'custom']
    metadata, extracted_keys = template_manager.extract_metadata_keys(keys, metadata)
    assert metadata == {'description': 'Test Description'}
    assert extracted_keys == {'title': 'Test Title', 'custom': 'Custom Value'}


def test_extract_template_run_overrides(template_manager):
    metadata = {
        'title': 'Test Title',
        'description': 'Test Description',
        'model_customizations': {'option': 'value'},
        'custom': 'Custom Value'
    }
    metadata, overrides = template_manager.extract_template_run_overrides(metadata)
    assert metadata == {'custom': 'Custom Value'}
    assert overrides == {'title': 'Test Title', 'model_customizations': {'option': 'value'}}


def test_build_message_from_template(template_manager):
    template_name = "hello.md"
    template_content = """
---
title: Existent Template
---
Hello, {{ name }}
"""
    make_template_file(template_manager, template_name, template_content)
    message, overrides = template_manager.build_message_from_template(template_name, {'name': 'John Doe'})
    remove_template_file(template_manager, template_name)
    assert 'Hello, John Doe' in message
    assert overrides == {'title': 'Existent Template'}


def test_process_template_builtin_variables(template_manager, monkeypatch):
    pyperclip.copy("clipboard_text")
    variables = ['clipboard']
    substitutions = template_manager.process_template_builtin_variables("existent_template.md", variables)
    assert substitutions == {'clipboard': 'clipboard_text'}


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
