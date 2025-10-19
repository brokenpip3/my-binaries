#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import util_task_open as uto

@pytest.mark.parametrize("env_value,expected", [
    ("/custom/path/taskrc", Path("/custom/path/taskrc")),
    (None, Path("/homeless-shelter/.config/task/taskrc"))
])
def test_get_taskrc_path(env_value, expected):
    with patch.dict(os.environ, {"TASKRC": env_value} if env_value else {}, clear=True):
        with patch("pathlib.Path.home", return_value=Path("/homeless-shelter")):
            assert uto.get_taskrc_path() == expected

@pytest.mark.parametrize("file_content,expected", [
    ("taskopen.browser=firefox\nother=value", {"taskopen.browser": "firefox"}),
    ("", {}),
    ("bla bla bla", {})
])
def test_read_taskrc_config(file_content, expected):
    m = mock_open(read_data=file_content)
    with patch("builtins.open", m), patch("pathlib.Path.exists", return_value=True):
        assert uto.read_taskrc_config() == expected

@pytest.mark.parametrize("task_list,fzf_output,expected_id", [
    ([{"id":1,"description":"buy a book around pytest"}], "1 |          | desc1\n", "1"),
    ([{"id":42,"description":"and around the builtin marks","project":"pytest"}], "42 | proj      | task\n", "42"),
])
def test_fzf_select_task(task_list, fzf_output, expected_id):
    task_json = json.dumps(task_list)
    mock_result_task = MagicMock(returncode=0, stdout=task_json)
    mock_result_fzf = MagicMock(returncode=0, stdout=fzf_output)
    with patch("subprocess.run", side_effect=[mock_result_task, mock_result_fzf]), \
         patch("os.get_terminal_size", return_value=os.terminal_size((80, 24))):
        assert uto.fzf_select_task() == expected_id

@pytest.mark.parametrize("task_id,task_data", [
    ("1",[{"id":1,"description":"this is a great task that you will never do"}]),
])
def test_get_task_data(task_id, task_data):
    mock_result = MagicMock(returncode=0, stdout=json.dumps(task_data))
    with patch("subprocess.run", return_value=mock_result):
        assert uto.get_task_data(task_id) == task_data[0]

@pytest.mark.parametrize("task_data,tmux_env,expected", [
    ({"neovim_file":"file.py","neovim_line":10,"neovim_repo":"/tmp","id":1}, True, True),
    ({"id":1}, False, False),
])
def test_handle_neovim(task_data, tmux_env, expected):
    env = {"TMUX":"1"} if tmux_env else {}
    with patch.dict(os.environ, env, clear=True), patch("subprocess.run") as m, patch("builtins.print"):
        assert uto.handle_neovim(task_data, {}) == expected

@pytest.mark.parametrize("annotations,config,expected_called", [
    ([{"description":"https://juventus.com"}], {"taskopen.browser":"echo"}, True),
    ([{"description":"not a url but sempre forza juve"}], {}, False),
])
def test_handle_url(annotations, config, expected_called):
    task_data = {"annotations": annotations}
    with patch("subprocess.run") as m, patch("builtins.print"):
        assert uto.handle_url(task_data, config) == expected_called

@pytest.mark.parametrize("task_id", ["1", "42"])
def test_show_task_info(task_id):
    with patch("builtins.print") as mp, patch("subprocess.run") as sp:
        uto.show_task_info(task_id)
        mp.assert_called_with("no actionable data found")
        sp.assert_called_once()

@pytest.mark.parametrize("argv,fzf_result,get_data_result,neovim_result,url_result,expected_exit", [
    (["util_task_open.py"], "1", {"id":1}, True, False, None),
    (["util_task_open.py"], None, {"id":1}, True, False, SystemExit),
    (["util_task_open.py"], "1", {"id":1}, False, True, None),
    (["util_task_open.py"], "1", {"id":1}, False, False, None),
    (["util_task_open.py","42"], None, {"id":42}, False, False, None),
    (["util_task_open.py","too","many"], None, {}, False, False, SystemExit)
])
def test_main(argv, fzf_result, get_data_result, neovim_result, url_result, expected_exit):
    def fake_fzf(): return fzf_result
    def fake_get_data(task_id): return get_data_result
    with patch.object(sys, "argv", argv), \
         patch("util_task_open.read_taskrc_config", return_value={}), \
         patch("util_task_open.fzf_select_task", side_effect=fake_fzf), \
         patch("util_task_open.get_task_data", side_effect=fake_get_data), \
         patch("util_task_open.handle_neovim", return_value=neovim_result), \
         patch("util_task_open.handle_url", return_value=url_result), \
         patch("util_task_open.show_task_info") as show_info:
        if expected_exit is SystemExit:
            with pytest.raises(SystemExit):
                uto.main()
        else:
            uto.main()
            if not (neovim_result or url_result):
                show_info.assert_called_once()
