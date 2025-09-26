# Dobb.ai Backend

A FastAPI backend for AI-powered applications with intelligent chatbot, document processing, report generation, and GitHub/Jira integration.

## 📋 Prerequisites

### System Requirements
- **Python 3.12+**
- **Node.js 18+** (for GitHub MCP server)
- **Git**
- **Docker** (for Jira MCP server)

### Required API Keys
- **Google AI API Key** (for Gemini chatbot)
- **OpenAI API Key** (for embeddings)
- **GitHub Personal Access Token** (with repo read access)
- **Jira API Token** (for Jira integration)

## 🚀 Installation

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd dobb.ai-backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp env.example .env
# Edit .env with your API keys
```

**Required Environment Variables:**
```bash
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_pat
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your_email
JIRA_API_TOKEN=your_jira_api_token
```

### 4. Start Services
```bash
# Start API server
python main.py
# Server runs at http://localhost:8000

# Start web interface (new terminal)
streamlit run streamlit_app.py
# Interface at http://localhost:8501
```

## 🏗️ Overview

### Core Features
- **AI Chatbot**: Google Gemini-powered assistant with project context
- **Document Processing**: Text/PDF embedding with ChromaDB vector storage
- **Report Generation**: AI-powered technical impact analysis
- **GitHub Integration**: Repository management via MCP
- **Jira Integration**: Issue management via MCP

### Project Structure
```
dobb.ai-backend/
├── api/                    # API route handlers
│   ├── chatbot_routes.py   # Chatbot endpoints
│   ├── embedding_routes.py # Document processing
│   ├── github_routes.py    # GitHub MCP integration
│   └── jira_routes.py      # Jira MCP integration
├── chatbot/                # AI chatbot implementation
├── services/               # Business logic services
├── agents/                 # MCP agent implementations
├── main.py                 # FastAPI application
└── streamlit_app.py        # Web interface
```

### Technology Stack
- **Backend**: FastAPI, Python 3.12+
- **AI**: Google Gemini, OpenAI GPT, LangChain
- **Database**: ChromaDB (vector storage)
- **Frontend**: Streamlit
- **Integrations**: GitHub MCP, Jira MCP

## 📡 API Documentation

### Interactive Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Chatbot**
```bash
POST /chatbot/
# Send message with conversation history
```

**Document Processing**
```bash
POST /embedding/text    # Process text files
POST /embedding/pdf     # Process PDF files
```

**GitHub Integration**
```bash
GET /api/github/repositories?owner={owner}&limit={limit}
GET /api/github/repositories/{owner}/{repo}/commits
```

**Jira Integration**
```bash
GET /api/jira/issues/search?jql={jql}&limit={n}
POST /api/jira/issues
```

## 🔧 Development

### Development Mode
```bash
# API server with auto-reload
uvicorn main:app --reload --port 8000

# Streamlit with auto-reload
streamlit run streamlit_app.py --server.runOnSave true
```

### Docker Deployment
```bash
# Build and run
docker build -t dobb-ai-backend .
docker run -p 8000:8000 --env-file .env dobb-ai-backend
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ using FastAPI, Google Gemini, LangChain, and modern AI technologies.**
