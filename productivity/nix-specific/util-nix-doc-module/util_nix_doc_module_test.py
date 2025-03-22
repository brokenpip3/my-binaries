import pytest
from unittest import mock
from util_nix_doc_module import parse_nix_module, generate_readme, process_nix_files_in_directory

@pytest.fixture(autouse=True)
def mock_logging():
    with mock.patch('logging.error') as mock_error, mock.patch('logging.info') as mock_info, mock.patch('logging.warning') as mock_warning:
        yield mock_info, mock_warning, mock_error

@pytest.fixture
def mock_nix_module():
    module_file = """
    dotfiles.superhero.time = lib.mkOption {
      description = ''
      this option will unlock the power to stop time
      '';
      type = lib.types.str;
      default = "why not";
    }

    dotfiles.superhero.time.traveler = lib.mkOption {
      description = ''
      this option will make you a timetraveler
      '';
      type = lib.types.int;
      default = 1;
    }
    """
    return module_file

def test_parse_nix_module_valid(mock_logging, mock_nix_module):
    mock_info, mock_warning, mock_error = mock_logging
    with mock.patch('builtins.open', mock.mock_open(read_data=mock_nix_module)), \
         mock.patch('os.path.exists', return_value=True):
        result = parse_nix_module('test_file.nix')

    assert 'dotfiles.superhero.time' in result
    assert result['dotfiles.superhero.time']['description'] == 'this option will unlock the power to stop time'
    assert result['dotfiles.superhero.time']['type'] == 'str'
    assert result['dotfiles.superhero.time']['default'] == '"why not"'

    assert 'dotfiles.superhero.time.traveler' in result
    assert result['dotfiles.superhero.time.traveler']['description'] == 'this option will make you a timetraveler'
    assert result['dotfiles.superhero.time.traveler']['type'] == 'int'
    assert result['dotfiles.superhero.time.traveler']['default'] == '1'

def test_parse_nix_module_file_not_found(mock_logging):
    mock_info, mock_warning, mock_error = mock_logging
    with mock.patch('os.path.exists', return_value=False):
        result = parse_nix_module('nonexistent_file.nix')

    assert result == {}
    mock_error.assert_called_once_with("File not found: nonexistent_file.nix")

def test_generate_readme(mock_nix_module):
    options = {
        'dotfiles.superhero.time': {
            'description': 'this option will unlock the power to stop time',
            'type': 'str',
            'default': '"why not"'
        },
        'dotfiles.superhero.time.traveler': {
            'description': 'this option will make you a timetraveler',
            'type': 'int',
            'default': '1'
        }
    }
    readme = generate_readme('module_name', options)
    assert "# module_name Module Options" in readme
    assert "| `dotfiles.superhero.time` | this option will unlock the power to stop time | str | \"why not\" |" in readme
    assert "| `dotfiles.superhero.time.traveler` | this option will make you a timetraveler | int | 1 |" in readme

def test_process_nix_files_in_directory_no_write(mock_logging, mock_nix_module):
    mock_info, mock_warning, mock_error = mock_logging
    with mock.patch('builtins.open', mock.mock_open(read_data=mock_nix_module)), \
         mock.patch('os.path.exists', return_value=True), \
         mock.patch('os.walk', return_value=[('test_dir', [], ['test_file.nix'])]), \
         mock.patch('logging.info') as mock_info:
        process_nix_files_in_directory('test_dir', write=False)

    mock_info.assert_any_call("parsing file: test_dir/test_file.nix")

def test_process_nix_files_in_directory_write(mock_logging, mock_nix_module):
    mock_info, mock_warning, mock_error = mock_logging
    with mock.patch('builtins.open', mock.mock_open(read_data=mock_nix_module)), \
         mock.patch('os.path.exists', return_value=True), \
         mock.patch('os.walk', return_value=[('test_dir', [], ['test_file.nix'])]), \
         mock.patch('logging.info') as mock_info, \
         mock.patch('builtins.open', mock.mock_open()) as mock_open:
        process_nix_files_in_directory('test_dir', write=True)
    mock_info.assert_any_call("parsing file: test_dir/test_file.nix")

def test_main_valid(mock_logging):
    with mock.patch('os.path.isdir', return_value=True), \
         mock.patch('util_nix_doc_module.process_nix_files_in_directory') as mock_process:
        with mock.patch('argparse.ArgumentParser.parse_args', return_value=mock.Mock(directory_path='test_dir', write=False)):
            from util_nix_doc_module import main
            main()
        mock_process.assert_called_once_with('test_dir', False)

def test_main_invalid_directory(mock_logging):
    mock_info, mock_warning, mock_error = mock_logging
    with mock.patch('os.path.isdir', return_value=False), \
         mock.patch('argparse.ArgumentParser.parse_args', return_value=mock.Mock(directory_path='invalid_dir', write=False)):
        from util_nix_doc_module import main
        main()
    mock_error.assert_called_once_with("directory not found: invalid_dir")
