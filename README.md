# Dobb.ai Backend

A comprehensive FastAPI backend for AI-powered applications featuring intelligent chatbot, document processing, report generation, and GitHub integration capabilities.

## 🚀 Features

### 🤖 AI Codebase Assistant
- **Google Gemini Integration**: Powered by Google's Gemini AI model
- **README Context**: Uses project documentation as knowledge source
- **Focused Scope**: Specializes in answering questions about this codebase
- **Chain Pattern**: Efficient context injection similar to embedding service
- **Streamlit Web Interface**: Full-featured chat UI for project assistance

### 📄 Document Processing & Embeddings
- **Text & PDF Support**: Process `.txt` and `.pdf` files
- **ChromaDB Integration**: Vector database for semantic search
- **HuggingFace Embeddings**: Using `sentence-transformers/all-MiniLM-L6-v2`
- **RAG (Retrieval-Augmented Generation)**: Context-aware responses

### 📊 Report Generation
- **Technical Impact Analysis**: Automated report generation from PRD documents
- **AI-Powered Insights**: Leverages embedded knowledge for comprehensive analysis

### 🔧 GitHub Integration
- **Model Context Protocol (MCP)**: Modern GitHub integration via MCP
- **Repository Management**: List repositories and fetch commit history
- **Secure Access**: Token-based authentication

### 🧩 Jira Integration (MCP)
- **Model Context Protocol (MCP)**: Jira integration via MCP server
- **Run Modes**: Docker (default) or Local subprocess (like GitHub MCP)
- **Issue Operations**: Search, get, and create issues; invoke MCP tools
- **Secure Access**: Atlassian API token authentication

## 🛠️ Technology Stack

### Core Framework
- **FastAPI**: Modern, high-performance API framework
- **Python 3.12+**: Latest Python features and performance

### AI & Machine Learning
- **Google Gemini**: Primary language model for chat
- **OpenAI GPT**: Secondary LLM for embeddings
- **LangChain/LangGraph**: AI agent framework and workflow management
- **HuggingFace Transformers**: Embedding models and NLP tools

### Data & Storage
- **ChromaDB**: Vector database for embeddings
- **SQLAlchemy**: Database ORM (if needed)

### Web & UI
- **Streamlit**: Interactive web interface
- **CORS**: Cross-origin resource sharing enabled

### External Integrations
- **GitHub MCP**: Official GitHub Model Context Protocol server
- **DuckDuckGo API**: Web search functionality

## 📋 Prerequisites

Before setting up the project, ensure you have:

- **Python 3.12+**
- **Node.js 18+** (for GitHub MCP server via `npx`)
- **Git** (for version control)
- **Docker** (for Jira MCP server, unless using local mode)

### Required API Keys
- **GitHub Personal Access Token** (with repo read access)
- **Google AI API Key** (for Gemini)
- **OpenAI API Key** (for embeddings)
- **Jira URL + Username + API Token** (for Jira MCP)

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd dobb.ai-backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp env.example .env
# Edit .env and fill in required keys
```

Required keys (see `env.example`):
- `GOOGLE_API_KEY` (required for chatbot/Gemini)
- `OPENAI_API_KEY` (required for embeddings/report generation)
- `GITHUB_TOKEN` (required for GitHub MCP)
- `CHROMA_DB_DIRECTORY_PATH` (local path for Chroma persistence)
- Optional: `APP_NAME`, `DEBUG`, `GITHUB_MCP_TOOLSETS`, `GITHUB_MCP_READ_ONLY`
 - Jira MCP: `JIRA_URL`, `JIRA_USERNAME` (or `JIRA_USER_NAME`), `JIRA_API_TOKEN`, optional `JIRA_VERIFY_SSL`

```bash
# Required
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_pat

# Jira MCP
# Now uses HTTP SSE endpoint for Atlassian MCP server

JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your_email
JIRA_API_TOKEN=your_jira_api_token
# JIRA_VERIFY_SSL=true

# Optional
CHROMA_DB_DIRECTORY_PATH=./data/db
APP_NAME=Dobb.ai Backend
DEBUG=true
```

### 4. Start the API Server

```bash
# Using the main script
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
The server runs at `http://localhost:8000`.

### 5. Launch the Web Interface

```bash
# In a new terminal (with virtual environment activated)
streamlit run streamlit_app.py
```
The app expects the API to be available at `http://127.0.0.1:8000` and uses the `/chatbot/` endpoint.

## API Documentation

Once the server is running:
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The Streamlit interface will be available at `http://localhost:8501`

## 📡 API Endpoints

### Core Endpoints
- `GET /` — Welcome message and API status
- `GET /health` — Health check endpoint

### 🤖 Chatbot API
- `POST /chatbot/` — Send message to AI chatbot with conversation history

**Example Request:**
```bash
curl -X POST "http://localhost:8000/chatbot/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 15 * 8?",
    "history": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi! How can I help you?"}
    ]
  }'
```

