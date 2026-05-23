#!/usr/bin/env python3
import pytest
import json
from unittest.mock import patch, MagicMock
from mcp_server_github import (
    GitHubUser, IssueComment, Issue, PRComment, PullRequest,
    _github_get,
)


class TestModels:
    def test_github_user_minimal(self):
        user = GitHubUser(
            login="brokenpip3", id=1,
            avatar_url="https://avatars.githubusercontent.com/u/40476330?v=4",
            html_url="https://github.com/brokenpip3",
        )
        assert user.login == "brokenpip3"
        assert user.id == 1

    def test_issue_minimal(self):
        user = GitHubUser(login="brokenpip3", id=40476330, avatar_url="", html_url="")
        issue = Issue(
            id=10, number=42, title="Bug", state="open",
            body="something broke", user=user,
            labels=["bug"], created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            html_url="https://github.com/brokenpip3/my-binaries/issues/42",
        )
        assert issue.number == 42
        assert issue.title == "Bug"
        assert issue.labels == ["bug"]
        assert issue.comments == []

    def test_pull_request_minimal(self):
        user = GitHubUser(login="brokenpip3", id=40476330, avatar_url="", html_url="")
        pr = PullRequest(
            id=20, number=7, title="Fix", state="open",
            body="fixes it", user=user,
            merged=False, draft=False,
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-02T00:00:00Z",
            html_url="https://github.com/brokenpip3/my-binaries/pull/7",
        )
        assert pr.number == 7
        assert pr.diff is None
        assert pr.comments == []

    def test_issue_with_comments(self):
        user = GitHubUser(login="brokenpip3", id=40476330, avatar_url="", html_url="")
        comment = IssueComment(
            id=1, body="nice catch", user=user,
            created_at="2026-01-01T01:00:00Z",
            html_url="https://github.com/brokenpip3/my-binaries/issues/42#issuecomment-1",
        )
        issue = Issue(
            id=10, number=42, title="Bug", state="open",
            body="something broke", user=user,
            labels=[], created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            html_url="https://github.com/brokenpip3/my-binaries/issues/42",
            comments=[comment],
        )
        assert len(issue.comments) == 1
        assert issue.comments[0].body == "nice catch"

    def test_pr_with_comments(self):
        user = GitHubUser(login="brokenpip3", id=40476330, avatar_url="", html_url="")
        comment = PRComment(
            id=1, body="use a constant", user=user,
            path="main.py", line=10,
            created_at="2026-01-01T01:00:00Z",
            html_url="https://github.com/brokenpip3/my-binaries/pull/7#discussion-1",
        )
        pr = PullRequest(
            id=20, number=7, title="Fix", state="open",
            body="fixes it", user=user,
            merged=False, draft=False,
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-02T00:00:00Z",
            html_url="https://github.com/brokenpip3/my-binaries/pull/7",
            diff="--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-old\n+new",
            comments=[comment],
        )
        assert pr.diff is not None
        assert pr.diff.startswith("---")
        assert pr.comments[0].path == "main.py"


