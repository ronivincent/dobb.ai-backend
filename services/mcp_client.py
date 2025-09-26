from typing import Dict, List, Any, Optional
import logging
from mcp_use import MCPClient  # type: ignore
from config import settings

logger = logging.getLogger(__name__)


class GithubMCPClient:
    def __init__(self):
        self.client: Optional[MCPClient] = None

    @staticmethod
    def _parse_enforced_repo() -> Optional[tuple[str, str]]:
        url = settings.GITHUB_REPO_URL.strip()
        if not url:
            return None
        import re as _re
        m = _re.search(r"github\.com/([\w.-]+)/([\w.-]+)", url)
        if not m:
            return None
        return m.group(1), m.group(2)

    @classmethod
    def _ensure_repo_in_query(cls, query: str) -> str:
        enforced = cls._parse_enforced_repo()
        if not enforced:
            return query
        owner, repo = enforced
        # If query already has a repo: qualifier for this repo, leave it
        token = f"repo:{owner}/{repo}"
        if token in query:
            return query
        return f"{token} {query}".strip()

    @classmethod
    def _enforced_owner_repo(cls, owner: Optional[str], repo: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        enforced = cls._parse_enforced_repo()
        if enforced:
            return enforced[0], enforced[1]
        return owner, repo

    async def _ensure_client(self) -> MCPClient:
        if self.client is None:
            if not settings.GITHUB_TOKEN:
                raise RuntimeError("GITHUB_TOKEN is not set")

            config = {
                "mcpServers": {
                    "github": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"],
                        "env": {
                            "GITHUB_PERSONAL_ACCESS_TOKEN": settings.GITHUB_TOKEN,
                            "GITHUB_TOOLSETS": settings.GITHUB_MCP_TOOLSETS,
                            "GITHUB_READ_ONLY": str(settings.GITHUB_MCP_READ_ONLY).lower(),
                        },
                    }
                }
            }

            self.client = MCPClient.from_dict(config)
            await self.client.create_all_sessions()
        return self.client

    async def close(self) -> None:
        if self.client:
            await self.client.close_all_sessions()
            self.client = None

    @staticmethod
    def _unwrap_result(call_result: Any) -> Any:
        """Convert mcp_use CallToolResult into plain Python data.

        Prefer JSON content if present; otherwise parse text content as JSON if possible.
        Fallback to the raw content/text when parsing fails.
        """
        # Already a plain type
        if isinstance(call_result, (list, dict)):
            return call_result

        # mcp_use CallToolResult typically has a .content list
        content_list = getattr(call_result, "content", None)
        if isinstance(content_list, list) and content_list:
            first_item = content_list[0]
            # Try text attribute that may contain JSON
            text_value = getattr(first_item, "text", None)
            if isinstance(text_value, str):
                try:
                    import json as _json
                    return _json.loads(text_value)
                except (ValueError, TypeError):
                    return text_value

            # Try json attribute/method
            json_attr = getattr(first_item, "json", None)
            try:
                if callable(json_attr):
                    return json_attr()
                if json_attr is not None:
                    return json_attr
            except (TypeError, ValueError, AttributeError):
                pass

        return call_result

    async def list_repositories(self, owner: str = None, per_page: int = 30) -> List[Dict[str, Any]]:
        client = await self._ensure_client()
        session = client.get_session("github")
        enforced = self._parse_enforced_repo()
        if enforced:
            query = f"repo:{enforced[0]}/{enforced[1]}"
        else:
            query = f"user:{owner}" if owner else "stars:>1000"
        raw = await session.call_tool(name="search_repositories", arguments={"query": query, "perPage": per_page})
        data = self._unwrap_result(raw)
        # Normalize to list of repos
        if isinstance(data, dict):
            items = data.get("items") or data.get("repositories") or []
            return items if isinstance(items, list) else []
        return data if isinstance(data, list) else []

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        client = await self._ensure_client()
        session = client.get_session("github")
        owner, repo = self._enforced_owner_repo(owner, repo)
        raw = await session.call_tool(name="search_repositories", arguments={"query": f"repo:{owner}/{repo}", "perPage": 1})
        data = self._unwrap_result(raw)
        if isinstance(data, list):
            return data[0] if data else {}
        if isinstance(data, dict):
            items = data.get("items") or data.get("repositories") or []
            return items[0] if isinstance(items, list) and items else {}
        return {}

    async def list_commits(self, owner: str, repo: str, sha: str = None, path: str = None, per_page: int = 30) -> List[Dict[str, Any]]:
        client = await self._ensure_client()
        session = client.get_session("github")
        owner, repo = self._enforced_owner_repo(owner, repo)
        args: Dict[str, Any] = {"owner": owner, "repo": repo, "perPage": per_page}
        if sha:
            args["sha"] = sha
        if path:
            args["path"] = path
        raw = await session.call_tool(name="list_commits", arguments=args)
        data = self._unwrap_result(raw)
        return data if isinstance(data, list) else []

    async def get_commit(self, owner: str, repo: str, ref: str) -> Dict[str, Any]:
        client = await self._ensure_client()
        session = client.get_session("github")
        owner, repo = self._enforced_owner_repo(owner, repo)
        raw = await session.call_tool(name="get_commit", arguments={"owner": owner, "repo": repo, "ref": ref})
        data = self._unwrap_result(raw)
        return data if isinstance(data, dict) else {}

    async def search_issues(
        self,
        query: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        order: Optional[str] = None,
        sort: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search GitHub issues via MCP 'search_issues' tool.

        Parameters mirror the GitHub MCP Server tool:
        - query: Required search string using GitHub issues search syntax
        - owner: Optional repository owner (limits results with repo)
        - repo: Optional repository name (use with owner)
        - order: Optional sort order (e.g., 'asc' or 'desc')
        - sort: Optional sort field
        - page: Optional page number (min 1)
        - per_page: Optional page size (min 1, max 100)
        """
        client = await self._ensure_client()
        session = client.get_session("github")

        # Enforce repo scoping always
        query = self._ensure_repo_in_query(query)
        owner, repo = self._enforced_owner_repo(owner, repo)

        args: Dict[str, Any] = {"query": query}
        if owner:
            args["owner"] = owner
        if repo:
            args["repo"] = repo
        if order:
            args["order"] = order
        if sort:
            args["sort"] = sort
        if page is not None:
            args["page"] = page
        if per_page is not None:
            args["perPage"] = per_page  # MCP expects camelCase

        raw = await session.call_tool(name="search_issues", arguments=args)
        data = self._unwrap_result(raw)

        # Normalize to list of issues
        if isinstance(data, dict):
            items = data.get("items") or data.get("issues") or []
            return items if isinstance(items, list) else []
        return data if isinstance(data, list) else []


# Global client instance
mcp_client = GithubMCPClient()
