#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
import logging
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import uvicorn
import httpx
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings

logging.basicConfig(level=logging.INFO)

BEARER_TOKEN = os.getenv("UTIL_AI_MCP_GH_LOCAL_TOKEN", "change-me")
GITHUB_API_BASE = "https://api.github.com"


class GitHubTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if token == BEARER_TOKEN:
            return AccessToken(
                token=token,
                client_id="github_client",
                scopes=["github:read"],
            )
        return None


mcp = FastMCP(
    "github mcp server",
    instructions="read-only github mcp server for issues and pull requests",
    token_verifier=GitHubTokenVerifier(),
    auth=AuthSettings(
        issuer_url="https://github-mcp.local/auth", resource_server_url=None
    ),
)

class GitHubUser(BaseModel):
    login: str
    id: int
    avatar_url: str
    html_url: str


class IssueComment(BaseModel):
    id: int
    body: Optional[str] = None
    user: GitHubUser
    created_at: str
    html_url: str


class Issue(BaseModel):
    id: int
    number: int
    title: str
    state: str
    body: Optional[str] = None
    user: GitHubUser
    labels: List[str] = []
    created_at: str
    updated_at: str
    html_url: str
    comments_count: int = 0
    comments: List[IssueComment] = []


class PRComment(BaseModel):
    id: int
    body: Optional[str] = None
    user: GitHubUser
    path: Optional[str] = None
    line: Optional[int] = None
    created_at: str
    html_url: str


class PullRequest(BaseModel):
    id: int
    number: int
    title: str
    state: str
    body: Optional[str] = None
    user: GitHubUser
    merged: bool = False
    draft: bool = False
    created_at: str
    updated_at: str
    html_url: str
    diff: Optional[str] = None
    comments: List[PRComment] = []

def _github_get(endpoint: str, accept: str = "application/vnd.github.v3+json") -> Tuple[Any, Dict[str, Any]]:
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = {
        "Accept": accept,
        "User-Agent": "mcp-server-github",
    }
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url, headers=headers)

        remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
        limit = int(response.headers.get("X-RateLimit-Limit", 60))
        reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
        reset_at = datetime.fromtimestamp(reset_ts, tz=timezone.utc).isoformat() if reset_ts else ""
        rate_limit = {"remaining": remaining, "limit": limit, "reset_at": reset_at}

        if response.status_code == 404:
            raise Exception(f"Not found: {url}")
        elif response.status_code == 403:
            if remaining == 0:
                raise Exception(f"Rate limit exhausted, resets at {reset_at}")
            raise Exception(f"Forbidden: {url}")

        response.raise_for_status()

        if accept == "application/vnd.github.v3.diff":
            return response.text, rate_limit
        return response.json(), rate_limit

@mcp.resource("github://{owner}/{repo}/issues/{number}")
async def get_issue(owner: str, repo: str, number: int) -> str:
    try:
        return _fetch_issue_response(owner, repo, number)
    except Exception as e:
        logging.error(f"error fetching issue: {e}")
        return json.dumps({"error": str(e)}, indent=2)


def _fetch_issue_response(owner: str, repo: str, number: int) -> str:
    issue_data, rl1 = _github_get(f"/repos/{owner}/{repo}/issues/{number}")
    issue_data["labels"] = [l["name"] for l in issue_data.get("labels", [])]

    comments_data, rl2 = _github_get(f"/repos/{owner}/{repo}/issues/{number}/comments")

    issue = Issue(
        id=issue_data["id"],
        number=issue_data["number"],
        title=issue_data["title"],
        state=issue_data["state"],
        body=issue_data.get("body"),
        user=GitHubUser(**issue_data["user"]),
        labels=issue_data["labels"],
        created_at=issue_data["created_at"],
        updated_at=issue_data["updated_at"],
        html_url=issue_data["html_url"],
        comments_count=issue_data.get("comments", 0),
        comments=[IssueComment(
            id=c["id"],
            body=c.get("body"),
            user=GitHubUser(**c["user"]),
            created_at=c["created_at"],
            html_url=c["html_url"],
        ) for c in comments_data],
    )

    result = json.loads(issue.model_dump_json())
    result["_rate_limit"] = rl2
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_issue_tool(owner: str, repo: str, number: int) -> str:
    """Fetch a GitHub issue with its comments. Uses unauthenticated API (60 req/hr)."""
    return _fetch_issue_response(owner, repo, number)


@mcp.resource("github://{owner}/{repo}/pulls/{number}")
async def get_pull_request(owner: str, repo: str, number: int) -> str:
    try:
        return _fetch_pr_response(owner, repo, number)
    except Exception as e:
        logging.error(f"error fetching pull request: {e}")
        return json.dumps({"error": str(e)}, indent=2)


def _fetch_pr_response(owner: str, repo: str, number: int) -> str:
    pr_data, rl1 = _github_get(f"/repos/{owner}/{repo}/pulls/{number}")
    diff_text, rl2 = _github_get(
        f"/repos/{owner}/{repo}/pulls/{number}",
        accept="application/vnd.github.v3.diff",
    )
    comments_data, rl3 = _github_get(f"/repos/{owner}/{repo}/pulls/{number}/comments")

    pr = PullRequest(
        id=pr_data["id"],
        number=pr_data["number"],
        title=pr_data["title"],
        state=pr_data["state"],
        body=pr_data.get("body"),
        user=GitHubUser(**pr_data["user"]),
        merged=pr_data.get("merged", False),
        draft=pr_data.get("draft", False),
        created_at=pr_data["created_at"],
        updated_at=pr_data["updated_at"],
        html_url=pr_data["html_url"],
        diff=diff_text if diff_text.strip() else None,
        comments=[PRComment(
            id=c["id"],
            body=c.get("body"),
            user=GitHubUser(**c["user"]),
            path=c.get("path"),
            line=c.get("line"),
            created_at=c["created_at"],
            html_url=c["html_url"],
        ) for c in comments_data],
    )

    result = json.loads(pr.model_dump_json())
    result["_rate_limit"] = rl3
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_pull_request_tool(owner: str, repo: str, number: int) -> str:
    """Fetch a GitHub pull request with its diff and review comments. Uses unauthenticated API (60 req/hr)."""
    return _fetch_pr_response(owner, repo, number)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="read-only github mcp server")
        parser.add_argument("--port", type=int, default=8127, help="server port")
        args = parser.parse_args()
        uvicorn.run(
            mcp.streamable_http_app, host="0.0.0.0", port=args.port, factory=True
        )
    except Exception as e:
        logging.error(f"server startup failed: {e}")
        raise
