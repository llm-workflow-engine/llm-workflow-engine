import os
import frontmatter

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, meta

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
import chatgpt_wrapper.core.util as util

class TemplateManager():
    """
    Manage templates.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.template_dirs = self.make_template_dirs()
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
            'model_customizations',
        ]
        builtin_keys = [
            'description',
        ]
        metadata, overrides = self.extract_metadata_keys(override_keys, metadata)
        metadata, _ = self.extract_metadata_keys(builtin_keys, metadata)
        return metadata, overrides

    def build_message_from_template(self, template_name, substitutions={}):
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        template_substitutions, overrides = self.extract_template_run_overrides(source.metadata)
        final_substitutions = {**template_substitutions, **substitutions}
        self.log.debug(f"Rendering template: {template_name}")
        final_template = Template(source.content)
        message = final_template.render(**final_substitutions)
        return message, overrides

    def process_template_builtin_variables(self, template_name, variables=[]):
        builtin_variables = self.template_builtin_variables()
        substitutions = {}
        for variable, method in builtin_variables.items():
            if variable in variables:
                substitutions[variable] = method()
                self.log.debug(f"Collected builtin variable {variable} for template {template_name}: {substitutions[variable]}")
        return substitutions

    def make_template_dirs(self):
        template_dirs = []
        template_dirs.append(os.path.join(self.config.config_dir, 'templates'))
        template_dirs.append(os.path.join(self.config.config_profile_dir, 'templates'))
        for template_dir in template_dirs:
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)
        return template_dirs

    def load_templates(self):
        self.log.debug("Loading templates from dirs: %s" % ", ".join(self.template_dirs))
        jinja_env = Environment(loader=FileSystemLoader(self.template_dirs))
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
