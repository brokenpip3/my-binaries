#!/usr/bin/env python3
import pytest
from unittest import mock
import subprocess
import os
import json
import hashlib
import tempfile
import requests
from unittest.mock import patch, MagicMock
import tartufi


@pytest.fixture
def mock_subprocess():
    with mock.patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_requests():
    with mock.patch("requests.get") as mock_get:
        yield mock_get


@pytest.fixture
def mock_db():
    temp_db = tempfile.NamedTemporaryFile(suffix=".db").name
    conn = tartufi.setup_database(temp_db)
    yield conn
    conn.close()
    if os.path.exists(temp_db):
        os.remove(temp_db)


@pytest.fixture
def sample_repositories():
    return [
        {"name": "murdock", "pull_count": 1000, "description": "Daredevil Repository"},
        {
            "name": "nelson",
            "pull_count": 2000,
            "description": "Foggy Nelson Repository with a very long description that needs to be truncated",
        },
    ]


@pytest.fixture
def sample_tags():
    return [
        {
            "name": "latest",
            "last_updated": "2023-01-01T00:00:00Z",
            "full_size": 104857600,
        },
        {"name": "v1.0", "last_updated": "2022-12-31T00:00:00Z", "full_size": 52428800},
    ]


@pytest.fixture
def sample_findings():
    return [
        {
            "DetectorName": "AWS",
            "Redacted": "AKIA***",
            "Verified": True,
            "SourceMetadata": {"Data": {"Docker": {"file": "/etc/credentials"}}},
        },
        {
            "DetectorName": "Generic",
            "Redacted": "password***",
            "Verified": False,
            "SourceMetadata": {"Data": {"Docker": {"file": "/app/config.json"}}},
        },
    ]


def test_pcolor_with_color():
    with patch.dict(os.environ, {}, clear=True):
        result = tartufi.pcolor("kingpin")
        assert result == f"{tartufi.BROWN}kingpin{tartufi.RESET}"


def test_pcolor_no_color():
    with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=True):
        result = tartufi.pcolor("foggy")
        assert result == "foggy"


def test_setup_database(mock_db):
    cursor = mock_db.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='scan_results'"
    )
    assert cursor.fetchone() is not None


def test_get_image_hash():
    image_name = "defenders/daredevil:tag"
    expected_hash = hashlib.md5(image_name.encode()).hexdigest()
    assert tartufi.get_image_hash(image_name) == expected_hash


def test_check_image_scanned_found(mock_db):
    cursor = mock_db.cursor()
    cursor.execute(
        "INSERT INTO scan_results (image_hash, image_name, findings_count, findings_data) VALUES (?, ?, ?, ?)",
        ("natchioshash", "defenders/elektra:tag", 2, json.dumps([{"test": "data"}])),
    )
    mock_db.commit()

    result = tartufi.check_image_scanned(mock_db, "natchioshash")
    assert result is not None
    assert result[0] == "defenders/elektra:tag"
    assert result[1] == 2


def test_check_image_scanned_not_found(mock_db):
    result = tartufi.check_image_scanned(mock_db, "poindexter")
    assert result is None


def test_save_scan_result(mock_db):
    findings = [{"test": "castle1"}, {"test": "castle2"}]
    tartufi.save_scan_result(mock_db, "castlehash", "defenders/punisher:tag", findings)

    cursor = mock_db.cursor()
    cursor.execute(
        "SELECT image_name, findings_count, findings_data FROM scan_results WHERE image_hash = ?",
        ("castlehash",),
    )
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "defenders/punisher:tag"
    assert result[1] == 2
    assert json.loads(result[2]) == findings


def test_save_scan_result_empty_findings(mock_db):
    tartufi.save_scan_result(mock_db, "pagehash", "defenders/karen:tag", [])

    cursor = mock_db.cursor()
    cursor.execute(
        "SELECT image_name, findings_count, findings_data FROM scan_results WHERE image_hash = ?",
        ("pagehash",),
    )
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "defenders/karen:tag"
    assert result[1] == 0
    assert result[2] == "[]"


