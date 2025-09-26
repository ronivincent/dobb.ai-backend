from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from services.jira_mcp_client import jira_mcp_client
from services.mcp_client import mcp_client as github_mcp_client
from config import settings


logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry to discover available MCP tools at runtime and cache results."""

    def __init__(self) -> None:
        self._cached: Optional[Dict[str, List[Dict[str, Any]]]] = None

    async def list_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        if self._cached is not None:
            return self._cached

        tools: Dict[str, List[Dict[str, Any]]] = {}

        try:
            jira_tools_raw = await jira_mcp_client.list_tools()
            tools["jira"] = _normalize_tools_list(jira_tools_raw)
        except (TypeError, ValueError, AttributeError) as exc:
            logger.warning("Unable to list Jira tools: %s", exc)
            tools["jira"] = []

        try:
            client = await github_mcp_client._ensure_client()  # pylint: disable=protected-access
            session = client.get_session("github")
            gh_tools_raw = await session.list_tools()
            tools["github"] = _normalize_tools_list(gh_tools_raw)
            logger.info("GitHub tools: %s", tools["github"])
        except (TypeError, ValueError, AttributeError) as exc:
            logger.warning("Unable to list GitHub tools: %s", exc)
            tools["github"] = []

        self._cached = tools
        return tools


registry = ToolRegistry()


def _normalize_tool_item(tool: Any) -> Dict[str, Any]:
    """Coerce an MCP Tool object (or dict) into a plain dict with key fields."""
    if isinstance(tool, dict):
        return tool
    # Try pydantic-style APIs
    for attr in ("model_dump", "dict"):
        fn = getattr(tool, attr, None)
        if callable(fn):
            try:
                dumped = fn()
                if isinstance(dumped, dict):
                    return dumped
            except (TypeError, ValueError, AttributeError):
                pass
    # Fallback to attribute introspection
    name = getattr(tool, "name", None)
    description = getattr(tool, "description", None)
    input_schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
    if hasattr(input_schema, "model_dump"):
        try:
            input_schema = input_schema.model_dump()
        except (TypeError, ValueError, AttributeError):
            input_schema = None
    elif hasattr(input_schema, "dict"):
        try:
            input_schema = input_schema.dict()
        except (TypeError, ValueError, AttributeError):
            input_schema = None
    data: Dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if input_schema is not None:
        data["input_schema"] = input_schema
    return data or {"name": str(tool)}


def _normalize_tools_list(tools: Any) -> List[Dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    return [_normalize_tool_item(t) for t in tools]


def _extract_keywords(user_message: str, limit: int = 5) -> List[str]:
    """Extract simple keywords from the user message for queries/JQL."""
    text = user_message.lower()
    words = re.findall(r"[a-z0-9_\-]+", text)
    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "on",
        "in",
        "for",
        "of",
        "with",
        "about",
        "all",
        "give",
        "show",
        "list",
        "get",
        "me",
        "my",
        "please",
        "could",
        "would",
        "find",
        "fetch",
        "retrieve",
        "past",
        "history",
        "issue",
        "issues",
        "pr",
        "pull",
        "request",
        "requests",
        "related",
        "know",
        "want",
    }
    keywords: List[str] = []
    for w in words:
        if w not in stop and len(w) > 2 and w not in keywords:
            keywords.append(w)
        if len(keywords) >= limit:
            break
    return keywords or ["permission"]


def _parse_repo_filters(user_message: str) -> List[str]:
    """Extract repo filters of the form repo:owner/name from the user message."""
    matches = re.findall(r"repo:([\w.-]+/[\w.-]+)", user_message, flags=re.IGNORECASE)
    # From env default repos
    defaults = [r.strip() for r in settings.GITHUB_DEFAULT_REPOS.split(",") if r.strip()]
    # From a single repo URL
    if settings.GITHUB_REPO_URL:
        m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", settings.GITHUB_REPO_URL, flags=re.IGNORECASE)
        if m:
            defaults.append(f"{m.group(1)}/{m.group(2)}")
    # De-duplicate while preserving order
    seen = set()
    repos: List[str] = []
    for r in matches + defaults:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            repos.append(r)
    return repos


def _needs_tools(user_message: str) -> bool:
    text = user_message.lower()
    triggers = [
        "jira",
        "github",
        "issue",
        "issues",
        "task",
        "tasks",
        "ticket",
        "pull request",
        "pr",
        "permission",
        "history",
        "story",
        "stories",
        "epic",
        "epics",
        "feature",
        "features",
        "bug",
        "bugs",
        "problem",
        "problems",
        "error",
        "errors",
        "help",
        "need",
        "needs",
        "want",
        "wants"
        "commit",
        "commits",
        "repository",
        "repositories",
        "repo",
        "repos",
        "list repos",
        "list commits",
        "list commit",
        "list commit history",
        "commit history",
        "commit history",
    ]
    return any(t in text for t in triggers)


def _wants_direct_create(user_message: str) -> bool:
    """Detect if the user explicitly asks to create a Jira ticket/issue/bug."""
    text = user_message.lower()
    patterns = [
        "create a bug",
        "create bug",
        "create jira bug",
        "create jira ticket",
        "create ticket in jira",
        "create a ticket",
        "create ticket",
        "open a bug",
        "open bug in jira",
        "open a ticket",
        "file a bug",
        "report a bug",
        "create issue",
        "create an issue",
        "raise a bug",
    ]
    return any(p in text for p in patterns)


def _parse_title_description(user_message: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse title and description from patterns like 'title - X, description - Y'."""
    title: Optional[str] = None
    description: Optional[str] = None
    m_title = re.search(r"title\s*[-:]\s*(.+?)(?:,|$)", user_message, flags=re.IGNORECASE)
    if m_title:
        title = m_title.group(1).strip()
    m_desc = re.search(r"description\s*[-:]\s*(.+)$", user_message, flags=re.IGNORECASE)
    if m_desc:
        description = m_desc.group(1).strip()
    return title, description


