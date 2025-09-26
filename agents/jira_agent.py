from typing import Any, Dict, List, Optional
import logging
from services.jira_mcp_client import jira_mcp_client

logger = logging.getLogger(__name__)


class JiraAgent:
    async def list_tools(self) -> List[Dict[str, Any]]:
        return await jira_mcp_client.list_tools()

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        return await jira_mcp_client.call_tool(name, arguments)

    async def search_issues(self, jql: str, limit: int = 50) -> Any:
        return await jira_mcp_client.search_issues(jql, max_results=limit)

    async def get_issue(self, key: str) -> Any:
        return await jira_mcp_client.get_issue(key)

    async def create_issue(self, project_key: str, summary: str, description: str, issue_type: str = "Task") -> Any:
        return await jira_mcp_client.create_issue(project_key, summary, description, issue_type)


jira_agent = JiraAgent()