@patch("subprocess.run")
def test_get_docker_hub_token_success(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "token123\n"
    mock_run.return_value = mock_result

    with patch.dict(
        os.environ,
        {
            "UTIL_SECURITY_TARTUFI_PASS": "fisk_pass",
            "UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN": "fisk_entry",
        },
    ):
        token = tartufi.get_docker_hub_token()

    assert token == "token123"
    mock_run.assert_called_once_with(
        ["fisk_pass", "show", "fisk_entry"], capture_output=True, text=True, check=True
    )


@patch("subprocess.run")
def test_get_docker_hub_token_subprocess_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "fisk_pass")

    with patch.dict(
        os.environ,
        {
            "UTIL_SECURITY_TARTUFI_PASS": "fisk_pass",
            "UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN": "fisk_entry",
        },
    ):
        with patch("sys.exit") as mock_exit:
            tartufi.get_docker_hub_token()
            mock_exit.assert_called_once_with(1)


@patch("subprocess.run")
def test_get_docker_hub_token_command_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError()

    with patch.dict(
        os.environ,
        {
            "UTIL_SECURITY_TARTUFI_PASS": "vanessa_pass",
            "UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN": "vanessa_entry",
        },
    ):
        with patch("sys.exit") as mock_exit:
            tartufi.get_docker_hub_token()
            mock_exit.assert_called_once_with(1)


@patch("requests.get")
def test_get_repositories_success(mock_get, sample_repositories):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": sample_repositories}
    mock_get.return_value = mock_response

    result = tartufi.get_repositories("stick", "sticktoken")

    assert result == sample_repositories
    mock_get.assert_called_once_with(
        "https://hub.docker.com/v2/repositories/stick/?page_size=100",
        headers={"Authorization": "JWT sticktoken"},
    )