def _resolve_tool_name(tools: List[Dict[str, Any]], preferred_names: List[str], required_tokens: Optional[List[str]] = None) -> Optional[str]:
    """Pick a tool name from a tool list by preferred names or tokens in name/description."""
    names = [str(t.get("name", "")) for t in tools]
    lower_map = {n.lower(): n for n in names if n}
    # 1) exact preferred name match (case-insensitive)
    for pref in preferred_names:
        if pref.lower() in lower_map:
            return lower_map[pref.lower()]
    # 2) token-based heuristic
    if required_tokens:
        best: Optional[str] = None
        for t in tools:
            name = str(t.get("name", ""))
            desc = str(t.get("description", ""))
            blob = f"{name} {desc}".lower()
            if all(tok in blob for tok in required_tokens):
                best = name
                break
        if best:
            return best
    # 3) fallback: first tool that contains all tokens in name only
    if required_tokens:
        for t in tools:
            name = str(t.get("name", "")).lower()
            if all(tok in name for tok in required_tokens):
                return str(t.get("name"))
    return None


def _find_tool_by_name(tools: List[Dict[str, Any]], name: Optional[str]) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    for t in tools:
        if str(t.get("name", "")).lower() == name.lower():
            return t
    return None


def _extract_schema_keys(tool_meta: Optional[Dict[str, Any]]) -> List[str]:
    if not tool_meta:
        return []
    # Common schema key variants in MCP
    schema = (
        tool_meta.get("input_schema")
        or tool_meta.get("inputSchema")
        or tool_meta.get("schema")
        or {}
    )
    props = schema.get("properties") if isinstance(schema, dict) else None
    if isinstance(props, dict):
        return list(props.keys())
    return []