class TestGithubGet:
    @patch("httpx.Client")
    def test_successful_json(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "58",
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Reset": "1712345678",
        }
        mock_response.json.return_value = {"id": 1, "name": "test"}
        mock_response.text = ""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        data, rate_limit = _github_get("/repos/brokenpip3/my-binaries/issues/1")

        assert data["id"] == 1
        assert rate_limit["remaining"] == 58
        assert rate_limit["limit"] == 60
        mock_client_instance.get.assert_called_once_with(
            "https://api.github.com/repos/brokenpip3/my-binaries/issues/1",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "mcp-server-github",
            },
        )

    @patch("httpx.Client")
    def test_successful_diff(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "57",
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Reset": "1712345678",
        }
        mock_response.text = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new"
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        diff_text, rate_limit = _github_get(
            "/repos/brokenpip3/my-binaries/pulls/1", accept="application/vnd.github.v3.diff"
        )

        assert diff_text.startswith("---")
        assert rate_limit["remaining"] == 57

    @patch("httpx.Client")
    def test_404_error(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {
            "X-RateLimit-Remaining": "59",
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Reset": "1712345678",
        }
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        with pytest.raises(Exception, match="Not found"):
            _github_get("/repos/brokenpip3/my-binaries/issues/999")

    @patch("httpx.Client")
    def test_rate_limit_exhausted(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Reset": "9999999999",
        }
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        with pytest.raises(Exception, match="Rate limit exhausted"):
            _github_get("/repos/brokenpip3/my-binaries/issues/1")


class TestIssueResource:
    @pytest.mark.anyio
    @patch("mcp_server_github._github_get")
    async def test_get_issue_resource(self, mock_get):
        mock_get.side_effect = [
            (
                {
                    "id": 1, "number": 42, "title": "Test Issue", "state": "open",
                    "body": "desc",
                    "user": {"login": "brokenpip3", "id": 40476330, "avatar_url": "", "html_url": ""},
                    "labels": [{"name": "bug"}],
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                    "html_url": "https://github.com/brokenpip3/my-binaries/issues/42",
                    "comments": 1,
                },
                {"remaining": 58, "limit": 60, "reset_at": "2026-01-01T01:00:00Z"},
            ),
            (
                [{
                    "id": 1, "body": "a comment",
                    "user": {"login": "brokenpip3", "id": 40476330, "avatar_url": "", "html_url": ""},
                    "created_at": "2026-01-01T00:30:00Z",
                    "html_url": "https://github.com/brokenpip3/my-binaries/issues/42#issuecomment-1",
                }],
                {"remaining": 57, "limit": 60, "reset_at": "2026-01-01T01:00:00Z"},
            ),
        ]

        from mcp_server_github import get_issue
        result_str = await get_issue("brokenpip3", "my-binaries", 42)
        result = json.loads(result_str)
        assert result["number"] == 42
        assert result["title"] == "Test Issue"
        assert len(result["comments"]) == 1
        assert result["comments"][0]["body"] == "a comment"
        assert "_rate_limit" in result
        assert result["_rate_limit"]["remaining"] == 57


class TestPullRequestResource:
    @pytest.mark.anyio
    @patch("mcp_server_github._github_get")
    async def test_get_pull_request_resource(self, mock_get):
        mock_get.side_effect = [
            (
                {
                    "id": 10, "number": 7, "title": "Fix the thing", "state": "open",
                    "body": "fixes it",
                    "user": {"login": "brokenpip3", "id": 40476330, "avatar_url": "", "html_url": ""},
                    "merged": False, "draft": False,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                    "html_url": "https://github.com/brokenpip3/my-binaries/pull/7",
                },
                {"remaining": 57, "limit": 60, "reset_at": "2026-01-01T01:00:00Z"},
            ),
            (
                "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new",
                {"remaining": 56, "limit": 60, "reset_at": "2026-01-01T01:00:00Z"},
            ),
            (
                [{
                    "id": 1, "body": "use a constant",
                    "user": {"login": "brokenpip3", "id": 40476330, "avatar_url": "", "html_url": ""},
                    "path": "main.py", "line": 10,
                    "created_at": "2026-01-01T00:30:00Z",
                    "html_url": "https://github.com/brokenpip3/my-binaries/pull/7#discussion-1",
                }],
                {"remaining": 55, "limit": 60, "reset_at": "2026-01-01T01:00:00Z"},
            ),
        ]

        from mcp_server_github import get_pull_request
        result_str = await get_pull_request("brokenpip3", "my-binaries", 7)
        result = json.loads(result_str)
        assert result["number"] == 7
        assert result["title"] == "Fix the thing"
        assert result["diff"] is not None
        assert "old" in result["diff"]
        assert len(result["comments"]) == 1
        assert result["comments"][0]["path"] == "main.py"
        assert result["_rate_limit"]["remaining"] == 55


class TestErrorHandling:
    @pytest.mark.anyio
    @patch("mcp_server_github._github_get")
    async def test_issue_not_found(self, mock_get):
        mock_get.side_effect = Exception(
            "Not found: https://api.github.com/repos/brokenpip3/my-binaries/issues/999"
        )

        from mcp_server_github import get_issue
        result_str = await get_issue("brokenpip3", "my-binaries", 999)
        result = json.loads(result_str)
        assert "error" in result
        assert "Not found" in result["error"]

    @pytest.mark.anyio
    @patch("mcp_server_github._github_get")
    async def test_pr_rate_limit_exhausted(self, mock_get):
        mock_get.side_effect = Exception(
            "Rate limit exhausted, resets at 2026-01-01T02:00:00Z"
        )

        from mcp_server_github import get_pull_request
        result_str = await get_pull_request("brokenpip3", "my-binaries", 1)
        result = json.loads(result_str)
        assert "error" in result
        assert "Rate limit exhausted" in result["error"]

    @pytest.mark.anyio
    @patch("mcp_server_github._github_get")
    async def test_network_error(self, mock_get):
        mock_get.side_effect = Exception("Network error: Connection refused")

        from mcp_server_github import get_issue
        result_str = await get_issue("brokenpip3", "my-binaries", 1)
        result = json.loads(result_str)
        assert "error" in result
        assert "Network error" in result["error"]
