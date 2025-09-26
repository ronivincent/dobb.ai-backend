from fastapi import APIRouter, HTTPException, Query, Path, Body  # type: ignore[import-not-found]
from typing import Optional, Dict, Any
from agents.jira_agent import jira_agent
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jira", tags=["Jira"])


@router.get("/tools")
async def list_tools():
    try:
        tools = await jira_agent.list_tools()
        return {"tools": tools, "count": len(tools) if isinstance(tools, list) else 0}
    except Exception as e:
        logger.error("Error listing Jira tools: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tools/{tool_name}")
async def call_tool(tool_name: str = Path(..., description="Tool name to call"), payload: Dict[str, Any] = Body(None)):
    try:
        arguments = payload.get("arguments") if isinstance(payload, dict) else None
        result = await jira_agent.call_tool(tool_name, arguments=arguments or payload or {})
        return {"result": result}
    except Exception as e:
        logger.error("Error calling Jira tool %s: %s", tool_name, str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/issues/search")
async def search_issues(
    jql: str = Query(..., description="JQL query string"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
):
    try:
        issues = await jira_agent.search_issues(jql, limit=limit)
        # Normalize basic response shape
        if isinstance(issues, dict) and "issues" in issues:
            items = issues["issues"]
            return {"issues": items, "count": len(items) if isinstance(items, list) else 0}
        if isinstance(issues, list):
            return {"issues": issues, "count": len(issues)}
        return {"issues": issues}
    except Exception as e:
        logger.error("Error searching Jira issues: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/issues/{key}")
async def get_issue(key: str = Path(..., description="Issue key (e.g., PROJ-123)")):
    try:
        issue = await jira_agent.get_issue(key)
        return {"issue": issue}
    except Exception as e:
        logger.error("Error getting Jira issue %s: %s", key, str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/issues")
async def create_issue(payload: Dict[str, Any] = Body(...)):
    try:
        project_key = payload.get("projectKey") or payload.get("project_key")
        summary = payload.get("summary")
        description = payload.get("description") or ""
        issue_type = payload.get("issueType") or payload.get("issue_type") or "Task"

        if not project_key or not summary:
            raise HTTPException(status_code=400, detail="projectKey and summary are required")

        created = await jira_agent.create_issue(project_key, summary, description, issue_type)
        return {"issue": created}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating Jira issue: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