def _adapt_arguments(provider: str, tool_meta: Optional[Dict[str, Any]], intended_args: Dict[str, Any]) -> Dict[str, Any]:
    schema_keys = _extract_schema_keys(tool_meta)
    keys_lower = {k.lower(): k for k in schema_keys}

    def choose_key(candidates: List[str], default_key: str) -> str:
        for c in candidates:
            k = keys_lower.get(c.lower())
            if k:
                return k
        return default_key

    args: Dict[str, Any] = {}
    if provider == "jira":
        jql_key = choose_key(["jql", "query", "jqlQuery"], "jql")
        max_key = choose_key(["maxResults", "max_results", "limit"], "maxResults")
        if "jql" in intended_args:
            args[jql_key] = intended_args["jql"]
        if "maxResults" in intended_args:
            args[max_key] = intended_args["maxResults"]
        if "limit" in intended_args and max_key not in args:
            args[max_key] = intended_args["limit"]
        # Also pass through remaining intended args (e.g., project_key, summary, description, issue_type)
        for k, v in intended_args.items():
            if k not in args:
                # Map common variants to schema keys when available
                candidate = keys_lower.get(k.lower()) or k
                # Handle camelCase <-> snake_case for common fields
                if candidate == k and schema_keys:
                    if k == "project_key" and "projectKey" in schema_keys:
                        candidate = "projectKey"
                    elif k == "projectKey" and "project_key" in schema_keys:
                        candidate = "project_key"
                    elif k == "issue_type" and "issueType" in schema_keys:
                        candidate = "issueType"
                    elif k == "issueType" and "issue_type" in schema_keys:
                        candidate = "issue_type"
                args[candidate] = v
    elif provider == "github":
        query_key = choose_key(["query", "q"], "query")
        per_page_key = choose_key(["perPage", "per_page", "limit"], "perPage")
        owner_key = choose_key(["owner", "user", "org"], "owner")
        repo_key = choose_key(["repo", "repository"], "repo")
        sha_key = choose_key(["sha", "start_sha"], "sha")
        ref_key = choose_key(["ref", "sha", "commit"], "ref")
        path_key = choose_key(["path", "filePath"], "path")
        order_key = choose_key(["order", "direction"], "order")
        sort_key = choose_key(["sort"], "sort")
        page_key = choose_key(["page"], "page")

        if "query" in intended_args:
            args[query_key] = intended_args["query"]
        if "perPage" in intended_args:
            args[per_page_key] = intended_args["perPage"]
        if "limit" in intended_args and per_page_key not in args:
            args[per_page_key] = intended_args["limit"]
        if "owner" in intended_args:
            args[owner_key] = intended_args["owner"]
        if "repo" in intended_args:
            args[repo_key] = intended_args["repo"]
        if "sha" in intended_args:
            args[sha_key] = intended_args["sha"]
        if "ref" in intended_args:
            args[ref_key] = intended_args["ref"]
        if "path" in intended_args:
            args[path_key] = intended_args["path"]
        if "order" in intended_args:
            args[order_key] = intended_args["order"]
        if "sort" in intended_args:
            args[sort_key] = intended_args["sort"]
        if "page" in intended_args:
            args[page_key] = intended_args["page"]

        # Enforce repository scoping using GITHUB_REPO_URL if set
        enforced_url = settings.GITHUB_REPO_URL.strip()
        if enforced_url:
            m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", enforced_url)
            if m:
                enforced_owner, enforced_repo = m.group(1), m.group(2)
                # Ensure query includes repo qualifier
                if query_key in args and isinstance(args[query_key], str):
                    token = f"repo:{enforced_owner}/{enforced_repo}"
                    if token not in args[query_key]:
                        args[query_key] = f"{token} {args[query_key]}".strip()
                # Set owner/repo arguments; schema filter will drop them if not accepted
                args[owner_key] = enforced_owner
                args[repo_key] = enforced_repo
    else:
        args = dict(intended_args)

    # If we know the schema keys, drop extras not present to avoid validation errors
    if schema_keys:
        args = {k: v for k, v in args.items() if k in schema_keys}

    return args


