from unittest.mock import patch, MagicMock
import json
import requests
import subprocess
from _logseq import (
    grab_todos_from_logseq,
    extract_priority,
    extract_marker,
    extract_project_from_content,
    extract_project_from_page,
    extract_schedule,
    extract_tags_from_content,
    remove_unwanted,
    translate_todo,
    main,
    create_logseq_todo,
    translate_taskwarrior,
    update_logseq_todo,
)
from _tasklib import fetch_existing_tasks
from _youtrack import (
    update_youtrack_issue,
    get_youtrack_issues,
)
from util_task_youtrack_sync import sync_task_with_youtrack

GENERIC_TODO = {
    "id": "1",
    "uuid": "rtr-3433-ddsds-121",
    "page": {"name": "projects/stufftodo/butwhen"},
    "content": "TODO [#A] Sample task #tag1 #tag2\nSCHEDULED: <2025-01-09 Thu>",
}


def test_grab_todos_from_logseq():
    with patch("_logseq.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = [GENERIC_TODO]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        todos = grab_todos_from_logseq()
        assert len(todos) == 1
        assert todos[0] == GENERIC_TODO


def test_fetch_existing_tasks():
    with patch("_logseq.subprocess.run") as mock_run:
        mock_run.return_value.stdout = json.dumps([{"id": "1", "project": "test"}])
        tasks = fetch_existing_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "1"


def test_extract_priority():
    content, priority = extract_priority("[#B] Do something")
    assert content == "Do something"
    assert priority == "M"

    content, priority = extract_priority("No priority task")
    assert content == "No priority task"
    assert priority is None


def test_extract_marker():
    content, marker = extract_marker("TODO Finish task")
    assert content == "Finish task"
    assert marker == "TODO"

    content, marker = extract_marker("Completed task")
    assert content == "Completed task"
    assert marker is None


def test_extract_project_from_content():
    content, project = extract_project_from_content(
        "Some content with [[projects/sample_project]]"
    )
    assert content == "Some content with"
    assert project == "sample_project"

    content, project = extract_project_from_content("No project here")
    assert content == "No project here"
    assert project is None

    content, project = extract_project_from_content(
        "Some content with [[projects/stufftodo/butwhen]]"
    )
    assert content == "Some content with"
    assert project == "stufftodo/butwhen"


def test_extract_project_from_page():
    project = extract_project_from_page("projects/sample_project")
    assert project == "sample_project"

    project = extract_project_from_page("some_other_page")
    assert project is None


def test_extract_schedule():
    content, schedule = extract_schedule("TODO Task\nSCHEDULED: <2025-01-09 Thu>")
    assert content == "TODO Task"
    assert schedule == "2025-01-09 Thu"

    content, schedule = extract_schedule("No schedule here")
    assert content == "No schedule here"
    assert schedule is None


def test_extract_tags_from_content():
    content, tags = extract_tags_from_content("This is a task #urgent #home")
    assert content == "This is a task"
    assert tags == ["urgent", "home"]

    content, tags = extract_tags_from_content("No tags here")
    assert content == "No tags here"
    assert tags == []


def test_remove_unwanted():
    cleaned_content = remove_unwanted("Task details :LOGBOOK: some details :END:")
    assert cleaned_content == "Task details"


def test_translate_todo():
    translated = translate_todo(GENERIC_TODO)
    assert translated[1] == "project:stufftodo.butwhen"
    assert translated[2] == "priority:H"
    assert translated[3] == "tags:tag1,tag2"
    assert translated[4] == "schedule:2025-01-09 Thu"
    assert translated[5] == "logseq_id:1"
    assert translated[6] == "logseq_uuid:rtr-3433-ddsds-121"
    assert translated[7] == "logseq_page:projects/stufftodo/butwhen"


def test_translate_todo_with_no_project():
    todo_with_no_project = {
        "id": "2",
        "uuid": "def-5678",
        "page": {"name": "journals/2023"},
        "content": "TODO [#B] Another task",
    }
    translated = translate_todo(todo_with_no_project)
    assert translated[0] == "Another task"
    assert translated[1] == ""
    assert translated[2] == "priority:M"
    assert translated[3] == ""
    assert translated[4] == ""
    assert translated[5] == "logseq_id:2"
    assert translated[6] == "logseq_uuid:def-5678"
    assert translated[7] == "logseq_page:journals/2023"


def test_extract_priority_invalid_format():
    content, priority = extract_priority("[#D] Invalid priority task")
    assert content == "[#D] Invalid priority task"
    assert priority is None


def test_extract_tags_from_content_edge_cases():
    content, tags = extract_tags_from_content("#tag1 #tag2 Task content")
    assert content == "Task content"
    assert tags == ["tag1", "tag2"]

    content, tags = extract_tags_from_content("Task content #tag1")
    assert content == "Task content"
    assert tags == ["tag1"]

    content, tags = extract_tags_from_content("No tags here")
    assert content == "No tags here"
    assert tags == []


def test_extract_marker_variations():
    content, marker = extract_marker("DOING Finish task")
    assert content == "Finish task"
    assert marker == "DOING"

    content, marker = extract_marker("Completed task")
    assert content == "Completed task"
    assert marker is None


def test_main_function_skip_existing_task():
    with patch("_logseq.fetch_existing_tasks") as mock_fetch:
        mock_fetch.return_value = [{"logseq_uuid": "rtr-3433-ddsds-121"}]
        with patch("_logseq.grab_todos_from_logseq") as mock_grab:
            mock_grab.return_value = [GENERIC_TODO]

            with patch("_logseq.subprocess.run") as mock_run:
                result = mock_run.return_value
                result.returncode = 0
                main()

        mock_run.assert_not_called()


def test_create_logseq_todo_success():
    with patch("_logseq.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": "new-task-uuid"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = create_logseq_todo("TODO Sample Task", "test-page")
        assert result["uuid"] == "new-task-uuid"


def test_create_logseq_todo_failure():
    with patch("_logseq.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Error"
        )
        mock_post.return_value = mock_response

        result = create_logseq_todo("TODO Sample Task", "test-page")
        assert result is None


def test_translate_taskwarrior_with_all_fields():
    task_data = {
        "description": "Sample task",
        "priority": "M",
        "project": "test.project",
        "tags": ["tag1", "tag2"],
        "scheduled": "20250102T230000Z",
    }
    result = translate_taskwarrior(task=task_data)
    assert "TODO [#B] Sample task" in result
    assert "[#B]" in result
    assert "#tag1" in result
    assert "#tag2" in result
    assert "SCHEDULED: <2025-01-02 Thu>" in result


def test_translate_taskwarrior_no_priority():
    task_data = {
        "description": "No priority task",
        "project": "test.project",
    }
    result = translate_taskwarrior(task=task_data)
    assert "TODO No priority task" in result
    assert "[#]" not in result


def test_translate_taskwarrior_no_tags():
    task_data = {
        "description": "Task without any tag",
        "project": "test.project",
    }
    result = translate_taskwarrior(task=task_data)
    assert "TODO Task without any tag" in result
    assert "#tag" not in result


def test_translate_taskwarrior_without_scheduled_date():
    task_data = {
        "description": "Task without a scheduled date",
        "project": "test.project",
    }
    result = translate_taskwarrior(task_data)
    assert "TODO Task without a scheduled date" in result
    assert "SCHEDULED:" not in result


def test_translate_taskwarrior_without_project():
    task_data = {
        "description": "Task without a project",
        "tags": ["tag1", "tag2"],
    }
    result = translate_taskwarrior(task_data)
    assert "TODO Task without a project" in result
    assert "[#]" not in result


def test_translate_todo_with_missing_fields():
    todo_with_missing_fields = {
        "id": "3",
        "uuid": "ghi-9012",
        "page": {"name": "random_page"},
        "content": "TODO Sample task without full data",
    }

    translated = translate_todo(todo_with_missing_fields)
    assert translated[0] == "Sample task without full data"
    assert translated[1] == ""
    assert translated[2] == ""
    assert translated[3] == ""
    assert translated[4] == ""
    assert translated[5] == "logseq_id:3"
    assert translated[6] == "logseq_uuid:ghi-9012"
    assert translated[7] == "logseq_page:random_page"


def test_translate_todo_with_doing_marker():
    todo_with_doing = {
        "id": "4",
        "uuid": "jkl-3456",
        "page": {"name": "projects/test_project"},
        "content": "DOING Task that is in progress",
    }

    translated = translate_todo(todo_with_doing)
    assert translated[0] == "Task that is in progress"
    assert translated[8] == "start:now"


def test_remove_unwanted_various_formats():
    cleaned_content = remove_unwanted("Detail :LOGBOOK: along with things :END:")
    assert cleaned_content == "Detail"

    cleaned_content = remove_unwanted("Just some text")
    assert cleaned_content == "Just some text"

    cleaned_content = remove_unwanted(":LOGBOOK: stray content")
    assert cleaned_content == ":LOGBOOK: stray content"


def test_fetch_existing_tasks_empty_output():
    with patch("_logseq.subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        tasks = fetch_existing_tasks()
        assert len(tasks) == 0


def test_main_function_add_task():
    with patch("_logseq.fetch_existing_tasks") as mock_fetch:
        mock_fetch.return_value = []
        with patch("_logseq.grab_todos_from_logseq") as mock_grab:
            mock_grab.return_value = [GENERIC_TODO]

            with patch("_logseq.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                main()
                mock_run.assert_called_once()


def test_main_function_with_translation_error():
    with patch("_logseq.fetch_existing_tasks") as mock_fetch:
        mock_fetch.return_value = []
        with patch("_logseq.grab_todos_from_logseq") as mock_grab:
            mock_grab.return_value = [GENERIC_TODO]

            with patch("_logseq.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                main()
                mock_run.assert_called_once()


def test_update_logseq_todo_success():
    with patch("_logseq.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        result = update_logseq_todo("uuid-1234", "Updated task content")
        assert result is True


def test_update_logseq_todo_failure():
    with patch("_logseq.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Error"
        )
        mock_post.return_value = mock_response

        result = update_logseq_todo("uuid-5678", "Updated task content")
        assert result is False


def test_extract_project_from_content_invalid_format():
    content, project = extract_project_from_content(
        "Some content with [[projects/invalid_project_format"
    )
    assert content.strip() == "Some content with [[projects/invalid_project_format"
    assert project is None


def test_fetch_existing_tasks_error_handling():
    with patch("_logseq.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "task")
        tasks = fetch_existing_tasks()
        assert len(tasks) == 0


def test_update_youtrack_issue_success():
    with patch("_youtrack.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        success = update_youtrack_issue("123", "456", "To Do")
        assert success is True


def test_update_youtrack_issue_failure():
    with patch("_youtrack.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Error"
        )
        mock_post.return_value = mock_response
        success = update_youtrack_issue("123", "456", "To Do")
        assert success is False


def test_get_youtrack_issues_success():
    with patch("_youtrack.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [{"idReadable": "YT-1", "summary": "Issue 1"}]
        mock_get.return_value = mock_response
        issues = get_youtrack_issues("query")
        assert issues == [{"idReadable": "YT-1", "summary": "Issue 1"}]


def test_sync_task_with_youtrack_no_issues():
    with patch("util_task_youtrack_sync.get_youtrack_issues") as mock_get:
        mock_get.return_value = None
        with patch("util_task_youtrack_sync.logging") as mock_logging:
            sync_task_with_youtrack()
            mock_logging.warning.assert_called_once_with(
                "no card assigned, you are basically fired!"
            )
