import os
from dotenv import load_dotenv
from services.llm_factory import LLMProvider, LLMFactory

# Load environment variables
load_dotenv()

class Settings:
    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    # Google AI Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Application Configuration
    APP_NAME: str = os.getenv("APP_NAME", "Dobb.ai Backend")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # GitHub MCP Server Configuration (used by mcp-use)
    GITHUB_MCP_TOOLSETS: str = os.getenv("GITHUB_MCP_TOOLSETS", "repos,issues,pull_requests,actions,code_security")
    GITHUB_MCP_READ_ONLY: bool = os.getenv("GITHUB_MCP_READ_ONLY", "False").lower() == "true"
    # Optional default repo scope for GitHub searches. Comma-separated list of owner/name.
    GITHUB_DEFAULT_REPOS: str = os.getenv("GITHUB_DEFAULT_REPOS", "")
    # Optional single repository URL (e.g., https://github.com/owner/repo)
    GITHUB_REPO_URL: str = os.getenv("GITHUB_REPO_URL", "")

    # Jira MCP Server Configuration (used by mcp-use)
    # Jira connection details
    JIRA_URL: str = os.getenv("JIRA_URL", "")
    # Prefer JIRA_USERNAME but support legacy JIRA_USER_NAME
    JIRA_USERNAME: str = os.getenv("JIRA_USERNAME", os.getenv("JIRA_USER_NAME", ""))
    JIRA_USER_NAME: str = os.getenv("JIRA_USER_NAME", "")
    JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
    # Optional SSL verification toggle for some deployments
    JIRA_VERIFY_SSL: bool = os.getenv("JIRA_VERIFY_SSL", "True").lower() == "true"
    JIRA_DEFAULT_PROJECT_KEY: str = os.getenv("JIRA_DEFAULT_PROJECT_KEY", "")
    # Optional: Docker image or command to run Jira MCP server. If not set, client may fallback to npx server.
    JIRA_MCP_SERVER_URL: str = os.getenv("JIRA_MCP_SERVER_URL", "")
settings = Settings()


class LLMConfig:
    LLM_PROVIDER = LLMFactory.create(
        provider=LLMProvider.GROQ,
        model_name="llama-3.3-70b-versatile" 
    )