#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
from bitsync import (
    verify_bitwarden_binary,
    authenticate_bitwarden,
    fetch_pass_entries,
    get_pass_details,
    insert_or_update_bitwarden,
    build_item_data,
)


@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_getpass():
    with patch("bitsync.getpass") as mock_getpass:
        yield mock_getpass


def test_verify_bitwarden_binary_success(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    verify_bitwarden_binary()
    mock_subprocess_run.assert_called_once_with(
        ["bw", "--version"], capture_output=True, text=True
    )


def test_verify_bitwarden_binary_failure(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="Error")
    with pytest.raises(RuntimeError, match="Bitwarden cli binary not found"):
        verify_bitwarden_binary()


def test_authenticate_bitwarden_success(mock_subprocess_run, mock_getpass):
    mock_getpass.return_value = "master_password"
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout="my_super_uber_secret_api_key"
    )
    session = authenticate_bitwarden()
    assert session == "my_super_uber_secret_api_key"
    mock_subprocess_run.assert_called_once_with(
        ["bw", "unlock", "--raw"],
        input="master_password",
        text=True,
        capture_output=True,
    )


def test_authenticate_bitwarden_failure(mock_subprocess_run, mock_getpass):
    mock_getpass.return_value = "master_password"
    mock_subprocess_run.return_value = MagicMock(
        returncode=1, stderr="Invalid password"
    )
    with pytest.raises(RuntimeError, match="Bitwarden authentication failed."):
        authenticate_bitwarden()


def test_fetch_pass_entries_success(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(
        returncode=0,
        stdout="deathstar_password.gpg\nbank_account_password.gpg\nI_lost_my_keys.txt\n",
    )
    entries = fetch_pass_entries()
    assert entries == ["deathstar_password.gpg", "bank_account_password.gpg"]
    mock_subprocess_run.assert_called_once_with(
        ["pass", "git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
    )


def test_fetch_pass_entries_failure(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="Error")
    with pytest.raises(RuntimeError, match="Failed to retrieve pass entries."):
        fetch_pass_entries()


def test_get_pass_details_success(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout="mypassword\nuser: myuser\n"
    )
    password, username = get_pass_details("deathstar_password.gpg")
    assert password == "mypassword"
    assert username == "myuser"
    mock_subprocess_run.assert_called_once_with(
        ["pass", "show", "deathstar_password"],
        capture_output=True,
        text=True,
    )


def test_get_pass_details_no_username(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="mypassword\n")
    password, username = get_pass_details("deathstar_password.gpg")
    assert password == "mypassword"
    assert username is None


def test_get_pass_details_failure(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="Error")
    password, username = get_pass_details("deathstar_password.gpg")
    assert password == ""
    assert username == ""


def test_build_item_data():
    item_data = build_item_data("juventus.com", "mypassword", "myuser")
    assert item_data["name"] == "juventus.com"
    assert item_data["login"]["password"] == "mypassword"
    assert item_data["login"]["username"] == "myuser"
    assert item_data["login"]["uris"] == [{"match": 0, "uri": "https://juventus.com"}]


def test_insert_or_update_bitwarden_create(mock_subprocess_run):
    session = "my_super_uber_secret_api_key"
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout="[]"),
        MagicMock(returncode=0),
    ]

    insert_or_update_bitwarden("juventus.com.gpg", "mypassword", "myuser", session)

    mock_subprocess_run.assert_any_call(
        f"bw list items --search 'juventus.com' --session {session}",
        shell=True,
        capture_output=True,
        text=True,
    )


def test_insert_or_update_bitwarden_update(mock_subprocess_run):
    session = "my_super_uber_secret_api_key"
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout='[{"id": "123"}]'),
        MagicMock(returncode=0),
    ]

    insert_or_update_bitwarden("juventus.com.gpg", "mypassword", "myuser", session)

    mock_subprocess_run.assert_any_call(
        f"bw list items --search 'juventus.com' --session {session}",
        shell=True,
        capture_output=True,
        text=True,
    )
