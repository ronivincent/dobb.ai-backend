from typing import Any, Dict, List, Optional
import logging
import shutil
from mcp_use import MCPClient  # type: ignore
from config import settings

logger = logging.getLogger(__name__)


class JiraMCPClient:
    def __init__(self) -> None:
        self.client: Optional[MCPClient] = None

    async def _ensure_client(self) -> MCPClient:
        if self.client is None:
            if not settings.JIRA_URL:
                raise RuntimeError("JIRA_URL is not set")
            if not (settings.JIRA_USERNAME or settings.JIRA_USER_NAME):
                raise RuntimeError("JIRA_USERNAME/JIRA_USER_NAME is not set")
            if not settings.JIRA_API_TOKEN:
                raise RuntimeError("JIRA_API_TOKEN is not set")

            # Prefer Docker image if provided and docker is available; otherwise use npx server
            jira_env = {
                "JIRA_URL": settings.JIRA_URL,
                "JIRA_USERNAME": settings.JIRA_USERNAME or settings.JIRA_USER_NAME,
                "JIRA_API_TOKEN": settings.JIRA_API_TOKEN,
                "JIRA_VERIFY_SSL": str(settings.JIRA_VERIFY_SSL).lower(),
            }

            use_docker = bool(settings.JIRA_MCP_SERVER_URL) and shutil.which("docker") is not None

            if use_docker:
                config: Dict[str, Any] = {
                    "mcpServers": {
                        "jira": {
                            "command": "docker",
                            "args": [
                                "run",
                                "-i",
                                "--rm",
                                "-e",
                                "JIRA_URL",
                                "-e",
                                "JIRA_USERNAME",
                                "-e",
                                "JIRA_API_TOKEN",
                                "-e",
                                "JIRA_VERIFY_SSL",
                                settings.JIRA_MCP_SERVER_URL,
                            ],
                            "env": jira_env,
                        }
                    }
                }
            else:
                # Fallback to official Atlassian MCP server via npx (stdio transport)
                config = {
                    "mcpServers": {
                        "jira": {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-atlassian"],
                            "env": jira_env,
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
        # Similar logic to GitHub client's unwrap
        if isinstance(call_result, (list, dict)):
            return call_result
        content_list = getattr(call_result, "content", None)
        if isinstance(content_list, list) and content_list:
            first_item = content_list[0]
            text_value = getattr(first_item, "text", None)
            if isinstance(text_value, str):
                try:
                    import json as _json
                    return _json.loads(text_value)
                except Exception:
                    return text_value
            json_attr = getattr(first_item, "json", None)
            try:
                if callable(json_attr):
                    return json_attr()
                if json_attr is not None:
                    return json_attr
            except Exception:
                pass
        return call_result

    async def list_tools(self) -> List[Dict[str, Any]]:
        client = await self._ensure_client()
        session = client.get_session("jira")
        tools = await session.list_tools()
        return self._unwrap_result(tools)  # type: ignore[return-value]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        client = await self._ensure_client()
        session = client.get_session("jira")
        raw = await session.call_tool(name=name, arguments=arguments or {})
        return self._unwrap_result(raw)

    # Convenience wrappers — actual tool names may vary; discover via list_tools
    async def search_issues(self, jql: str, max_results: int = 50) -> Any:
        """Try modern jira_search first; fallback to legacy search_issues."""
        try:
            return await self.call_tool("jira_search", {"jql": jql, "limit": max_results})
        except Exception as exc:  # pylint: disable=broad-except
            if any(s in str(exc).lower() for s in ("unknown tool", "not found", "no such tool")):
                return await self.call_tool("search_issues", {"jql": jql, "maxResults": max_results})
            raise

    async def get_issue(self, key: str) -> Any:
        """Try modern jira_get_issue; fallback to legacy get_issue."""
        try:
            return await self.call_tool("jira_get_issue", {"issue_key": key})
        except Exception as exc:  # pylint: disable=broad-except
            if any(s in str(exc).lower() for s in ("unknown tool", "not found", "no such tool")):
                return await self.call_tool("get_issue", {"key": key})
            raise

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
    ) -> Any:
        # Prefer modern Atlassian tool then fallback
        try:
            return await self.call_tool(
                "jira_create_issue",
                {
                    "project_key": project_key,
                    "summary": summary,
                    "description": description,
                    "issue_type": issue_type,
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            if not any(s in str(exc).lower() for s in ("unknown tool", "not found", "no such tool")):
                raise
            return await self.call_tool(
                "create_issue",
                {
                    "projectKey": project_key,
                    "summary": summary,
                    "description": description,
                    "issueType": issue_type,
                },
            )


# Global client instance
jira_mcp_client = JiraMCPClient()