async def _plan(user_message: str, available_tools: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Produce a simple plan consisting of tool calls with arguments."""
    tasks: List[Dict[str, Any]] = []

    keywords = _extract_keywords(user_message)
    logger.debug("Planner keywords: %s", keywords)

    text_lower = user_message.lower()
    logger.info("Planner user_message: %s", user_message)
    logger.info("Planner text_lower: %s", text_lower)
    # Provider filter based on user intent
    def _allowed_providers(text: str) -> set[str]:
        allowed: set[str] = {"jira", "github"}
        if ("only jira" in text) or ("consider only jira" in text) or ("jira only" in text):
            return {"jira"}
        if ("only github" in text) or ("consider only github" in text) or ("github only" in text):
            return {"github"}
        if ("no jira" in text) or ("without jira" in text) or ("ignore jira" in text):
            allowed.discard("jira")
        if ("no github" in text) or ("without github" in text) or ("ignore github" in text):
            allowed.discard("github")
        return allowed

    providers = _allowed_providers(text_lower)
    logger.info("Provider filter: %s", sorted(list(providers)))

    # Resolve tool names based on what's exposed by MCP servers
    jira_tools = available_tools.get("jira", [])
    gh_tools = available_tools.get("github", [])

    # If the user explicitly asks to create a Jira bug/ticket, plan only the create step
    if "jira" in providers and _wants_direct_create(user_message):
        jira_create_tool = _resolve_tool_name(
            jira_tools,
            preferred_names=["jira_create_issue", "create_issue", "createIssue"],
            required_tokens=["create", "issue"],
        )
        chosen_create_tool = jira_create_tool or "jira_create_issue"
        create_meta = _find_tool_by_name(jira_tools, chosen_create_tool)
        title, desc = _parse_title_description(user_message)
        summary = title or user_message[:100]
        description = desc or user_message
        project_key = settings.JIRA_DEFAULT_PROJECT_KEY or ""
        logger.info("Direct-create Jira issue planned: project=%s tool=%s", project_key, chosen_create_tool)
        return [{
            "provider": "jira",
            "tool": chosen_create_tool,
            "meta": create_meta,
            "args": {"project_key": project_key, "summary": summary, "description": description, "issue_type": "Bug"},
        }]

    jira_search_tool = _resolve_tool_name(
        jira_tools,
        preferred_names=[
            "search_issues",
            "searchIssues",
            "issues_search",
            "jira_search_issues",
        ],
        required_tokens=["search", "issue"],
    )
    if not jira_search_tool:
        logger.warning("No Jira search issues tool found; available=%s", [t.get("name") for t in jira_tools])

    gh_search_tool = _resolve_tool_name(
        gh_tools,
        preferred_names=[
            "search_issues",  # GitHub search API returns issues & PRs
            "searchIssues",
        ],
        required_tokens=["search", "issue"],
    )
    if not gh_search_tool:
        # try a PR specific tool name variant
        gh_search_tool = _resolve_tool_name(
            gh_tools,
            preferred_names=["search_pull_requests", "searchPullRequests"],
            required_tokens=["search", "pull"],
        )
    if not gh_search_tool:
        logger.warning("No GitHub search tool found; available=%s", [t.get("name") for t in gh_tools])

    # Additional GitHub tools resolution
    gh_repo_search_tool = _resolve_tool_name(
        gh_tools,
        preferred_names=["search_repositories", "searchRepositories"],
        required_tokens=["search", "repo"],
    )
    gh_list_commits_tool = _resolve_tool_name(
        gh_tools,
        preferred_names=["list_commits", "listCommits"],
        required_tokens=["commit"],
    )
    gh_get_commit_tool = _resolve_tool_name(
        gh_tools,
        preferred_names=["get_commit", "getCommit"],
        required_tokens=["commit"],
    )

    # JIRA plan: build filter then add ORDER BY once
    jql_filter: Optional[str]
    if "all tasks" in text_lower or ("tasks" in text_lower and len(keywords) <= 2):
        jql_filter = 'issuetype in ("Task","Story","Bug","Epic")'
    else:
        jql_terms = [f'(summary ~ "{kw}" OR description ~ "{kw}")' for kw in keywords]
        jql_filter = " OR ".join(jql_terms) if jql_terms else None
    jira_meta = _find_tool_by_name(jira_tools, jira_search_tool)
    if ("jira" in providers) and jql_filter and jira_search_tool:
        jql = f"({jql_filter}) ORDER BY updated DESC"
        logger.debug("Planner JQL (final): %s", jql)
        tasks.append({
            "provider": "jira",
            "tool": jira_search_tool,
            "meta": jira_meta,
            "args": {"jql": jql, "maxResults": 30},
        })

    # GitHub plan - search pull requests/issues mentioning the keywords
    gh_meta = _find_tool_by_name(gh_tools, gh_search_tool)
    issue_pr_intent = any(
        k in text_lower for k in (
            "issue",
            "issues",
            "pr",
            "pull request",
            "pull requests",
        )
    )
    # Detect if user referenced a specific commit by SHA and intent
    sha_match = re.search(r"\b[0-9a-f]{7,40}\b", text_lower)
    specific_commit_intent = bool(sha_match) and any(
        phrase in text_lower for phrase in (
            "this commit",
            "that commit",
            "the commit",
            "show commit",
            "get commit",
            "view commit",
            "open commit",
            "commit details",
            "details for commit",
            "details of commit",
            "what changed in commit",
            "changes in commit",
        )
    )
    if ("github" in providers) and gh_search_tool and issue_pr_intent:
        repo_filters = _parse_repo_filters(user_message)
        repo_part = " ".join([f"repo:{r}" for r in repo_filters]) + (" " if repo_filters else "")
        gh_query = f"{repo_part}is:pr is:merged sort:updated-desc " + " ".join(keywords)
        logger.debug("Planner GitHub query: %s", gh_query)
        tasks.append({
            "provider": "github",
            "tool": gh_search_tool,
            "meta": gh_meta,
            "args": {"query": gh_query, "perPage": 30},
        })

    # GitHub plan - search repositories
    gh_repo_meta = _find_tool_by_name(gh_tools, gh_repo_search_tool)
    if ("github" in providers) and gh_repo_search_tool and ("repositories" in text_lower or "repos" in text_lower or "list repos" in text_lower):
        repo_query = " ".join(keywords) or "stars:>1"
        logger.debug("Planner GitHub repo query: %s", repo_query)
        tasks.append({
            "provider": "github",
            "tool": gh_repo_search_tool,
            "meta": gh_repo_meta,
            "args": {"query": repo_query, "perPage": 30},
        })

    # GitHub plan - list commits for a repository
    gh_list_commits_meta = _find_tool_by_name(gh_tools, gh_list_commits_tool)
    logger.info("Planner gh_list_commits_meta: %s", gh_list_commits_tool)
    if ("github" in providers) and gh_list_commits_tool and ("commits" in text_lower or "commit history" in text_lower or "history" in text_lower) and not specific_commit_intent:
        repos = _parse_repo_filters(user_message)
        logger.info("Planner repos: %s", repos)
        if repos:
            try:
                owner, repo_name = repos[0].split("/", 1)
                tasks.append({
                    "provider": "github",
                    "tool": gh_list_commits_tool,
                    "meta": gh_list_commits_meta,
                    "args": {"owner": owner, "repo": repo_name, "perPage": 30},
                })
            except ValueError:
                logger.warning("Unable to parse owner/repo from repo filter: %s", repos[0])

    # GitHub plan - get a specific commit by SHA/ref (only when explicitly asked)
    gh_get_commit_meta = _find_tool_by_name(gh_tools, gh_get_commit_tool)
    if ("github" in providers) and gh_get_commit_tool and specific_commit_intent:
        repos = _parse_repo_filters(user_message)
        if sha_match and repos:
            try:
                owner, repo_name = repos[0].split("/", 1)
                ref = sha_match.group(0)
                tasks.append({
                    "provider": "github",
                    "tool": gh_get_commit_tool,
                    "meta": gh_get_commit_meta,
                    "args": {"owner": owner, "repo": repo_name, "ref": ref},
                })
            except ValueError:
                logger.warning("Unable to parse owner/repo for get_commit from: %s", repos[0])
    logger.info("Planner tasks: %s", tasks)
    return tasks


async def _execute(tasks: List[Dict[str, Any]]) -> List[Any]:
    calls: List[asyncio.Future] = []

    for t in tasks:
        provider = t.get("provider")
        tool_name = t.get("tool")
        logger.info("Orchestrator tool name: %s", tool_name)
        args = t.get("args", {})

        if provider == "jira":
            adapted = _adapt_arguments(provider, t.get("meta"), args)
            logger.info("Calling Jira tool %s with args %s", tool_name, adapted)
            calls.append(jira_mcp_client.call_tool(tool_name, arguments=adapted))
        elif provider == "github":
            meta = t.get("meta")
            async def _call_github(name: str, arguments: Dict[str, Any], _meta: Optional[Dict[str, Any]]):
                client = await github_mcp_client._ensure_client()  # pylint: disable=protected-access
                session = client.get_session("github")
                adapted = _adapt_arguments("github", _meta, arguments)
                logger.info("Calling GitHub tool %s with args %s", name, adapted)
                raw = await session.call_tool(name=name, arguments=adapted)
                return _unwrap_mcp_result(raw)

            calls.append(_call_github(tool_name, args, meta))
        else:
            logger.warning("Unknown provider in task: %s", provider)

    results = await asyncio.gather(*calls, return_exceptions=True)
    return results


def _aggregate(tasks: List[Dict[str, Any]], results: List[Any]) -> Tuple[str, List[Dict[str, str]]]:
    """Summarize results and prepare sources."""
    lines: List[str] = []
    sources: List[Dict[str, str]] = []
    structured: Dict[str, Any] = {}

    def _jira_issues_from_payload(payload: Any) -> List[Dict[str, Any]]:
        def normalize_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
            # Some create endpoints return { message, issue: { ... } }
            if isinstance(raw.get("issue"), dict):
                raw = raw["issue"]  # type: ignore[assignment]

            issue_id = raw.get("id") or raw.get("issue_id")
            issue_key = raw.get("key")
            # fields may be top-level or under 'fields'
            fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
            summary = raw.get("summary") or fields.get("summary") or ""
            description = raw.get("description") or fields.get("description") or ""
            # Prefer browse URL if we have a key and base URL; otherwise fall back to API links
            browse_url = f"{settings.JIRA_URL.rstrip('/')}/browse/{issue_key}" if settings.JIRA_URL and issue_key else ""
            url = browse_url or raw.get("self") or raw.get("url") or ""
            return {
                "id": issue_id,
                "key": issue_key,
                "summary": summary,
                "description": description,
                "url": url,
            }

        issues_list: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            # pattern: [ { total, issues: [...] } ]
            for entry in payload:
                if isinstance(entry, dict) and isinstance(entry.get("issues"), list):
                    for it in entry["issues"]:
                        if isinstance(it, dict):
                            issues_list.append(normalize_issue(it))
        elif isinstance(payload, dict):
            # Handle wrapped search results under 'items' → [{ issues: [...] }]
            if isinstance(payload.get("items"), list):
                for entry in payload["items"]:
                    if isinstance(entry, dict) and isinstance(entry.get("issues"), list):
                        for it in entry["issues"]:
                            if isinstance(it, dict):
                                issues_list.append(normalize_issue(it))
            if isinstance(payload.get("issues"), list):
                for it in payload["issues"]:
                    if isinstance(it, dict):
                        issues_list.append(normalize_issue(it))
            elif isinstance(payload.get("issue"), dict):
                issues_list.append(normalize_issue(payload["issue"]))
            else:
                # maybe already a single issue
                issues_list.append(normalize_issue(payload))
        return issues_list

    # --- GitHub normalizers ---
    def _github_search_items(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            items = payload.get("items")
            if isinstance(items, list):
                return [i for i in items if isinstance(i, dict)]
        if isinstance(payload, list):
            # Sometimes raw list of items is returned
            return [i for i in payload if isinstance(i, dict)]
        return []

    def _github_issues_from_payload(payload: Any) -> List[Dict[str, Any]]:
        items = _github_search_items(payload)
        results_: List[Dict[str, Any]] = []
        for it in items:
            url = it.get("html_url") or it.get("url") or ""
            results_.append({
                "id": it.get("id"),
                "number": it.get("number"),
                "title": it.get("title"),
                "state": it.get("state"),
                "url": url,
            })
        return results_

    def _github_repos_from_payload(payload: Any) -> List[Dict[str, Any]]:
        items = _github_search_items(payload)
        results_: List[Dict[str, Any]] = []
        for it in items:
            url = it.get("html_url") or it.get("url") or ""
            results_.append({
                "id": it.get("id"),
                "name": it.get("name"),
                "full_name": it.get("full_name"),
                "description": it.get("description"),
                "url": url,
                "stargazers_count": it.get("stargazers_count"),
            })
        return results_

    def _github_commits_from_payload(payload: Any) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            items = [i for i in payload if isinstance(i, dict)]
        elif isinstance(payload, dict):
            # Some tools wrap in a dict key; try common variants
            for key in ("commits", "items", "results"):
                if isinstance(payload.get(key), list):
                    items = [i for i in payload.get(key) if isinstance(i, dict)]
                    break

        results_: List[Dict[str, Any]] = []
        for it in items:
            commit = it.get("commit") if isinstance(it.get("commit"), dict) else {}
            author = commit.get("author") if isinstance(commit.get("author"), dict) else {}
            url = it.get("html_url") or it.get("url") or ""
            results_.append({
                "sha": it.get("sha"),
                "message": commit.get("message"),
                "author": author.get("name"),
                "date": author.get("date"),
                "url": url,
            })
        return results_

    for t, r in zip(tasks, results):
        label = f"{t.get('provider')}.{t.get('tool')}"
        if isinstance(r, Exception):
            lines.append(f"{label}: error {r}")
            continue

        # Count
        count = 0
        if isinstance(r, list):
            count = len(r)
        elif isinstance(r, dict):
            count = 1
        lines.append(f"{label}: {count} results")

        # Provider-specific normalization for structured output
        if t.get("provider") == "jira":
            jira_issues = _jira_issues_from_payload(r)
            if jira_issues:
                structured.setdefault("jira_issues", []).extend(jira_issues)
                logger.info("structured: %s", structured)
        elif t.get("provider") == "github":
            tool = str(t.get("tool") or "").lower()
            if "search_issues" in tool:
                gh_issues = _github_issues_from_payload(r)
                if gh_issues:
                    structured.setdefault("github_issues", []).extend(gh_issues)
            elif "search_repositories" in tool or "searchrepositories" in tool:
                gh_repos = _github_repos_from_payload(r)
                if gh_repos:
                    structured.setdefault("github_repositories", []).extend(gh_repos)
            elif "list_commits" in tool or "listcommits" in tool:
                gh_commits = _github_commits_from_payload(r)
                if gh_commits:
                    structured.setdefault("github_commits", []).extend(gh_commits)
            elif "get_commit" in tool or "getcommit" in tool:
                # Single commit object
                commits_one = _github_commits_from_payload([r] if isinstance(r, dict) else [])
                if commits_one:
                    structured.setdefault("github_commits", []).extend(commits_one)

        # Collect top sources mapped to ChatResponse.SourceInfo
        items_for_sources: List[Dict[str, Any]] = []
        # Prefer raw payload shape if it clearly contains issues
        if isinstance(r, list) and r and isinstance(r[0], dict) and isinstance(r[0].get("issues"), list):
            items_for_sources = r[0]["issues"]
        elif isinstance(r, dict) and isinstance(r.get("issues"), list):
            items_for_sources = r["issues"]
        else:
            # Fallback to structured aggregates built above
            if t.get("provider") == "jira":
                items_for_sources = structured.get("jira_issues", [])  # type: ignore[assignment]
            elif t.get("provider") == "github":
                items_for_sources = (
                    structured.get("github_issues", [])  # type: ignore[assignment]
                    or structured.get("github_repositories", [])  # type: ignore[assignment]
                    or structured.get("github_commits", [])  # type: ignore[assignment]
                )

        for idx, item in enumerate(items_for_sources[:5], start=1):
            # Prefer meaningful titles depending on item type
            title = item.get("title") or item.get("key") or item.get("name") or item.get("message") or "item"
            url = (
                item.get("html_url")
                or item.get("url")
                or item.get("self")
                or ""
            )
            preview = (
                (item.get("body") if isinstance(item.get("body"), str) else "")
                or (item.get("fields", {}).get("summary") if isinstance(item.get("fields"), dict) else "")
                or (item.get("commit", {}).get("message") if isinstance(item.get("commit"), dict) else "")
                or ""
            )
            sources.append({
                "chunk_id": idx,
                "source": str(url or title),
                "content_preview": str(preview)[:200],
            })

    # Prefer structured JSON if we built it; otherwise textual summary
    if structured:
        try:
            return json.dumps(structured, ensure_ascii=False), sources
        except (TypeError, ValueError):
            pass

    answer = "\n".join(lines) if lines else "No results found."
    return answer, sources


async def orchestrate(user_message: str) -> Dict[str, Any]:
    """Plan, execute, and aggregate tool calls for a user message.

    Returns a dict with keys: output (str|None) and sources (list) when applicable.
    If tools are not needed, returns {"output": None} to signal RAG fallback.
    """
    needs = _needs_tools(user_message)
    logger.info("Orchestrator needs_tools=%s", needs)
    if not needs:
        return {"output": None}

    tools = await registry.list_tools()  # prime discovery/cache

    tasks = await _plan(user_message, tools)
    logger.info("Orchestrator planned %d task(s)", len(tasks))
    if not tasks:
        return {"output": None}

    results = await _execute(tasks)
    logger.info("Orchestrator results: %s", results)
    output, sources = _aggregate(tasks, results)
    return {"output": output, "sources": sources}


def _unwrap_mcp_result(call_result: Any) -> Any:
    """Convert mcp_use CallToolResult into plain Python data.

    Prefer JSON content if present; otherwise parse text content as JSON if possible.
    Fallback to the raw content/text when parsing fails.
    """
    if isinstance(call_result, (list, dict)):
        return call_result
    content_list = getattr(call_result, "content", None)
    if isinstance(content_list, list) and content_list:
        first_item = content_list[0]
        text_value = getattr(first_item, "text", None)
        logger.info("Text value: %s", text_value)
        if isinstance(text_value, str):
            try:
                return json.loads(text_value)
            except (ValueError, TypeError):
                return text_value
        json_attr = getattr(first_item, "json", None)
        try:
            if callable(json_attr):
                return json_attr()
            if json_attr is not None:
                return json_attr
        except (TypeError, AttributeError):
            pass
    return call_result


