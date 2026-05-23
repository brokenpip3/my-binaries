# Github read-only mcp server

Readonly access to gh issues and pull requests via the unauthenticated api (60 requests/hour).

## Resources

- `github://{owner}/{repo}/issues/{number}` — issue with comments
- `github://{owner}/{repo}/pulls/{number}` — pr with diff and review comments

## Tools

- `get_issue_tool` — issue with comments
- `get_pull_request_tool` — pr with diff and review comments

## Usage

```bash
UTIL_AI_MCP_GH_LOCAL_TOKEN # bearer token for the MCP HTTP endpoint
```

### Config

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "http://localhost:8127/mcp",
      "headers": {
        "Authorization": "Bearer xxxxx"
      }
    }
  },
}
```
