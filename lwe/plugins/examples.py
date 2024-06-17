import os
import shutil

from lwe.core.plugin import Plugin
import lwe.core.util as util

TYPES = [
    "presets",
    "templates",
    "workflows",
    "tools",
]


class Examples(Plugin):
    """
    Easily install example configuration files
    """

    def default_config(self):
        return {
            "confirm_overwrite": True,
            "default_types": TYPES,
        }

    def setup(self):
        self.profile_dir = self.config.config_profile_dir
        self.examples_root = os.path.join(
            os.path.dirname(util.get_package_root(self.config)), "lwe", "examples"
        )
        self.default_types = self.config.get("plugins.examples.default_types")
        self.confirm_overwrite = self.config.get("plugins.examples.confirm_overwrite")
        self.log.info(
            f"This is the examples plugin, running with profile dir: {self.profile_dir}, examples root: {self.examples_root}, default types: {self.default_types}, confirm overwrite: {self.confirm_overwrite}"
        )

    def get_shell_completions(self, _base_shell_completions):
        """Example of provided shell completions."""
        commands = {}
        commands[util.command_with_leader("examples")] = util.list_to_completion_hash(
            ["list"] + TYPES
        )
        return commands

    def get_examples(self, example_type):
        example_type_dir = f"{self.examples_root}/{example_type}"
        examples = []
        for root, dirs, files in os.walk(example_type_dir):
            # Exclude directories that start with an underscore
            dirs[:] = [d for d in dirs if not d.startswith("_")]
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    examples.append(os.path.relpath(file_path, example_type_dir))
        return examples

    def install_example_file(self, example_type, example_file):
        """Helper method to install a single example file."""
        source_file = os.path.join(self.examples_root, example_type, example_file)
        dest_dir = os.path.join(self.profile_dir, example_type)
        dest_file = os.path.join(dest_dir, example_file)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        if os.path.exists(dest_file) and self.confirm_overwrite:
            confirm = input(f"File {dest_file} already exists. Overwrite? (y/n): ")
            if confirm.lower() != "y":
                message = f"Skipping file {example_file}"
                util.print_status_message(True, message, "bold blue")
                self.log.info(message)
                return
        try:
            shutil.copy(source_file, dest_file)
            util.print_status_message(True, f"Installed {example_file} to {dest_file}", "bold blue")
            self.log.info(f"Installed {example_file} to {dest_file}")
        except Exception as e:
            util.print_status_message(False, str(e))
            self.log.error(f"Error installing {example_file}: {str(e)}")

    def confirm_install(self, example_types):
        confirm = input(
            f"Are you sure you want to install examples for the following types? {', '.join(example_types)} (y/n): "
        )
        if confirm.lower() not in ["yes", "y"]:
            message = "Skipping installation"
            util.print_status_message(False, message)
            self.log.info(message)
            return False
        return True

    def install_examples_confirm(self, example_type=None):
        example_types = [example_type] if example_type else self.default_types
        if not self.confirm_install(example_types):
            return
        self.install_examples(example_type)

    def install_examples(self, example_type=None):
        """Install example files."""
        try:
            example_types = [example_type] if example_type else self.default_types
            for example_type in example_types:
                message = f"Installing examples for: {example_type}"
                util.print_status_message(True, message)
                self.log.info(message)
                for example_file in self.get_examples(example_type):
                    self.install_example_file(example_type, example_file)
            message = "Finished installing examples"
            util.print_status_message(True, message)
            self.log.info(message)
        except Exception as e:
            util.print_status_message(False, str(e))
            self.log.error(f"Error installing examples: {str(e)}")

    def command_examples(self, arg):
        """
        List or install example files

        The example files that come with the package can be listed and
        optionally installed in the currently running profile configuration.

        Arguments:
            list: List all example files, and where they will be installed.
            type: The type of example files to install (default is all configured types).

        Examples:
            {COMMAND} list
            {COMMAND} presets
        """
        if arg:
            if arg in self.default_types:
                self.log.info(f"Installing examples for: {arg}")
                self.install_examples_confirm(arg)
            elif arg == "list":
                for t in self.default_types:
                    self.log.debug(f"Listing examples for: {t}")
                    install_dir = f"{self.profile_dir}/{t}"
                    file_list = "\n".join([f"* {f}" for f in sorted(self.get_examples(t))])
                    util.print_markdown("## %s\nInstall to: %s\n%s" % (t, install_dir, file_list))
            else:
                return False, arg, "Invalid example type"
        else:
            self.log.info(f"Installing examples for: {', '.join(self.default_types)}")
            self.install_examples_confirm()
