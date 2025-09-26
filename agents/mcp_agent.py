from typing import Dict, List, Any
import logging
from services.mcp_client import mcp_client

logger = logging.getLogger(__name__)


class MCPAgent:
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        return await mcp_client.get_repository(owner, repo)

    async def list_repositories(self, owner: str = None, limit: int = 30) -> List[Dict[str, Any]]:
        return await mcp_client.list_repositories(owner=owner, per_page=limit)

    async def list_commits(self, owner: str, repo: str, limit: int = 30, sha: str = None, path: str = None) -> List[Dict[str, Any]]:
        return await mcp_client.list_commits(owner, repo, sha=sha, path=path, per_page=limit)

    async def get_commit(self, owner: str, repo: str, commit_sha: str) -> Dict[str, Any]:
        return await mcp_client.get_commit(owner, repo, commit_sha)

    async def search_issues(
        self,
        query: str,
        owner: str | None = None,
        repo: str | None = None,
        order: str | None = None,
        sort: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> List[Dict[str, Any]]:
        return await mcp_client.search_issues(
            query=query,
            owner=owner,
            repo=repo,
            order=order,
            sort=sort,
            page=page,
            per_page=per_page,
        )


mcp_agent = MCPAgent()