@patch("requests.get")
def test_get_repositories_error(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Error")

    with patch("sys.exit") as mock_exit:
        tartufi.get_repositories("owlsley", "lelandtoken")
        mock_exit.assert_called_once_with(1)


@patch("requests.get")
def test_get_tags_success(mock_get, sample_tags):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": sample_tags}
    mock_get.return_value = mock_response

    result = tartufi.get_tags("melvin", "potter", "melvintoken")

    assert result == sample_tags
    mock_get.assert_called_once_with(
        "https://hub.docker.com/v2/repositories/melvin/potter/tags/?page_size=100",
        headers={"Authorization": "JWT melvintoken"},
    )


@patch("requests.get")
def test_get_tags_error(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Error")

    result = tartufi.get_tags("wesley", "wesley", "wesleytoken")
    assert result == []


@patch("subprocess.run")
def test_scan_docker_image_success(mock_run, sample_findings):
    mock_result = MagicMock()
    mock_result.stdout = "\n".join(json.dumps(finding) for finding in sample_findings)
    mock_run.return_value = mock_result

    result = tartufi.scan_docker_image("brett/mahoney:tag")

    assert result["image"] == "brett/mahoney:tag"
    assert result["success"] is True
    assert result["findings"] == sample_findings


@patch("subprocess.run")
def test_scan_docker_image_empty_output(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_run.return_value = mock_result

    result = tartufi.scan_docker_image("midland/tower:tag")

    assert result["image"] == "midland/tower:tag"
    assert result["success"] is True
    assert result["findings"] == []


@patch("subprocess.run")
def test_scan_docker_image_exception(mock_run):
    mock_run.side_effect = Exception("Blake error")

    result = tartufi.scan_docker_image("blake/tower:tag")

    assert result["image"] == "blake/tower:tag"
    assert result["success"] is False
    assert "error" in result
    assert result["findings"] == []


def test_extract_secret_details(sample_findings):
    details = tartufi.extract_secret_details(sample_findings[0])

    assert details["detector"] == "AWS"
    assert details["redacted"] == "AKIA***"
    assert details["verified"] is True
    assert details["file_path"] == "/etc/credentials"


def test_extract_secret_details_missing_fields():
    finding = {"DetectorName": "Temple"}
    details = tartufi.extract_secret_details(finding)

    assert details["detector"] == "Temple"
    assert details["redacted"] == ""
    assert details["verified"] is False
    assert details["file_path"] == "Unknown path"


def test_format_finding_details_empty():
    result = tartufi.format_finding_details([])
    assert result == ""


def test_format_finding_details_single(sample_findings):
    result = tartufi.format_finding_details([sample_findings[0]])
    assert "AWS:AKIA*** (✓)" in result


def test_format_finding_details_multiple(sample_findings):
    result = tartufi.format_finding_details(sample_findings)
    assert "AWS:AKIA*** (✓)" in result
    assert "Generic:password*** (?)" in result


def test_format_finding_details_truncation():
    findings = [
        {"DetectorName": f"Hand{i}", "Redacted": f"secret{i}", "Verified": i % 2 == 0}
        for i in range(5)
    ]
    result = tartufi.format_finding_details(findings)
    assert "..." in result


@patch("builtins.print")
def test_display_summary_with_findings(mock_print, sample_findings):
    scan_results = [
        {"image": "nobu/daredevil:tag", "success": True, "findings": sample_findings}
    ]

    with patch("tartufi.display_detailed_findings") as mock_display:
        tartufi.display_summary(scan_results)
        mock_display.assert_called_once_with(scan_results)


@patch("builtins.print")
def test_display_summary_no_findings(mock_print):
    scan_results = [{"image": "madame/gao:tag", "success": True, "findings": []}]

    with patch("tartufi.display_detailed_findings") as mock_display:
        tartufi.display_summary(scan_results)
        mock_display.assert_not_called()


@patch("builtins.print")
def test_display_detailed_findings(mock_print, sample_findings):
    scan_results = [
        {"image": "murakami/hand:tag", "success": True, "findings": sample_findings},
        {"image": "murakami/five:tag", "success": True, "findings": []},
    ]

    tartufi.display_detailed_findings(scan_results)
    assert mock_print.call_count > 0


@patch("builtins.print")
def test_display_repositories_empty(mock_print):
    tartufi.display_repositories([])
    mock_print.assert_any_call("no repositories found for this user")


@patch("builtins.print")
def test_display_repositories(mock_print, sample_repositories):
    tartufi.display_repositories(sample_repositories)
    assert mock_print.call_count > 0


@patch("builtins.print")
def test_display_tags_empty(mock_print):
    tartufi.display_tags([], "sowande")
    mock_print.assert_any_call("no tags found for sowande")


@patch("builtins.print")
def test_display_tags(mock_print, sample_tags):
    tartufi.display_tags(sample_tags, "bakuto")
    assert mock_print.call_count > 0


@patch("builtins.input")
def test_get_user_selection_all(mock_input):
    mock_input.return_value = "all"
    result = tartufi.get_user_selection(3, "Select:")
    assert result == [0, 1, 2]


@patch("builtins.input")
def test_get_user_selection_empty(mock_input):
    mock_input.return_value = ""
    result = tartufi.get_user_selection(3, "Select:")
    assert result == []


@patch("builtins.input")
def test_get_user_selection_single(mock_input):
    mock_input.return_value = "2"
    result = tartufi.get_user_selection(3, "Select:")
    assert result == [1]


@patch("builtins.input")
def test_get_user_selection_multiple(mock_input):
    mock_input.return_value = "1,3"
    result = tartufi.get_user_selection(3, "Select:")
    assert result == [0, 2]


@patch("builtins.input")
def test_get_user_selection_range(mock_input):
    mock_input.return_value = "1-3"
    result = tartufi.get_user_selection(5, "Select:")
    assert result == [0, 1, 2]


@patch("builtins.input")
def test_get_user_selection_invalid_retry(mock_input):
    mock_input.side_effect = ["invalid", "1"]
    result = tartufi.get_user_selection(3, "Select:")
    assert result == [0]


@patch("builtins.input")
def test_get_user_selection_out_of_range(mock_input):
    mock_input.side_effect = ["5", "1"]
    result = tartufi.get_user_selection(3, "Select:")
    assert result == [0]
