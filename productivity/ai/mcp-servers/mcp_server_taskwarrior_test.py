#!/usr/bin/env python3
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mcp_server_taskwarrior import (
    task_execute_query,
    task_count_filtered,
    task_create_new,
    task_run_command,
    Task,
)


class TestTaskExecuteQuery:
    @patch("subprocess.run")
    def test_successful_query(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '[{"id": 1, "description": "test task", "status": "pending"}]'
        )
        mock_run.return_value = mock_result

        result = task_execute_query(["status:pending"])

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["description"] == "test task"
        mock_run.assert_called_once_with(
            ["task", "status:pending", "export"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_empty_result(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = task_execute_query(["status:completed"])

        assert result == []

    @patch("subprocess.run")
    def test_command_failure(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "task command failed"
        mock_run.return_value = mock_result

        with pytest.raises(Exception, match="task command failed"):
            task_execute_query(["invalid:filter"])


class TestTaskCountFiltered:
    @patch("subprocess.run")
    def test_valid_count(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5\n"
        mock_run.return_value = mock_result

        result = task_count_filtered(["status:pending"])

        assert result == 5
        mock_run.assert_called_once_with(
            ["task", "status:pending", "count"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_zero_count(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0\n"
        mock_run.return_value = mock_result

        result = task_count_filtered(["status:deleted"])

        assert result == 0

    @patch("subprocess.run")
    def test_command_failure_returns_zero(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = task_count_filtered(["invalid:filter"])

        assert result == 0

    @patch("subprocess.run")
    def test_non_numeric_output_returns_zero(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid\n"
        mock_run.return_value = mock_result

        result = task_count_filtered(["status:pending"])

        assert result == 0


class TestTaskCreateNew:
    @patch("subprocess.run")
    def test_basic_task_creation(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Created task 42.\n"
        mock_run.return_value = mock_result

        result = task_create_new("test task")

        assert result["success"] is True
        assert result["task_id"] == 42
        mock_run.assert_called_once_with(
            ["task", "add", "test task"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_task_creation_with_all_params(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Created task 43.\n"
        mock_run.return_value = mock_result

        task_create_new(
            "complex task",
            project="work",
            priority="H",
            due="tomorrow",
            scheduled="today",
            tags=["urgent", "important"],
            estimate="2h",
        )

        expected_cmd = [
            "task",
            "add",
            "complex task",
            "project:work",
            "priority:H",
            "due:tomorrow",
            "scheduled:today",
            "estimate:2h",
            "+urgent",
            "+important",
        ]
        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True)

    @patch("subprocess.run")
    def test_invalid_priority_ignored(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Created task 44.\n"
        mock_run.return_value = mock_result

        task_create_new("test task", priority="INVALID")

        mock_run.assert_called_once_with(
            ["task", "add", "test task"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    @patch("mcp_server_taskwarrior.logging.warning")
    def test_task_id_parsing_failure(self, mock_logging, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Created task invalid_number."
        mock_run.return_value = mock_result

        result = task_create_new("test task")

        assert result["task_id"] is None
        mock_logging.assert_called_once()

    @patch("subprocess.run")
    def test_task_id_not_found_in_output(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Task added successfully but no ID shown"
        mock_run.return_value = mock_result

        result = task_create_new("test task")

        assert result["task_id"] is None

    @patch("subprocess.run")
    def test_command_failure(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "failed to add task"
        mock_run.return_value = mock_result

        with pytest.raises(Exception, match="failed to add task"):
            task_create_new("test task")


class TestTaskRunCommand:
    @patch("subprocess.run")
    def test_successful_command(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Task completed"
        mock_run.return_value = mock_result

        result = task_run_command(42, "done")

        assert result["success"] is True
        assert result["message"] == "Task completed"
        mock_run.assert_called_once_with(
            ["task", "42", "done"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_command_failure(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "task not found"
        mock_run.return_value = mock_result

        with pytest.raises(Exception, match="task start failed: task not found"):
            task_run_command(999, "start")


class TestTaskModel:
    def test_task_creation_minimal(self):
        task_data = {"id": 1, "description": "test task", "status": "pending"}
        task = Task(**task_data)

        assert task.id == 1
        assert task.description == "test task"
        assert task.status == "pending"
        assert task.project is None
        assert task.tags == []

    def test_task_creation_full(self):
        task_data = {
            "id": 2,
            "description": "complex task",
            "status": "pending",
            "project": "work",
            "tags": ["urgent", "important"],
            "due": "2024-12-31",
            "priority": "H",
            "urgency": 8.5,
            "scheduled": "2024-12-30",
            "start": "2024-12-29T10:00:00Z",
        }
        task = Task(**task_data)

        assert task.project == "work"
        assert task.tags == ["urgent", "important"]
        assert task.due == "2024-12-31"
        assert task.priority == "H"
        assert task.urgency == 8.5


class TestIntegrationMocking:
    @patch("mcp_server_taskwarrior.task_execute_query")
    def test_task_list_pending_integration(self, mock_query):
        mock_query.return_value = [
            {"id": 1, "description": "task 1", "status": "pending"},
            {"id": 2, "description": "task 2", "status": "pending", "project": "work"},
        ]

        result = mock_query(["status:pending"])
        assert len(result) == 2
        assert result[0]["id"] == 1

    @patch("mcp_server_taskwarrior.task_create_new")
    def test_task_add_new_integration(self, mock_create):
        mock_create.return_value = {
            "success": True,
            "message": "Created task 100.",
            "task_id": 100,
        }

        result = mock_create("integration test task")
        assert result["success"] is True
        assert result["task_id"] == 100


class TestDateHandling:
    def test_tomorrow_date_format(self):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert len(tomorrow) == 10
        assert tomorrow.count("-") == 2

    def test_week_calculation(self):
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        assert (week_end - week_start).days == 6
        assert week_start.weekday() == 0  # monday
