import os
import frontmatter
import shutil
import tempfile

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, meta

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util

TEMP_TEMPLATE_DIR = "lwe-temp-templates"


class TemplateManager:
    """
    Manage templates.
    """

    def __init__(self, config=None):
        """
        Initializes the class with the given configuration.

        :param config: Configuration settings. If not provided, a default Config object is used.
        :type config: Config, optional
        """
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.temp_template_dir = self.make_temp_template_dir()
        self.user_template_dirs = (
            self.config.args.templates_dir
            or util.get_environment_variable_list("template_dir")
            or self.config.get("directories.templates")
        )
        self.make_user_template_dirs()
        self.system_template_dirs = [
            os.path.join(util.get_package_root(self), "templates"),
        ]
        self.all_template_dirs = (
            self.user_template_dirs + self.system_template_dirs + [self.temp_template_dir]
        )
        self.templates = []
        self.templates_env = None

    def template_builtin_variables(self):
        """
        This method returns a dictionary of built-in variables.

        :return: A dictionary where the key is the variable name and the value is the function associated with it.
        :rtype: dict
        """
        return {
            "clipboard": util.paste_from_clipboard,
        }

    def ensure_template(self, template_name):
        """
        Checks if a template exists.

        :param template_name: The name of the template to check.
        :type template_name: str
        :return: A tuple containing a boolean indicating if the template exists, the template name, and a message.
        :rtype: tuple
        """
        if not template_name:
            return False, None, "No template name specified"
        self.log.debug(f"Ensuring template {template_name} exists")
        self.load_templates()
        if template_name not in self.templates:
            return False, template_name, f"Template {template_name!r} not found"
        message = f"Template {template_name} exists"
        self.log.debug(message)
        return True, template_name, message

    def get_raw_template(self, template_name):
        """
        Retrieve the raw source of a template by its name.

        :param template_name: The name of the template to retrieve.
        :type template_name: str
        :return: A tuple containing a boolean success flag, the raw template source as a string, and a user message.
        :rtype: tuple
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template_source = self.templates_env.loader.get_source(self.templates_env, template_name)
        return True, template_source[0], f"Retrieved raw template: {template_name}"

    def get_template_variables_substitutions(self, template_name):
        """
        Get template variables and their substitutions.

        :param template_name: The name of the template
        :type template_name: str
        :return: A tuple containing a boolean indicating success, the template with its variables and substitutions, and a user message
        :rtype: tuple
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, variables = self.get_template_and_variables(template_name)
        substitutions = self.process_template_builtin_variables(template_name, variables)
        return (
            True,
            (template, variables, substitutions),
            f"Loaded template substitutions: {template_name}",
        )

    def render_template(self, template_name):
        """
        Render a template with variable substitutions.

        :param template_name: The name of the template to render
        :type template_name: str
        :return: A tuple containing a success flag, the rendered message or template name, and a user message
        :rtype: tuple
        """
        success, response, user_message = self.get_template_variables_substitutions(template_name)
        if not success:
            return success, template_name, user_message
        template, variables, substitutions = response
        message = template.render(**substitutions)
        return True, message, f"Rendered template: {template_name}"

    def get_template_source(self, template_name):
        """
        Get the source of a specified template.

        :param template_name: The name of the template
        :type template_name: str
        :return: A tuple containing a boolean indicating success, the source of the template if successful, and a user message
        :rtype: tuple
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        return True, source, f"Loaded template source: {template_name}"

    def get_template_editable_filepath(self, template_name):
        """
        Get the editable file path for a given template.

        :param template_name: The name of the template
        :type template_name: str
        :return: A tuple containing a boolean indicating if the template is editable, the file path of the template, and a message
        :rtype: tuple
        """
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.get_template_and_variables(template_name)
        if template:
            filename = template.filename
            if self.is_system_template(filename):
                return (
                    False,
                    template_name,
                    f"{template_name} is a system template, and cannot be edited directly",
                )
        else:
            filename = os.path.join(self.user_template_dirs[0], template_name)
        return True, filename, f"Template {filename} can be edited"

    def copy_template(self, old_name, new_name):
        """
        Copies a template file to a new location.

        :param old_name: The name of the existing template file.
        :type old_name: str
        :param new_name: The name for the new template file.
        :type new_name: str
        :return: A tuple containing a boolean indicating success or failure, the new file path, and a status message.
        :rtype: tuple
        """
        template, _ = self.get_template_and_variables(old_name)
        if not template:
            return False, old_name, f"{old_name} does not exist"
        old_filepath = template.filename
        base_filepath = (
            self.user_template_dirs[0]
            if self.is_system_template(old_filepath)
            else os.path.dirname(old_filepath)
        )
        new_filepath = os.path.join(base_filepath, new_name)
        if os.path.exists(new_filepath):
            return False, new_filepath, f"{new_filepath} already exists"
        shutil.copy2(old_filepath, new_filepath)
        self.load_templates()
        return True, new_filepath, f"Copied template {old_filepath} to {new_filepath}"

    def template_can_delete(self, template_name):
        """
        Checks if a template can be deleted.

        :param template_name: The name of the template to check
        :type template_name: str
        :return: A tuple containing a boolean indicating if the template can be deleted, the template name or filename, and a message
        :rtype: tuple
        """
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
        """
        Deletes a specified template file and reloads the templates.

        :param filename: The name of the file to be deleted.
        :type filename: str
        :return: A tuple containing a boolean indicating success, the filename, and a message.
        :rtype: tuple
        """
        os.remove(filename)
        self.load_templates()
        return True, filename, f"Deleted {filename}"

    def extract_metadata_keys(self, keys, metadata):
        """
        Extracts specified keys from the metadata.

        :param keys: Keys to be extracted from the metadata.
        :type keys: list
        :param metadata: The metadata from which keys are to be extracted.
        :type metadata: dict
        :return: A tuple containing the updated metadata and the extracted keys.
        :rtype: tuple
        """
        extracted_keys = {}
        for key in keys:
            if key in metadata:
                extracted_keys[key] = metadata[key]
                del metadata[key]
        return metadata, extracted_keys

    def extract_template_run_overrides(self, metadata):
        """
        Extracts template run overrides from metadata.

        :param metadata: The metadata from which to extract overrides.
        :type metadata: dict
        :return: A tuple containing the updated metadata and the extracted overrides.
        :rtype: tuple
        """
        override_keys = [
            "request_overrides",
        ]
        builtin_keys = [
            "description",
        ]
        metadata, overrides = self.extract_metadata_keys(override_keys, metadata)
        metadata, _ = self.extract_metadata_keys(builtin_keys, metadata)
        return metadata, overrides

    def build_message_from_template(self, template_name, substitutions=None):
        """
        Build a message from a given template and substitutions.

        :param template_name: The name of the template to use.
        :type template_name: str
        :param substitutions: The substitutions to apply to the template. Defaults to None.
        :type substitutions: dict, optional
        :return: The rendered message and any overrides.
        :rtype: tuple
        """
        substitutions = substitutions or {}
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        template_substitutions, overrides = self.extract_template_run_overrides(source.metadata)
        final_substitutions = {**template_substitutions, **substitutions}
        self.log.debug(f"Rendering template: {template_name}")
        final_template = self.templates_env.from_string(source.content)
        message = final_template.render(**final_substitutions)
        return message, overrides

    def process_template_builtin_variables(self, template_name, variables=None):
        """
        Process the built-in variables in a template.

        :param template_name: The name of the template
        :type template_name: str
        :param variables: The variables to be processed, defaults to None
        :type variables: list, optional
        :return: A dictionary of substitutions for the variables
        :rtype: dict
        """
        variables = variables or []
        builtin_variables = self.template_builtin_variables()
        substitutions = {}
        for variable, method in builtin_variables.items():
            if variable in variables:
                substitutions[variable] = method()
                self.log.debug(
                    f"Collected builtin variable {variable} for template {template_name}: {substitutions[variable]}"
                )
        return substitutions

    def make_user_template_dirs(self):
        """
        Create directories for user templates if they do not exist.

        :return: None
        """
        for template_dir in self.user_template_dirs:
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)

    def make_temp_template_dir(self):
        """
        Create directory for temporary templates if it does not exist.

        :return: None
        """
        temp_dir = os.path.join(tempfile.gettempdir(), TEMP_TEMPLATE_DIR)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        util.clean_directory(temp_dir)
        return temp_dir

    def make_temp_template(self, template_contents, suffix="md"):
        """
        Create a temporary template.

        :param template_contents: The contents to be written to the temporary template
        :type template_contents: str
        :param suffix: The suffix for the temporary file, defaults to 'md'
        :type suffix: str, optional
        :return: The basename and the full path of the temporary template
        :rtype: tuple
        """
        filepath = util.write_temp_file(template_contents, suffix="md", dir=self.temp_template_dir)
        return os.path.basename(filepath), filepath

    def remove_temp_template(self, template_name):
        """
        Remove a temporary template.

        :param template_name: The name of the temporary template
        :type template_name: str
        :return: None
        """
        filepath = os.path.join(self.temp_template_dir, template_name)
        if os.path.exists(filepath):
            os.remove(filepath)

    def load_templates(self):
        """
        Load templates from directories.

        :return: None
        """
        self.log.debug("Loading templates from dirs: %s" % ", ".join(self.all_template_dirs))
        jinja_env = Environment(loader=FileSystemLoader(self.all_template_dirs))
        filenames = jinja_env.list_templates()
        self.templates_env = jinja_env
        self.templates = filenames or []

    def get_template_and_variables(self, template_name):
        """
        Fetches a template and its variables.

        :param template_name: The name of the template to fetch
        :type template_name: str
        :return: The fetched template and its variables, or (None, None) if the template is not found
        :rtype: tuple
        """
        try:
            template = self.templates_env.get_template(template_name)
        except TemplateNotFound:
            return None, None
        template_source = self.templates_env.loader.get_source(self.templates_env, template_name)
        parsed_content = self.templates_env.parse(template_source)
        variables = meta.find_undeclared_variables(parsed_content)
        return template, variables

    def is_system_template(self, filepath):
        """
        Check if a file is a system template.

        :param filepath: The path of the file to check
        :type filepath: str
        :return: True if the file is a system template, False otherwise
        :rtype: bool
        """
        for dir in self.system_template_dirs:
            if filepath.startswith(dir):
                return True
        return False
