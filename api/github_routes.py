from fastapi import APIRouter, HTTPException, Query, Path  # type: ignore[import-not-found]
from typing import Optional
from agents.mcp_agent import mcp_agent
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["GitHub"])

@router.get("/repositories")
async def list_repositories(
    owner: Optional[str] = Query(None, description="GitHub username or org"),
    limit: int = Query(30, description="Number of repositories", ge=1, le=100),
):
    try:
        repos = await mcp_agent.list_repositories(owner=owner, limit=limit)
        return {"repositories": repos, "count": len(repos)}
    except Exception as e:
        logger.error("Error listing repositories: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/repositories/{owner}/{repo}/commits")
async def list_commits(
    owner: str = Path(..., description="Repository owner"),
    repo: str = Path(..., description="Repository name"),
    limit: int = Query(30, description="Number of commits", ge=1, le=100),
    sha: Optional[str] = Query(None, description="Branch or starting SHA"),
    path: Optional[str] = Query(None, description="Filter by file path"),
):
    try:
        commits = await mcp_agent.list_commits(owner, repo, limit=limit, sha=sha, path=path)
        return {"commits": commits, "count": len(commits)}
    except Exception as e:
        logger.error("Error listing commits for %s/%s: %s", owner, repo, str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/issues/search")
async def search_issues(
    query: str = Query(..., description="GitHub issues search query"),
    owner: Optional[str] = Query(None, description="Repository owner to scope results"),
    repo: Optional[str] = Query(None, description="Repository name to scope results (with owner)"),
    order: Optional[str] = Query(None, description="Sort order (asc/desc)"),
    sort: Optional[str] = Query(None, description="Sort field"),
    page: Optional[int] = Query(None, description="Page number", ge=1),
    per_page: Optional[int] = Query(None, description="Results per page", ge=1, le=100),
):
    try:
        issues = await mcp_agent.search_issues(
            query=query,
            owner=owner,
            repo=repo,
            order=order,
            sort=sort,
            page=page,
            per_page=per_page,
        )
        return {"issues": issues, "count": len(issues)}
    except Exception as e:
        logger.error("Error searching issues: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
