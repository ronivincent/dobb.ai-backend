import json
import logging
from typing import Any, Dict, Tuple

from config import LLMConfig


logger = logging.getLogger(__name__)


GITHUB_REFINE_PROMPT = (
    "You are a precise formatter for GitHub tool results.\n"
    "Given the user's request and structured GitHub data, output exactly what the user needs without summarizing away lists.\n"
    "Rules:\n"
    "- Never invent facts.\n"
    "- If commits are present, list them as bullets with: sha(7), message(one line), author, date(ISO), url.\n"
    "- If repositories are present, list them: full_name, description(<=120 chars), stars, url.\n"
    "- If issues/PRs are present, list them: #number, title, state, url.\n"
    "- Prefer lists over paragraphs when the user asks to list commits/repos/issues/PRs.\n"
    "- Limit to at most 20 items; if more, end with '... and more'.\n"
    "- Keep formatting compact and skimmable.\n\n"
    "User request:\n{user}\n\n"
    "Structured GitHub data (JSON):\n{data}\n\n"
    "Output:"
)


JIRA_REFINE_PROMPT = (
    "You are a precise formatter for Jira tool results.\n"
    "Given the user's request and structured Jira data, output the key facts clearly.\n"
    "Rules:\n"
    "- Never invent facts.\n"
    "- If Jira issues are present, list them as bullets: KEY, summary, url.\n"
    "- Prefer lists over paragraphs when the user asks to list issues/tasks/stories.\n"
    "- Limit to at most 20 items; if more, end with '... and more'.\n"
    "- Keep formatting compact and skimmable.\n\n"
    "User request:\n{user}\n\n"
    "Structured Jira data (JSON):\n{data}\n\n"
    "Output:"
)


def _detect_provider_and_payload(output_str: str) -> Tuple[str, Dict[str, Any]]:
    try:
        parsed = json.loads(output_str)
        if isinstance(parsed, dict):
            for k in parsed.keys():
                lk = str(k).lower()
                if lk.startswith("github_"):
                    return "github", parsed
                if lk.startswith("jira_"):
                    return "jira", parsed
        return "unknown", {}
    except json.JSONDecodeError:  # json parsing fallback
        return "unknown", {}


def refine_tool_result(tool_result: Dict[str, Any], user_message: str) -> str:
    try:
        raw = tool_result.get("output")
        if not isinstance(raw, str):
            raw = str(raw)

        provider, data = _detect_provider_and_payload(raw)

        # Deterministic Jira formatting: enumerate all issues
        if provider == "jira" and isinstance(data, dict) and isinstance(data.get("jira_issues"), list):
            issues = data["jira_issues"]
            lines = []
            for it in issues:
                if not isinstance(it, dict):
                    continue
                key = str(it.get("key") or "").strip()
                summary = str(it.get("summary") or "").strip()
                url = str(it.get("url") or "").strip()
                if key or summary or url:
                    lines.append(f"- [{key}] {summary} — {url}")
            return "\n".join(lines) if lines else raw

        # Deterministic GitHub formatting still goes through the prompt for field selection/limits
        if provider == "github" and data:
            prompt = GITHUB_REFINE_PROMPT.format(user=user_message, data=json.dumps(data, ensure_ascii=False))
        elif provider == "jira" and data:
            prompt = JIRA_REFINE_PROMPT.format(user=user_message, data=json.dumps(data, ensure_ascii=False))
        else:
            # Fallback to a simple neutral summary preserving key fields
            fallback_prompt = (
                "You are a helpful assistant that refines raw tool outputs into concise, factual context.\n"
                "Given the user's request and the tool outputs below, produce a short, neutral, skimmable result.\n"
                "- Do not invent facts.\n"
                "- Prefer bullet points listing key fields.\n\n"
                f"User request:\n{user_message}\n\n"
                f"Tool outputs (raw):\n{raw}\n\n"
                "Output:"
            )
            prompt = fallback_prompt

        response = LLMConfig.LLM_PROVIDER.invoke(prompt)
        content = getattr(response, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        return raw
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Refine agent failed: %s", exc)
        return str(tool_result.get("output", ""))


