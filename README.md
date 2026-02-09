# BDE (Business Data Extraction)

A full-stack document intelligence platform with AI-powered chat, document processing, and business data extraction capabilities.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, React Router, Axios |
| **Backend** | FastAPI, Python 3.11+, SQLModel, Alembic |
| **Database** | PostgreSQL with pgvector extension |
| **Cloud** | Microsoft Azure (App Service, Functions, Blob Storage, Queue Storage) |
| **AI/ML** | Azure OpenAI (GPT-4o-mini, Embeddings, Whisper for audio transcription) |
| **Real-time** | WebSockets, Redis Pub/Sub |
| **Auth** | Microsoft Azure AD (MSAL), JWT |

## Features

### Document Management
- Upload and process multiple file types: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), images, and audio files
- Automatic document chunking with configurable strategies
- Vector embeddings generation for semantic search
- Document status tracking (pending, processing, completed, failed)
- BDE Pillar classification (Business, Development, Environmental)
- Azure Blob Storage for secure file storage

### AI Copilot
- RAG (Retrieval-Augmented Generation) powered chat interface
- Real-time responses via WebSocket connections
- Chat session management with history
- Customizable prompt templates
- Context-aware responses using document embeddings

### QuickBooks Integration
- OAuth 2.0 authentication flow
- Automatic data synchronization
- Raw data storage and processing
- Connector status monitoring

### Multi-Tenant Architecture
- Complete tenant isolation
- Company management within tenants
- Role-Based Access Control (RBAC)
- Hierarchical permission system
- Protected routes with permission validation

### Async Document Processing
- Queue-based processing via Azure Functions
- Automatic retry with exponential backoff
- Webhook callbacks for status updates
- Support for large file processing
- Real-time progress updates via WebSocket

### Scoring System
- Customizable evaluation criteria
- Real-time scoring with WebSocket updates
- Results tracking and reporting
- Configurable scoring prompts

## Project Structure

```
BDE/
├── web-app/                          # Main application
│   ├── main.py                       # FastAPI entry point
│   ├── requirements.txt              # Python dependencies
│   ├── alembic/                      # Database migrations
│   ├── alembic.ini                   # Alembic configuration
│   │
│   ├── frontend/                     # React SPA
│   │   ├── src/
│   │   │   ├── pages/                # Page components
│   │   │   ├── components/           # Reusable UI components
│   │   │   ├── api/                  # API service modules
│   │   │   ├── context/              # React Context (Auth, Permission)
│   │   │   ├── routes/               # Route configuration
│   │   │   ├── hooks/                # Custom React hooks
│   │   │   └── utils/                # Utility functions
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── api/                          # FastAPI route handlers
│   │   ├── auth/                     # Authentication endpoints
│   │   ├── tenant/                   # Tenant management
│   │   ├── user/                     # User management
│   │   ├── company/                  # Company management
│   │   ├── document/                 # Document upload & management
│   │   ├── chat/                     # Copilot chat functionality
│   │   ├── connector/                # External integrations
│   │   ├── scoring/                  # Scoring/evaluation
│   │   ├── prompt/                   # Prompt templates
│   │   └── onboarding/               # User onboarding
│   │
│   ├── database/
│   │   ├── models/                   # SQLModel definitions
│   │   ├── connection.py             # Database connection
│   │   └── seed.py                   # Database seeding
│   │
│   ├── config/
│   │   ├── settings.py               # App configuration
│   │   └── auth_settings.py          # Auth configuration
│   │
│   └── core/
│       └── permissions.py            # Permission definitions
│
├── azure-functions/                  # Serverless processing
│   ├── function_app.py               # Azure Functions entry point
│   ├── requirements.txt              # Function dependencies
│   └── shared/                       # Shared modules
│       ├── services/
│       │   ├── chunking/             # Document chunking strategies
│       │   ├── processors/           # File type processors
│       │   ├── document_processor.py
│       │   ├── embedding_service.py
│       │   └── llm_service.py
│       └── utils/
│
├── azure-pipelines.yml               # Web app CI/CD
└── azure-pipelines-functionapp.yml   # Functions CI/CD
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ with pgvector extension
- Redis (for WebSocket pub/sub)
- Azure account with the following services:
  - Azure OpenAI
  - Azure Blob Storage
  - Azure Queue Storage
  - Azure Functions (for production)

### Backend Setup

```bash
# Navigate to web-app directory
cd web-app

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed the database (optional)
python -m database.seed

# Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd web-app/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Azure Functions Setup

```bash
# Navigate to azure-functions directory
cd azure-functions

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally with Azure Functions Core Tools
func start
```

## Environment Variables

Create a `.env` file in `web-app/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bde

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_WHISPER_DEPLOYMENT=whisper

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER_NAME=documents

# Azure Queue
AZURE_QUEUE_CONNECTION_STRING=your-connection-string
AZURE_QUEUE_NAME=document-processing

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_TENANT_ID=your-tenant-id
JWT_SECRET_KEY=your-secret-key

# QuickBooks
QUICKBOOKS_CLIENT_ID=your-client-id
QUICKBOOKS_CLIENT_SECRET=your-client-secret
QUICKBOOKS_REDIRECT_URI=your-redirect-uri
```

## API Documentation

Once the backend is running, access the API documentation at:

- **Swagger UI**: http://localhost:8000/docs

## Deployment

### Azure Pipelines

The project includes CI/CD pipelines for automated deployment:

- **azure-pipelines.yml** - Deploys the web application to Azure App Service
- **azure-pipelines-functionapp.yml** - Deploys Azure Functions

### Manual Deployment

1. Build the frontend: `cd web-app/frontend && npm run build`
2. Deploy web-app to Azure App Service
3. Deploy azure-functions to Azure Functions
4. Configure environment variables in Azure Portal
5. Set up Azure Blob Storage containers and Queue

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Frontend │────▶│  FastAPI Backend│────▶│   PostgreSQL    │
│                 │     │                 │     │   (pgvector)    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │ WebSocket
                                 ▼
                        ┌─────────────────┐
                        │      Redis      │
                        │    (Pub/Sub)    │
                        └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Azure Blob     │     │  Azure Queue    │     │  Azure OpenAI   │
│  Storage        │     │  Storage        │     │  (GPT, Embed)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Azure Functions │
                        │ (Doc Processing)│
                        └─────────────────┘
```

## Supported File Types

| Type | Extensions | Processing |
|------|------------|------------|
| PDF | .pdf | Text extraction, OCR for scanned documents |
| Word | .docx | Full text and formatting extraction |
| PowerPoint | .pptx | Slide content extraction |
| Excel | .xlsx | Cell data extraction |
| Images | .png, .jpg, .jpeg | OCR via Azure Document Intelligence |
| Audio | .mp3, .wav, .m4a | Transcription via Azure Whisper |
# bde-edits
