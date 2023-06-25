import os
import frontmatter
import shutil

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, meta

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util

class TemplateManager():
    """
    Manage templates.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.user_template_dirs = self.config.args.template_dir or util.get_environment_variable_list('template_dir') or self.config.get('directories.templates')
        self.make_user_template_dirs()
        self.system_template_dirs = [
            os.path.join(util.get_package_root(self), 'templates'),
        ]
        self.all_template_dirs = self.user_template_dirs + self.system_template_dirs
        self.templates = []
        self.templates_env = None

    def template_builtin_variables(self):
        return {
            'clipboard': util.paste_from_clipboard,
        }

    def ensure_template(self, template_name):
        if not template_name:
            return False, None, "No template name specified"
        self.log.debug(f"Ensuring template {template_name} exists")
        self.load_templates()
        if template_name not in self.templates:
            return False, template_name, f"Template '{template_name}' not found"
        message = f"Template {template_name} exists"
        self.log.debug(message)
        return True, template_name, message

    def get_template_variables_substitutions(self, template_name):
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, variables = self.get_template_and_variables(template_name)
        substitutions = self.process_template_builtin_variables(template_name, variables)
        return True, (template, variables, substitutions), f"Loaded template substitutions: {template_name}"

    def render_template(self, template_name):
        success, response, user_message = self.get_template_variables_substitutions(template_name)
        if not success:
            return success, template_name, user_message
        template, variables, substitutions = response
        message = template.render(**substitutions)
        return True, message, f"Rendered template: {template_name}"

    def get_template_source(self, template_name):
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        return True, source, f"Loaded template source: {template_name}"

    def get_template_editable_filepath(self, template_name):
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.get_template_and_variables(template_name)
        if template:
            filename = template.filename
            if self.is_system_template(filename):
                return False, template_name, f"{template_name} is a system template, and cannot be edited directly"
        else:
            filename = os.path.join(self.user_template_dirs[0], template_name)
        return True, filename, f"Template {filename} can be edited"

    def copy_template(self, old_name, new_name):
        template, _ = self.get_template_and_variables(old_name)
        if not template:
            return False, old_name, f"{old_name} does not exist"
        old_filepath = template.filename
        base_filepath = self.user_template_dirs[0] if self.is_system_template(old_filepath) else os.path.dirname(old_filepath)
        new_filepath = os.path.join(base_filepath, new_name)
        if os.path.exists(new_filepath):
            return False, new_filepath, f"{new_filepath} already exists"
        shutil.copy2(old_filepath, new_filepath)
        self.load_templates()
        return True, new_filepath, f"Copied template {old_filepath} to {new_filepath}"

    def template_can_delete(self, template_name):
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.get_template_and_variables(template_name)
        if template:
            filename = template.filename
            if self.is_system_template(filename):
                return False, filename, f"{filename} is a system template, and cannot be deleted"
        else:
            return False, template_name, f"{template_name} does not exist"
        return True, filename, f"Template {filename} can be deleted"

    def template_delete(self, filename):
        os.remove(filename)
        self.load_templates()
        return True, filename, f"Deleted {filename}"

    def extract_metadata_keys(self, keys, metadata):
        extracted_keys = {}
        for key in keys:
            if key in metadata:
                extracted_keys[key] = metadata[key]
                del metadata[key]
        return metadata, extracted_keys

    def extract_template_run_overrides(self, metadata):
        override_keys = [
            'title',
            'request_overrides',
        ]
        builtin_keys = [
            'description',
        ]
        metadata, overrides = self.extract_metadata_keys(override_keys, metadata)
        metadata, _ = self.extract_metadata_keys(builtin_keys, metadata)
        return metadata, overrides

    def build_message_from_template(self, template_name, substitutions=None):
        substitutions = substitutions or {}
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        template_substitutions, overrides = self.extract_template_run_overrides(source.metadata)
        final_substitutions = {**template_substitutions, **substitutions}
        self.log.debug(f"Rendering template: {template_name}")
        final_template = Template(source.content)
        message = final_template.render(**final_substitutions)
        return message, overrides

    def process_template_builtin_variables(self, template_name, variables=None):
        variables = variables or []
        builtin_variables = self.template_builtin_variables()
        substitutions = {}
        for variable, method in builtin_variables.items():
            if variable in variables:
                substitutions[variable] = method()
                self.log.debug(f"Collected builtin variable {variable} for template {template_name}: {substitutions[variable]}")
        return substitutions

    def make_user_template_dirs(self):
        for template_dir in self.user_template_dirs:
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)

    def load_templates(self):
        self.log.debug("Loading templates from dirs: %s" % ", ".join(self.all_template_dirs))
        jinja_env = Environment(loader=FileSystemLoader(self.all_template_dirs))
        filenames = jinja_env.list_templates()
        self.templates_env = jinja_env
        self.templates = filenames or []

    def get_template_and_variables(self, template_name):
        try:
            template = self.templates_env.get_template(template_name)
        except TemplateNotFound:
            return None, None
        template_source = self.templates_env.loader.get_source(self.templates_env, template_name)
        parsed_content = self.templates_env.parse(template_source)
        variables = meta.find_undeclared_variables(parsed_content)
        return template, variables

    def is_system_template(self, filepath):
        for dir in self.system_template_dirs:
            if filepath.startswith(dir):
                return True
        return False