### 📄 Embedding Endpoints
- `POST /embedding/text` — Process text files for embedding
- `POST /embedding/pdf` — Process PDF files for embedding

**Example:**
```bash
curl -X POST "http://localhost:8000/embedding/text" \
  -F "file=@document.txt"
```

### 📊 Report Generation
- `POST /report/generate` — Generate technical impact report from PRD

**Example:**
```bash
curl -X POST "http://localhost:8000/report/generate" \
  -H "Content-Type: application/json" \
  -d '{"prd_text": "Your PRD content here..."}'
```

### 🔧 GitHub Integration
- `GET /api/github/repositories?owner={owner}&limit={limit}` — List repositories
- `GET /api/github/repositories/{owner}/{repo}/commits?limit={n}&sha={ref}&path={path}` — Get commits

**Example:**
```bash
curl "http://localhost:8000/api/github/repositories?owner=octocat&limit=5"
curl "http://localhost:8000/api/github/repositories/octocat/Hello-World/commits?limit=10"
```

### 🧩 Jira Integration
- `GET /api/jira/tools` — List available MCP tools
- `POST /api/jira/tools/{tool_name}` — Invoke a Jira MCP tool with arguments
- `GET /api/jira/issues/search?jql={jql}&limit={n}` — Search issues
- `GET /api/jira/issues/{key}` — Get issue by key
- `POST /api/jira/issues` — Create an issue

```bash
curl "http://localhost:8000/api/jira/issues/search?jql=project=PROJ%20ORDER%20BY%20created%20DESC&limit=10"
```

## 🤖 Codebase Assistant Capabilities

The AI chatbot is specifically designed to help with your Dobb.ai Backend project:

### 📚 Project Knowledge
Get detailed information about the project's features and capabilities.
```
Examples:
- "What features does the Dobb.ai Backend provide?"
- "How does the chatbot system work?"
- "What AI capabilities are available?"
```

### ⚙️ Setup & Configuration
Get help with installation, configuration, and deployment.
```
Examples:
- "How do I set up the development environment?"
- "What environment variables do I need?"
- "How do I configure the API keys?"
```

### 📡 API Documentation
Learn about available endpoints and how to use them.
```
Examples:
- "What API endpoints are available?"
- "How do I use the embedding endpoints?"
- "Show me the chatbot API format"
```

## 📚 API Documentation

Once the server is running, access interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Project Structure

```
dobb.ai-backend/
├── api/                      # API route handlers
│   ├── chatbot_routes.py    # Chatbot endpoints
│   ├── embedding_routes.py  # Document processing endpoints
│   ├── github_routes.py     # GitHub MCP integration
│   ├── jira_routes.py       # Jira MCP integration
│   └── report_routes.py     # Report generation endpoints
├── chatbot/                  # AI chatbot implementation
│   ├── agent.py             # Simplified chatbot using chain pattern
│   ├── models.py            # Pydantic models
│   └── prompt.py            # LLM configuration with README context
├── services/                 # Business logic services
│   ├── embedding_service.py # ChromaDB and embeddings
│   ├── mcp_client.py        # GitHub MCP client
│   ├── jira_mcp_client.py   # Jira MCP client
│   └── report_service.py    # Report generation logic
├── agents/                   # MCP agent implementations
├── data/                     # Data storage
│   ├── db/                  # ChromaDB storage
│   └── templates/           # Prompt templates
├── config.py                # Configuration management
├── main.py                  # FastAPI application
├── streamlit_app.py         # Web interface
└── requirements.txt         # Dependencies
```

## 🔧 Development

### Running in Development Mode

```bash
# API server with auto-reload
uvicorn main:app --reload --port 8000

# Streamlit with auto-reload
streamlit run streamlit_app.py --server.runOnSave true
```

### Environment Configuration

The application supports multiple environment configurations:

- **Development**: Set `DEBUG=True` in `.env`
- **Production**: Set `DEBUG=False` and configure appropriate logging

### Customizing the Chatbot

The chatbot now uses a simple chain pattern similar to the embedding service:

1. **Context**: README content is loaded once when the server starts
2. **Chain Pattern**: User input → Context injection → LLM → Response
3. **Focused Scope**: Answers only questions about the Dobb.ai Backend project

## 🚀 Deployment

### Using Docker (Recommended)

```bash
# Build the image
docker build -t dobb-ai-backend .

# Run the container
docker run -p 8000:8000 --env-file .env dobb-ai-backend
```

### Manual Deployment

1. Set up Python 3.12+ environment
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables
4. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋 Support

For questions, issues, or feature requests:

1. Check the [API documentation](http://localhost:8000/docs) when running locally
2. Review the code examples in this README
3. Create an issue in the repository

## 🚧 Roadmap

- [ ] Additional LLM provider integrations
- [ ] Enhanced document processing formats
- [ ] Advanced analytics and reporting
- [ ] Database persistence for chat history
- [ ] User authentication and sessions
- [ ] Advanced GitHub workflow automation

---

**Built with ❤️ using FastAPI, Google Gemini, LangChain, and modern AI technologies.**
