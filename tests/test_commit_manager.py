from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock
from commit_manager import ConfigManager, LicenseManager, VersionManager, GitHookManager
from pathlib import Path
import tomllib


class TestConfigManager(TestCase):

    def setUp(self) -> None:
        self.mock_config_data = {
            'placeholders': {'name_placeholder': 'Jack Johnson'},
            'git_defaults': {'defaults_dir': '..gitdefaults/'},
            'work': {{'script': 'foo'}, {'license': 'bar'}, {'intent': 'baz'}},
            'personal': {{'script': 'foo'}, {'license': 'bar'}}
        }


    @patch('commit_manager.Path.exists')
    def test_init_valid_path(self, mock_exists) -> None:
        mock_exists.return_value = True
        cm = ConfigManager(config_path=Path('..config.toml'))
        self.assertEqual(first=cm.config_path, second=Path('..config.toml'))

    @patch('commit_manager.Path.exists')
    def test_init_invalid_path(self, mock_exists) -> None:
        mock_exists.return_value = False
        with self.assertRaises(expected_exception=FileNotFoundError):
            ConfigManager(config_path=Path('invalid_path.toml'))

    @patch('commit_manager.tomllib.load')
    def test_load_config(self, mock_load) -> None:
        mock_load.return_value = self.mock_config_data
        cm = ConfigManager()
        self.assertEqual(first=cm.load_config(), second=self.mock_config_data)

    def test_replace_placeholders(self) -> None:
        cm = ConfigManager()
        raw_config: dict[str, dict[str, str]] = {'section': {'key': 'NAME_PLACEHOLDER'}}
        cm.name_placeholder = 'John Doe'
        updated_config: dict = cm.replace_placeholders(raw_config=raw_config)
        self.assertEqual(first=updated_config, second={'section': {'key': 'John Doe'}})

    def test_get_section(self) -> None:
        cm = ConfigManager()
        cm.config = self.mock_config_data
        self.assertEqual(first=cm.get_section(section='section1'), second={'key1': 'value1'})


class TestLicenseManager(TestCase):

    def setUp(self) -> None:
        self.config: dict[str, str] = {
            'license': 'Test License',
            'script': 'Test Header',
            'intent': 'Test Intent'
        }
        self.lm = LicenseManager(config=self.config)

    def test_init(self) -> None:
        self.assertEqual(first=self.lm.config, second=self.config)

    @patch("builtins.open", new_callable=mock_open)
    def test_prepend_to_file(self, mock_file) -> None:
        LicenseManager.prepend_to_file(file_path='.', content='content')
        mock_file.assert_called_once_with('some_path', 'r+')
        file_handle = mock_file()
        file_handle.read.assert_called_once()
        file_handle.write.assert_called_once_with('content\n')

    def test_update_copyright_year(self):
        original_text = "© 2020"
        current_year = 2023
        updated_text: str = LicenseManager.update_copyright_year(
            text=original_text, current_year=current_year)
        self.assertEqual(first=updated_text, second="© 2020-2023")

    @patch('commit_manager.Path.glob')
    @patch("builtins.open", new_callable=mock_open, read_data="existing content")
    def test_apply_files_and_headers(self, mock_file, mock_glob) -> None:
        mock_glob.return_value = ['file1.py', 'file2.py']
        self.lm.apply_files_and_headers(target_dir='target_dir', config_section=self.config)
        # Two files, each opened once for reading and once for writing
        self.assertEqual(first=mock_file.call_count, second=4)


class TestVersionManager(TestCase):

    def setUp(self) -> None:
        self.config: dict[str, str] = {
            'versioning_type': 'semver'
        }
        self.vm = VersionManager(config=self.config)

    def test_init(self) -> None:
        self.assertEqual(first=self.vm.config, second=self.config)

    @patch('commit_manager.subprocess.getoutput')
    @patch('commit_manager.subprocess.run')
    @patch('commit_manager.VersionManager.request_bump_type')
    def test_bump_version(self, mock_request_bump_type, mock_run, mock_getoutput) -> None:
        mock_getoutput.return_value = 'v1.0.0'
        mock_request_bump_type.return_value = 'minor'
        new_version = self.vm.bump_version(target_dir='target_dir')
        mock_run.assert_called_once_with(['git', 'tag', 'v1.1.0'])
        self.assertEqual(first=new_version, second='v1.1.0')

    @patch('commit_manager.input')
    def test_request_bump_type(self, mock_input) -> None:
        mock_input.return_value = 'major'
        bump_type = self.vm.request_bump_type(latest_tag='v1.0.0')
        self.assertEqual(first=bump_type, second='major')


class TestGitHookManager(TestCase):

    def setUp(self) -> None:
        self.config_manager = MagicMock(spec=ConfigManager)

    @patch('commit_manager.VersionManager')
    def test_init(self, mock_version_manager) -> None:
        gm = GitHookManager(config_manager=self.config_manager)
        self.assertEqual(first=gm.config_manager, second=self.config_manager)
        self.assertIsInstance(obj=gm.version_manager, cls=mock_version_manager)

    @patch('commit_manager.input')
    def test_decision_point(self, mock_input) -> None:
        mock_input.return_value = 'p'
        gm = GitHookManager(config_manager=self.config_manager)
        result = gm.decision_point()
        self.assertEqual(first=result, second='p')

    def test_check_existing_files(self) -> None:
        gm = GitHookManager(config_manager=self.config_manager)
        # You'll need to mock some more stuff here to fully test this method

    @patch('commit_manager.copytree')
    @patch('commit_manager.Path.iterdir')
    def test_copy_git_defaults(self, mock_iterdir, mock_copytree):
        mock_iterdir.return_value = ['file1', 'file2']
        gm = GitHookManager(config_manager=self.config_manager)
        gm.copy_git_defaults(target_dir='target', defaults_dir='defaults')
        # Assuming 2 files need to be copied
        self.assertEqual(first=mock_copytree.call_count, second=2)

    @patch('commit_manager.GitHookManager.decision_point')
    @patch('commit_manager.GitHookManager.check_existing_files')
    @patch('commit_manager.VersionManager')
    def test_run(self, mock_version_manager, mock_check_existing_files, mock_decision_point) -> None:
        mock_decision_point.return_value = 'p'
        mock_check_existing_files.return_value = True
        gm = GitHookManager(config_manager=self.config_manager)
        gm.run(target_dir='target_dir')
