import re
from datetime import datetime
from pathlib import Path
from tomllib import load as toml_load
from typing import Any, Literal

from attrs import define, field
from git import Repo


@define(auto_attribs=True, kw_only=True, order=True)
class ConfigManager:
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
        return {k: self._replace(value=v) for k, v in raw_config.items()}

    def _replace(self, value) -> Any:
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
        return self.config.get(section, {})


@define(auto_attribs=True, kw_only=True, order=True)
class LicenseManager:
    config: dict[str, str]

    @staticmethod
    def modify_file(file_path: Path, modifier_func) -> None:
        content: str = file_path.read_text()
        updated_content: Any = modifier_func(content)
        file_path.write_text(data=updated_content)

    @staticmethod
    def prepend_to_file(file_path: Path, content: str) -> None:
        LicenseManager.modify_file(
            file_path=file_path,
            modifier_func=lambda original: content + "\n" + original,
        )

    @staticmethod
    def update_copyright_year(text: str, current_year: int) -> str:
        return re.sub(
            pattern=r"© (\d{4})(-\d{4})?",
            repl=lambda m: f"© {m.group(1)}-{current_year}"
            if int(m.group(1)) < current_year
            else m.group(0),
            string=text,
        )

    def apply_files_and_headers(self, target_dir: Path) -> None:
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
    config: dict[str, str]
    latest_tag: str = field(init=False)
    repo: Repo = field(default=Repo(path="."))

    def __attrs_post_init__(self) -> None:
        try:
            self.latest_tag = self.repo.git.describe("--tags", "--abbrev=0")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.latest_tag = ""

    def bump_version(self, bump_type: str) -> str:
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
    config_manager: ConfigManager
    target_dir: Path = field(default=Path.cwd())
    license_manager: LicenseManager = field(default=None, init=False)

    def run(self) -> None:
        project_type: str = self.decide_project_type()
        if self.check_existing_files(project_type=project_type):
            self.setup_license_manager(project_type=project_type)
            if self.license_manager:
                self.license_manager.apply_files_and_headers(target_dir=self.target_dir)

            version_manager = VersionManager(config={})
            version_manager.bump_version(bump_type="patch")

    def decide_project_type(self) -> str:
        project_types: dict[str, str] = {"p": "personal", "w": "work"}
        while True:
            user_input: str = input(
                "Is this (p)ersonally produced or for (w)ork? (p/w): "
            ).lower()
            if user_input in project_types:
                return project_types[user_input]
            print("Invalid input. Please enter 'p' or 'w'.")

    def check_existing_files(self, project_type: str) -> bool:
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
