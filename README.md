# Lenny Growth Assistant

A conversational Retrieval-Augmented Generation (RAG) assistant for product, growth, and leadership questions, grounded in **Lenny's Podcast** transcripts.

---

## Overview

Lenny Growth Assistant combines vector retrieval with multi-agent orchestration to deliver highly grounded answers, action-oriented frameworks, and specialized structured outputs (such as Ship 30 for 30 essays and clean Markdown/HTML artifacts).

### Key Features
- **Grounded Conversational RAG**: Answers queries using semantically relevant transcript chunks with clear source attribution and episode citations.
- **Multi-Agent System**:
  - **Q&A Agent**: Answers product/growth questions with grounded citations and confidence fallback behavior.
  - **Ship 30 Agent**: Transforms insights into structured, viral 300-word atomic essays.
  - **Artifact Agent**: Formats multi-turn code or rich content for rendering in the interactive UI.
  - **Orchestrator**: Routes user intent dynamically to the optimal specialized agent.
- **Provider Flexibility**: Supports local inference (Ollama with `llama3.2:3b`) and cloud LLMs (Anthropic Claude).
- **Interactive Web UI**: React-based chat application featuring session persistent threads, inline citations, and a sandboxed artifact preview pane.

---

## Prerequisites

Before getting started, ensure you have the following installed on your machine:

- **Git** (2.x+)
- **Python** (3.11 or higher)
- **Node.js** (v18 or higher) & **npm**
- **Docker** & **Docker Compose** (optional for containerized deployment)
- **Ollama** (optional, if running models locally)

---

## How to Clone and Work on the Project

### 1. Clone the Repository
```bash
git clone https://github.com/suryatejabatchu08/Lenny-Growth-Assistant.git
cd Lenny-Growth-Assistant
```

### 2. Environment Setup

Copy `.env.example` to create your local `.env` file:
```bash
cp .env.example .env
```

Configure your `.env` file with your database and provider details:
```env
# Supabase Database Credentials
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-supabase-anon-key>
DATABASE_URL=postgresql://postgres:[password]@[project-ref].pooler.supabase.com:5432/postgres

# Model Provider Choice (ollama or anthropic)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
RETRIEVAL_TOP_K=3
SIMILARITY_THRESHOLD=0.3
GROUNDING_THRESHOLD=0.35
```

---

## Local Development Workflow

### Option A: Running with Docker Compose (Recommended)

1. Start all services:
   ```bash
   docker compose up --build
   ```
2. Access the components:
   - **Frontend UI**: http://localhost:3000
   - **FastAPI Backend**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs

---

### Option B: Local Manual Setup (Python + Node.js)

#### 1. Python Virtual Environment Setup (Backend)
```bash
# Create and activate virtual environment
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Initialize Database Schema
Run the database schema script on your PostgreSQL/Supabase instance using `init_db.sql`.

#### 3. Run Ingestion Pipeline (Optional / Pre-populating Data)
To clone transcript data and ingest embeddings into Supabase:
```bash
python -m ingestion.pipeline
```

#### 4. Run the API Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 5. Frontend Setup
In a separate terminal window:
```bash
cd frontend
npm install
npm start
```
The React frontend will start at http://localhost:3000.

---

## How to Run Tests

The repository includes test suites covering API endpoints, agent routing/grounding, script injection/sandboxing security, and vector retrieval logic.

### 1. Run Automated Test Suite
Run tests using Python inside your activated virtual environment:

```bash
python run_tests.py
```

Alternatively, run `pytest` directly:
```bash
pytest -v
```

### 2. Verified Test Coverage
- `tests/test_api.py`: Validates FastAPI `/health`, `/health/ready`, and `/config` endpoints.
- `tests/test_agents.py`: Tests `QAAgent`, `Ship30Agent`, low-grounding fallbacks, and `AgentOrchestrator` routing.
- `tests/test_artifact_sandbox.py`: Verifies Markdown/HTML artifact validation, script injection detection (`<script>` and `on*` inline event handlers), and iframe sandbox policy compliance.
- `tests/test_retrieval.py`: Tests embedding generation, vector similarity RPC lookup, and singleton service instantiation.

---

## Troubleshooting

### 1. Ollama Connection Error (`ProviderUnavailableError`)
- **Symptom**: `Ollama isn't reachable at http://localhost:11434` or API returns `503 Service Unavailable`.
- **Solution**:
  - Verify Ollama is installed and running (`ollama serve`).
  - Pull the required model: `ollama pull llama3.2:3b`.
  - Alternatively, switch `LLM_PROVIDER=anthropic` in `.env` and set `ANTHROPIC_API_KEY`.

### 2. Database / Vector RPC Error
- **Symptom**: `relation "transcript_chunks" does not exist` or `function match_chunks(...) does not exist`.
- **Solution**:
  - Connect to your Supabase/PostgreSQL database and execute `init_db.sql`.
  - Ensure the `pgvector` extension is enabled (`CREATE EXTENSION IF NOT EXISTS vector;`).

### 3. Missing Dependencies or Module Import Errors
- **Symptom**: `ModuleNotFoundError: No module named '...'` when running scripts or tests.
- **Solution**:
  - Ensure you are using Python 3.11+ in an active virtual environment.
  - Re-install requirements: `pip install -r requirements.txt`.

### 4. CORS or Frontend API Connection Issues
- **Symptom**: Frontend shows network error or cannot reach http://localhost:8000.
- **Solution**:
  - Verify FastAPI backend is running on port 8000 (`uvicorn api.main:app --reload --port 8000`).
  - Set `REACT_APP_API_URL=http://localhost:8000` in `frontend/.env` or `.env`.

---

## Repository Structure

```text
├── api/                   # FastAPI application & agents
│   ├── agents/            # QAAgent, Ship30Agent, ArtifactAgent, Orchestrator
│   ├── providers/         # Anthropic & Ollama provider implementations
│   ├── database.py        # Database connection & management
│   ├── retrieval.py       # Vector search & embedding retrieval
│   └── main.py            # FastAPI route definitions
├── frontend/              # React frontend application
│   ├── src/components/    # ChatPane, SessionList, ArtifactViewer
│   └── package.json       # Node dependencies
├── ingestion/             # Transcript fetching & embedding ingestion pipeline
├── docs/                  # PRD, Architecture, and Design documentation
├── tests/                 # Pytest test suite
├── init_db.sql            # Database schema & vector similarity function definition
├── run_tests.py           # Helper script to execute test suite
├── docker-compose.yml     # Multi-container orchestrator configuration
└── README.md              # Project documentation
```

---

## Documentation Links

- [`docs/PRD.md`](docs/PRD.md) - Product Requirements Document
- [`docs/architecture.md`](docs/architecture.md) - Technical Architecture Specification
- [`docs/design.md`](docs/design.md) - UI/UX Design Specs

---

## License

This project is open-source under the MIT License.
