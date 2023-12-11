import re
from datetime import datetime
from pathlib import Path
from tomllib import load as toml_load
from typing import Any, Literal

from attrs import define, field
from git import Repo


@define(auto_attribs=True, kw_only=True, order=True)
class ConfigManager:
    """
    A class for managing configuration settings.

    This class reads and processes a TOML configuration file, replacing placeholders with specified values.

    Attributes
    ----------
    config_path : The file path to the configuration file.

    name_placeholder : A placeholder string to be replaced in the
        configuration.

    defaults_dir : The directory containing default configuration files.

    year_placeholder : A placeholder for the current year to be used in the
        configuration.

    config : The processed configuration dictionary, initialized post object
        creation.

    Methods
    -------
    replace_placeholders
        Processes the raw configuration dictionary, replacing placeholders with actual values.

    get_section
        Retrieves a specific section from the processed configuration dictionary.
    Notes
    -----

    *Private Methods*:
        __attrs_post_init__
        Initializes the config attribute by loading and processing the TOML configuration file.
        _replace : Recursively replaces placeholders in the given value with actual values.
    """

    config_path: Path = field(default=Path("config.toml"))
    name_placeholder: str = field(default="John Doe")
    defaults_dir: Path = field(default=Path("gitdefaults/"))
    year_placeholder: int = field(default=datetime.now().year)
    config: dict = field(init=False)

    def __attrs_post_init__(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file at {self.config_path} not found.")
        self.config = self.replace_placeholders(
            raw_config=toml_load(self.config_path.read_bytes())
        )

    def replace_placeholders(self, raw_config: dict) -> dict:
        """
        Replaces placeholders in the raw configuration dictionary with actual values.

        Parameters
        ----------
        raw_config : dict
            The raw configuration dictionary containing placeholders.

        Returns
        -------
        dict
            The processed configuration dictionary with placeholders replaced
        """

        return {k: self._replace(value=v) for k, v in raw_config.items()}

    def _replace(self, value) -> Any:
        """
        Recursively replaces placeholders in the given value with actual values.

        Parameters
        ----------
        value : Any
            The value (string, dict, list, or other) potentially containing placeholders.

        Returns
        -------
        Any
            The value with placeholders replaced, maintaining the original type.
        """

        if isinstance(value, str):
            return value.replace(
                "YEAR_PLACEHOLDER", str(self.year_placeholder)
            ).replace("NAME_PLACEHOLDER", self.name_placeholder)
        elif isinstance(value, dict):
            return {k: self._replace(value=v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._replace(value=v) for v in value]
        return value

    def get_section(self, section: str) -> dict:
        """
        Retrieves a specific section from the processed configuration
        dictionary.

        Parameters
        ----------
        section : str
            The name of the section to retrieve.

        Returns
        -------
        dict
            The configuration dictionary for the specified section, or an
            empty dictionary if the section does not exist.
        """

        return self.config.get(section, {})


@define(auto_attribs=True, kw_only=True, order=True)
class LicenseManager:
    """
    A class for managing license and header information in project files.

    Geared towards Federal developers, it separates work and personal
    licensing, and adds an INTENT.md for [Federal] development per
    Defense Digital Service guidance/DoD policy.

    This class applies license headers to Python files and manages copyright
    notices in project documentation.

    Attributes
    ----------
    config : dict[str, str]
        A dictionary containing configuration for license headers and other
        related information.

    Methods
    -----------
    modify_file
        Modifies a file's content using a given modifier function.

    prepend_to_file
        Prepends specified content to a file.

    update_copyright_year
        Updates the copyright year in a given text.

    apply_files_and_headers
        Applies license headers and updates copyright notices in project files
    """

    config: dict[str, str]

    @staticmethod
    def modify_file(file_path: Path, modifier_func) -> None:
        """
        Modifies the content of a specified file using a provided modifier
        function.

        This method reads the content of a file, applies the modifier function
        to transform it, and then writes the modified content back to the file.

        Parameters
        ----------
        file_path : Path
            The path of the file to be modified.

        modifier_func : Callable
            A function that takes the current file content as input and
            returns the modified content.
        """

        content: str = file_path.read_text()
        updated_content: Any = modifier_func(content)
        file_path.write_text(data=updated_content)

    @staticmethod
    def prepend_to_file(file_path: Path, content: str) -> None:
        """
        Prepends specified content to the beginning of a file.

        This method uses the `modify_file` method to add the given content to
        the start of the file's existing content.

        Parameters
        ----------
        file_path : Path
            The path of the file to which the content will be prepended.

        content : str
            The string content to prepend to the file.

        Returns
        -------
        None
        """

        LicenseManager.modify_file(
            file_path=file_path,
            modifier_func=lambda original: content + "\n" + original,
        )

    @staticmethod
    def update_copyright_year(text: str, current_year: int) -> str:
        """
        Updates the copyright year in a given text.

        This method searches for a copyright year pattern in the text and
        updates it to include the current year, if necessary.

        Parameters
        ----------
        text : str
            The text containing the copyright information to be updated.

        current_year : int
            The current year, used to update the copyright year in the text.

        Returns
        -------
        str
            The text with the updated copyright year.
        """

        return re.sub(
            pattern=r"© (\d{4})(-\d{4})?",
            repl=lambda m: f"© {m.group(1)}-{current_year}"
            if int(m.group(1)) < current_year
            else m.group(0),
            string=text,
        )

    def apply_files_and_headers(self, target_dir: Path) -> None:
        """
        Applies license headers to Python files and updates copyright notices
        in project documentation.

        This method processes Python files in a specified directory, applying
        a script header if it's not already present. It also updates or
        creates the LICENSE.md and INTENT.md files with appropriate content
        and copyright notices.

        Parameters
        ----------
        target_dir : Path
            The directory containing the files to be processed.

        Returns
        -------
        None
        """

        script_header: str = self.config.get("script", "")
        current_year: int = datetime.now().year

        for py_file in target_dir.glob(pattern="*.py"):
            if script_header not in py_file.read_text():
                self.prepend_to_file(file_path=py_file, content=script_header)

        license_path: Path = target_dir / "LICENSE.md"
        license_content: str = self.config.get("license", "")
        if license_path.exists():
            content = license_path.read_text()
            updated_content = self.update_copyright_year(
                text=content, current_year=current_year
            )
            license_path.write_text(data=updated_content)
        else:
            license_path.write_text(data=license_content)

        intent_path: Path = target_dir / "INTENT.md"
        if "intent" in self.config:
            intent_content: str = self.config.get("intent", "")
            if intent_path.exists():
                content: str = intent_path.read_text()
                updated_content: str = self.update_copyright_year(
                    text=content, current_year=current_year
                )
                intent_path.write_text(data=updated_content)
            else:
                intent_path.write_text(data=intent_content)


@define(auto_attribs=True, kw_only=True, order=True)
class VersionManager:
    """
    A class for managing versioning in a Git repository.

    This class handles version bumping according to semantic versioning
    principles.

    Attributes
    ----------
    config : dict[str, str]
        A dictionary containing configuration related to versioning.
    latest_tag : str
        The latest tag found in the repository, initialized post object
        creation.
    repo : Repo
        The gitpython Git repository object.

    Methods
    -----------
    bump_version
        Bumps the version of the project based on the specified bump type.

    Notes
    -----
        __attrs_post_init__
        Initializes the latest_tag attribute by fetching the latest tag from
        the repository.
    """

    config: dict[str, str]
    latest_tag: str = field(init=False)
    repo: Repo = field(default=Repo(path="."))

    def __attrs_post_init__(self) -> None:
        """
        Initializes the latest_tag attribute by fetching the latest tag from
        the repository.

        This method attempts to retrieve the latest tag from the Git
        repository. If an error occurs, the latest_tag is set to an empty
        string and an error message is printed.
        """

        try:
            self.latest_tag = self.repo.git.describe("--tags", "--abbrev=0")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.latest_tag = ""

    def bump_version(self, bump_type: str) -> str:
        """
        Bumps the version of the project based on the specified bump type.

        The method increments the major, minor, or patch part of the version
        number, as specified, and creates a new Git tag with the bumped
        version. If the bump type is not valid or the current tag format is
        unrecognized, an error message is printed and no changes are made.

        Parameters
        ----------
        bump_type : str
            The type of version bump to apply. Valid options are 'major',
            'minor', or 'patch'.

        Returns
        -------
        str
            The new version tag after bumping, or the current tag if no
            changes are made.
        """

        valid_bump_types: set[str] = {"major", "minor", "patch"}

        if bump_type not in valid_bump_types:
            print("Invalid bump type. Aborting version change.")
            return self.latest_tag

        if match := re.match(pattern=r"v(\d+)\.(\d+)\.(\d+)", string=self.latest_tag):
            major, minor, patch = map(int, match.groups())
            new_version: str = {
                "major": f"v{major + 1}.0.0",
                "minor": f"v{major}.{minor + 1}.0",
                "patch": f"v{major}.{minor}.{patch + 1}",
            }[bump_type]

            self.repo.git.tag(new_version)
            return new_version

        print("Invalid tag format or no tags found. Aborting version change.")
        return self.latest_tag


@define(auto_attribs=True, kw_only=True, order=True)
class GitHookManager:
    """
    A class for managing Git hooks in a project.

    This class sets up license information and bumps version numbers as part
    of Git hook management.

    Attributes
    ----------
    config_manager : ConfigManager
        An instance of ConfigManager for managing configuration settings.
    target_dir : Path
        The target directory for applying Git hooks.
    license_manager : LicenseManager
        An instance of LicenseManager, initialized after object creation for managing license information.

    Methods
    -----------
    run
        Executes the Git hook management process.
    decide_project_type
        Determines the project type based on user input.
    check_existing_files
        Checks for the existence of necessary files based on the project type.
    setup_license_manager
        Sets up the LicenseManager instance based on the project type.
    """

    config_manager: ConfigManager
    target_dir: Path = field(default=Path.cwd())
    license_manager: LicenseManager = field(default=None, init=False)

    def run(self) -> None:
        """
        Executes the Git hook management process for a project.

        This method orchestrates the overall process of managing Git hooks. It
        determines the project type, checks for existing necessary files, sets
        up the license manager accordingly, and applies license headers and
        version bumping as required.
        """

        project_type: str = self.decide_project_type()
        if self.check_existing_files(project_type=project_type):
            self.setup_license_manager(project_type=project_type)
            if self.license_manager:
                self.license_manager.apply_files_and_headers(target_dir=self.target_dir)

            version_manager = VersionManager(config={})
            version_manager.bump_version(bump_type="patch")

    def decide_project_type(self) -> str:
        """
        Determines the project type based on user input.

        Asks the user to specify whether the project is for personal or work
        purposes. The input is validated, and the method continues to prompt

        until a valid response is received.

        Returns
        -------
        str
            The determined project type, either 'personal' or 'work'.
        """
        project_types: dict[str, str] = {"p": "personal", "w": "work"}
        while True:
            user_input: str = input(
                "Is this (p)ersonally produced or for (w)ork? (p/w): "
            ).lower()
            if user_input in project_types:
                return project_types[user_input]
            print("Invalid input. Please enter 'p' or 'w'.")

    def check_existing_files(self, project_type: str) -> bool:
        """
        Checks for the existence of necessary files based on the project type.

        For a work project, it checks for the existence of both LICENSE.md and
        INTENT.md. For a personal project, it only checks for LICENSE.md.

        Parameters
        ----------
        project_type : str
            The type of the project, 'personal' or 'work'.

        Returns
        -------
        bool
            True if the necessary files for the given project type are
                missing, otherwise False.
        """

        license_path: Path = self.target_dir / "LICENSE.md"
        intent_path: Path = self.target_dir / "INTENT.md"
        return (
            project_type == "w" and not (license_path.exists() and intent_path.exists())
        ) or (project_type == "p" and not license_path.exists())

    def setup_license_manager(self, project_type: str) -> None:
        config_section: Literal = "personal" if project_type == "p" else "work"
        self.license_manager = LicenseManager(
            config=self.config_manager.get_section(section=config_section)
        )
