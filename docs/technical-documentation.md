# Technical Documentation - BDE (Business Data Extraction)

## System Architecture

### High-Level Overview
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Frontend │────▶│  FastAPI Backend│────▶│   PostgreSQL    │
│     (Vite)      │     │    (Uvicorn)    │     │   (pgvector)    │
│                 │     │                 │     │                 │
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

### Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | React | 19.2.0 |
| **Frontend Build** | Vite | 7.2.4 |
| **Frontend Language** | TypeScript | 5.8.3 |
| **Backend** | FastAPI | 0.123.8 |
| **Backend Language** | Python | 3.11+ |
| **ORM** | SQLModel | 0.0.27 |
| **Database** | PostgreSQL | 14+ |
| **Vector Search** | pgvector | 0.4.2 |
| **Async Processing** | Azure Functions | v4 |
| **AI/LLM** | Azure OpenAI (GPT-4o-mini) | - |
| **Embeddings** | Azure OpenAI (text-embedding-ada-002) | - |
| **Audio Transcription** | Azure Whisper | - |
| **File Storage** | Azure Blob Storage | - |
| **Queue** | Azure Queue Storage | - |
| **Real-time** | WebSockets + Redis | 7.1.0 |
| **Authentication** | MSAL (Azure AD) | 1.34.0 |
| **Migrations** | Alembic | - |

## Database Schema

The database uses PostgreSQL with the pgvector extension for vector similarity search. Schema is managed using SQLModel and Alembic migrations.

### Core Tables

#### tenants
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    azure_tenant_id VARCHAR(255) UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, active, suspended, deleted
    is_platform_tenant BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    azure_oid VARCHAR(255) UNIQUE NOT NULL,
    azure_tid VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    role_id UUID REFERENCES roles(id),
    first_login_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### companies
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

#### documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    company_id UUID REFERENCES companies(id) NOT NULL,
    uploaded_by UUID REFERENCES users(id) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- pdf, docx, xlsx, pptx, audio, image
    file_size BIGINT,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    total_pages INTEGER,
    processed_pages INTEGER DEFAULT 0,
    error_message TEXT,
    document_type VARCHAR(255),
    document_title VARCHAR(255),
    document_summary TEXT,
    key_themes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### document_chunks
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    company_id UUID REFERENCES companies(id) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    chunk_type VARCHAR(50),  -- text, table, image_description
    page_number INTEGER,
    pillar VARCHAR(50),  -- business, development, environmental
    pillar_confidence FLOAT,
    metadata JSONB,
    embedding VECTOR(1536),  -- pgvector for semantic search
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

#### chat_sessions
```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    company_id UUID REFERENCES companies(id),
    title VARCHAR(255),
    document_ids UUID[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### chat_messages
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- user, assistant
    content TEXT NOT NULL,
    sources JSONB,
    usage_stats JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### connector_configs (QuickBooks)
```sql
CREATE TABLE connector_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    company_id UUID REFERENCES companies(id) NOT NULL,
    connector_type VARCHAR(50) NOT NULL,  -- quickbooks
    connector_status VARCHAR(50) DEFAULT 'disconnected',
    external_company_id VARCHAR(255),
    external_company_name VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    available_entities JSONB,
    enabled_entities TEXT[],
    sync_settings JSONB,
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(50),
    last_sync_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### bde_scores
```sql
CREATE TABLE bde_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    overall_score FLOAT,
    weighted_raw_score FLOAT,
    valuation_range JSONB,
    confidence VARCHAR(50),
    pillar_scores JSONB,
    document_count INTEGER,
    calculated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Roles and Permissions Tables

#### roles
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,  -- super_admin, tenant_admin, admin, user
    level INTEGER NOT NULL,  -- 0=super_admin, 1=tenant_admin, 2=admin, 3=user
    label VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### permissions
```sql
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    description TEXT
);
```

#### role_permissions
```sql
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id),
    permission_id UUID REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);
```

## Configuration

### Environment Variables

Environment variables are managed via `.env` file and loaded in `config/settings.py`.

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bde

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_WHISPER_DEPLOYMENT=whisper

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER_NAME=documents

# Azure Queue
AZURE_QUEUE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_QUEUE_NAME=document-processing

# Redis
REDIS_URL=redis://localhost:6379

# Authentication (Azure AD)
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# QuickBooks Integration
QUICKBOOKS_CLIENT_ID=your-client-id
QUICKBOOKS_CLIENT_SECRET=your-client-secret
QUICKBOOKS_REDIRECT_URI=https://your-app.com/api/connectors/oauth/callback
QUICKBOOKS_ENVIRONMENT=sandbox  # or production

# Application Settings
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:5173
MAX_UPLOAD_SIZE_MB=50
LLM_MAX_INPUT_TOKENS=10000
LLM_MAX_OUTPUT_TOKENS=16000

# Azure Functions (for webhook callbacks)
WEBAPP_WEBHOOK_URL=https://your-app.azurewebsites.net/api/documents/webhook/status
```

### Config Files

| File | Purpose |
|------|---------|
| `config/settings.py` | Main application settings, loads environment variables |
| `config/auth_settings.py` | Azure AD and JWT configuration |
| `alembic.ini` | Database migration configuration |
| `web-app/frontend/vite.config.ts` | Frontend build configuration |

## Deployment

### Docker Setup

The application can be containerized using Docker.

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=18

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    postgresql-client \
    poppler-utils \
    && curl -sL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build frontend
COPY web-app/frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY web-app/frontend ./frontend
RUN cd frontend && npm run build

# Install backend dependencies
COPY web-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY web-app .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Azure Pipelines CI/CD

The project uses Azure Pipelines for deployment. Configuration is in `azure-pipelines.yml`.

```yaml
trigger:
  branches:
    include:
      - development
      - staging

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: '18.x'

          - script: |
              cd web-app/frontend
              npm ci
              npm run build
            displayName: 'Build Frontend'

          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'

          - script: |
              cd web-app
              pip install -r requirements.txt
            displayName: 'Install Backend Dependencies'

  - stage: Deploy
    dependsOn: Build
    jobs:
      - deployment: DeployWebApp
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'Your-Azure-Subscription'
                    appName: 'bde-webapp'
                    package: '$(Pipeline.Workspace)/drop'
```

### Azure Functions Deployment

Azure Functions are deployed separately via `azure-pipelines-functionapp.yml`.

```yaml
trigger:
  branches:
    include:
      - development
  paths:
    include:
      - azure-functions/**

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: |
      cd azure-functions
      pip install -r requirements.txt --target=".python_packages/lib/site-packages"
    displayName: 'Install Dependencies'

  - task: ArchiveFiles@2
    inputs:
      rootFolderOrFile: 'azure-functions'
      includeRootFolder: false
      archiveFile: '$(Build.ArtifactStagingDirectory)/functionapp.zip'

  - task: AzureFunctionApp@1
    inputs:
      azureSubscription: 'Your-Azure-Subscription'
      appType: 'functionAppLinux'
      appName: 'bde-functions'
      package: '$(Build.ArtifactStagingDirectory)/functionapp.zip'
```

### Infrastructure Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 4 GB | 8 GB |
| **Storage** | 20 GB | 50 GB |
| **Database** | PostgreSQL 14, 2 vCPU | PostgreSQL 14, 4 vCPU |
| **Redis** | Basic tier | Standard tier |

## Security

### Authentication Flow

1. User clicks login, redirected to Azure AD
2. Azure AD authenticates user and redirects back with authorization code
3. Backend exchanges code for tokens
4. JWT token stored in HTTP-only cookie
5. All subsequent requests include JWT for authentication
6. Backend validates JWT and extracts user context

### Multi-Tenant Isolation

- Every database query includes `tenant_id` filter
- Users can only access data within their tenant
- Platform users (Super Admin) can access cross-tenant data
- Role-based permissions further restrict access within tenant

### Security Measures

| Area | Implementation |
|------|----------------|
| **Authentication** | Azure AD with MSAL, JWT tokens |
| **Authorization** | Role-based access control (RBAC) |
| **Data Isolation** | Tenant-level filtering on all queries |
| **Secrets** | Environment variables, Azure Key Vault |
| **Transport** | HTTPS required in production |
| **File Storage** | Azure Blob with SAS tokens for access |
| **SQL Injection** | SQLModel ORM with parameterized queries |
| **CORS** | Configured for specific origins in production |

### Permission Levels

| Role | Level | Access |
|------|-------|--------|
| Super Admin | 0 | Full platform access, manage tenants |
| Tenant Admin | 1 | Full tenant access, manage users |
| Admin | 2 | Manage companies and documents |
| User | 3 | Read-only or limited write access |

## Performance

### Caching Strategy

- **Redis**: Used for WebSocket pub/sub across multiple workers
- **Database**: Connection pooling via SQLModel/SQLAlchemy
- **Embeddings**: Cached during document processing to avoid recomputation

### Database Optimization

- **pgvector Index**: IVFFlat index on embeddings for fast similarity search
- **Indexes**: Standard B-tree indexes on foreign keys and frequently queried columns
- **Connection Pool**: Configured for optimal concurrent connections

### Async Processing

- Heavy document processing offloaded to Azure Functions
- Queue-based architecture prevents API timeout
- Webhook callbacks update status in real-time
- WebSocket pushes progress updates to frontend

### Token Limits

| Model | Input Tokens | Output Tokens |
|-------|--------------|---------------|
| GPT-4o-mini (Chat) | 10,000 | 16,000 |
| text-embedding-ada-002 | 8,191 | - |

## Document Processing Pipeline

### Flow

```
1. Upload → Azure Blob Storage
2. Queue message → Azure Queue Storage
3. Azure Function triggered
4. Document parsed (PDF/DOCX/XLSX/PPTX/Audio/Image)
5. Content chunked with configurable strategy
6. Embeddings generated via Azure OpenAI
7. Chunks stored in PostgreSQL with vectors
8. Webhook callback to update status
9. WebSocket notification to frontend
```

### File Type Processors

| File Type | Library | Processing |
|-----------|---------|------------|
| PDF | pdf2image, PyMuPDF | Text extraction, OCR for images |
| DOCX | python-docx | Paragraph and table extraction |
| XLSX | openpyxl | Cell data extraction |
| PPTX | python-pptx | Slide content extraction |
| Images | Pillow, Azure Document Intelligence | OCR |
| Audio | Azure Whisper | Transcription |

### Chunking Strategies

- **Fixed Size**: Split by character count with overlap
- **Semantic**: Split by paragraphs/sections preserving context
- **Table-Aware**: Keep tables as single chunks
- **Page-Based**: Respect page boundaries for PDFs

## BDE Scoring Pipeline

The scoring pipeline is a multi-stage system that analyzes company data through both LLM and deterministic code to generate comprehensive due diligence scores.

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BDE SCORING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Stage 1: Metric Extraction (LLM)                                   │
│     ↓                                                               │
│  Stage 2: Pillar Aggregation (Code)                                 │
│     ↓                                                               │
│  Stage 3A: Pillar Evaluation (LLM)                                  │
│     ↓                                                               │
│  Stage 3B: Pillar Scoring (Deterministic Code)                      │
│     ↓                                                               │
│  Stage 4: Flag Detection (LLM)                                      │
│     ↓                                                               │
│  Stage 5A: BDE Score Calculation (Math)                             │
│     ↓                                                               │
│  Stage 5B: Acquisition Recommendation (LLM)                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Metric Extraction

**Purpose:** Extract structured business metrics from document and connector chunks.

**Process:**
1. Retrieves max 150 document chunks + 50 connector chunks per pillar
2. LLM evaluates chunks against 330+ metric definitions across 8 pillars
3. Connector data prioritized over document data for quantitative metrics
4. Corroboration detection boosts confidence when metrics appear in multiple sources

**Metric Categories (8 Pillars):**

| Pillar | Example Metrics |
|--------|-----------------|
| Financial Health | ARR, MRR, Gross Margin %, EBITDA Margin %, Customer Concentration % |
| GTM Engine | ICP Defined, Pipeline Coverage Ratio, Forecast Accuracy % |
| Customer Health | GRR, NRR, Churn Rate %, NPS, CSAT |
| Product/Technical | Uptime %, Tech Debt Level, Test Coverage % |
| Operational Maturity | Core Processes Documented, SOP Coverage % |
| Leadership Transition | Founder Daily Involvement Hours, Succession Plan Exists |
| Ecosystem Dependency | Primary ERP Dependency %, Partner Tier Level |
| Service/Software Ratio | Software Revenue %, Services Revenue % |

**Confidence Levels:**
- 95-100: Exact number from connector (authoritative)
- 90-95: Explicit statement + connector corroboration
- 80-89: Clear explicit statement from documents
- 70-79: Clear implication or strong signal
- 50-69: Reasonable inference
- <50: Rejected

**Data Lineage:** Every metric stores `source_chunk_ids`, `primary_pillar`, `pillars_used_by`, and `extraction_context`.

### Stage 2: Pillar Aggregation

**Purpose:** Prepare clean, aggregated data structures for pillar evaluation.

**Process:**
1. Fetch high-confidence document chunks (>0.7)
2. Include connector chunks (always trusted)
3. Gather all metrics where pillar is primary or in `pillars_used_by`
4. Calculate data coverage using `PillarDataCoverageConfig` checklist
5. Generate metadata summary (chunk counts, confidence breakdown)

**Data Coverage Calculation:**
```
coverage% = (present_count / required_count) × 100
```

### Stage 3A: Pillar Evaluation (LLM)

**Purpose:** LLM assesses whether company meets green/yellow/red criteria for each pillar.

**Pillar Evaluation Criteria Example (Financial Health):**

| Level | Criteria |
|-------|----------|
| GREEN | >50% recurring revenue, EBITDA 15-25%, customer concentration <25%, AR days <45 |
| YELLOW | 20-50% recurring, EBITDA 5-15%, concentration 25-40%, AR days 60-90 |
| RED | <20% recurring, EBITDA <5%, concentration >40%, AR days >90 |

**LLM Output:**
- `meets_green_criteria`: boolean
- `green_criteria_strength`: 0.0-1.0
- `meets_yellow_criteria`: boolean
- `yellow_criteria_strength`: 0.0-1.0
- `fails_red_criteria`: boolean
- `key_findings`, `risks`, `data_gaps`: arrays
- `evidence_chunk_ids`: supporting chunks

**Key Design:** LLM does NOT assign scores, only YES/NO on criteria.

### Stage 3B: Pillar Scoring (Deterministic)

**Purpose:** Convert LLM's criteria evaluation into deterministic 0-5.0 scores.

**Score Ranges:**
| Score | Interpretation |
|-------|---------------|
| 5.0 | Exceptional (Top 10%) |
| 4.0-4.75 | Strong (Top 25%) |
| 3.0-3.9 | Adequate (Middle 50%) |
| 2.0-2.9 | Weak (Bottom 25%) |
| 1.0-1.9 | Fragile (Bottom 10%) |
| 0.0 | Deal-killing conditions |

**Scoring Algorithm:**
```python
if fails_red_criteria:
    score = 1.0 + (yellow_strength * 0.4) + (0.5 if meets_yellow else 0)
    score = min(2.4, score)  # Cap RED at 2.4
elif meets_green_criteria AND green_strength >= 0.7:
    score = 4.0 + (green_strength * 0.75)  # 4.0-4.75
elif meets_green_criteria AND green_strength >= 0.4:
    score = 3.9 + (green_strength * 0.4)   # 3.9-4.3
elif meets_yellow_criteria AND yellow_strength >= 0.7:
    score = 3.4 + (yellow_strength * 0.5)  # 3.4-3.9
elif meets_yellow_criteria:
    score = 2.5 + (yellow_strength * 0.4)  # 2.5-3.4
else:
    score = 1.0  # No criteria met

# Coverage adjustments
if coverage < 30%: score -= 0.3
if coverage < 50%: score -= 0.2
if coverage < 70%: score -= 0.1

# Critical missing penalty
score -= min(0.5, critical_missing_count * 0.1)
```

**Health Status Mapping:**
- GREEN: score ≥ 4.0
- YELLOW: 2.5 ≤ score < 4.0
- RED: score < 2.5

### Stage 4: Flag Detection

**Purpose:** Detect red/yellow/green flags based on comprehensive analysis.

**Flag Types:**
| Type | Description | Severity |
|------|-------------|----------|
| Red Flags | Critical risks, deal-breakers | 4-5 |
| Yellow Flags | Concerns worth noting | 2-3 |
| Green Accelerants | Positive signals | N/A |

**Examples:**
- **Red:** "Top 3 customers = 45% of ARR", "No succession plan"
- **Yellow:** "High churn rate", "CRM hygiene issues"
- **Green:** "Strong NRR >120%", "Proven expansion capability"

**Flag Structure:**
```json
{
  "flag_type": "RED",
  "flag_category": "customer_concentration",
  "flag_text": "Top 3 customers represent 45% of revenue",
  "pillar": "financial_health",
  "severity": 5,
  "evidence_chunk_ids": ["chunk-1", "chunk-2"],
  "rationale": "High concentration risk..."
}
```

### Stage 5A: BDE Score Calculation

**Purpose:** Calculate overall weighted BDE score from 8 pillar scores.

**Pillar Weights:**
| Pillar | Weight |
|--------|--------|
| Financial Health | 20% |
| GTM Engine | 15% |
| Customer Health | 15% |
| Product/Technical | 15% |
| Operational Maturity | 10% |
| Leadership Transition | 10% |
| Ecosystem Dependency | 10% |
| Service/Software Ratio | 5% |

**Calculation:**
```python
weighted_raw_score = sum(pillar_score[p] * PILLAR_WEIGHTS[p] for p in all_pillars)
# Results in 0-5.0

overall_score = int(weighted_raw_score * 20)
# Converts to 0-100 scale
```

**Valuation Range Mapping:**
| Weighted Score | Valuation Range | Interpretation |
|----------------|-----------------|----------------|
| 4.25-5.0 | 6-10x ARR | Premium (Exceptional) |
| 3.75-4.24 | 5-7x ARR | Above-market (Strong) |
| 3.00-3.74 | 3-5x ARR | Standard (Solid) |
| 2.00-2.99 | 1.5-3x ARR | Discounted (Weak) |
| 1.00-1.99 | Deep Discount | High Risk |
| 0.0-0.99 | Walk-away | Uninvestable |

### Stage 5B: Acquisition Recommendation

**Purpose:** Generate executive-level acquisition recommendation.

**Output Structure:**
```json
{
  "recommendation": "STRONG BUY | BUY WITH CONDITIONS | HOLD | PASS",
  "confidence": 85,
  "rationale": "Executive summary rationale",
  "value_drivers": [
    "Strong recurring revenue model (72% of revenue)",
    "Proven GTM with defined ICP"
  ],
  "key_risks": [
    "Customer concentration risk (top 3 = 38%)",
    "Founder dependency in sales"
  ],
  "100_day_plan": [
    {"priority": 1, "action": "Hire VP Sales"},
    {"priority": 2, "action": "Implement CRM discipline"}
  ],
  "suggested_valuation_multiple": "5.5x ARR",
  "valuation_adjustments": [
    {"adjustment": "Customer concentration", "impact": "-0.5x"}
  ]
}
```

### Scoring Database Tables

| Table | Purpose |
|-------|---------|
| `company_metrics` | Extracted signals with source lineage |
| `pillar_evaluation_criteria` | LLM evaluation results (Stage 3A) |
| `company_pillar_scores` | Deterministic scores (Stage 3B) |
| `company_flags` | Detected red/yellow/green flags |
| `company_bde_scores` | Overall scores and valuation range |
| `acquisition_recommendations` | Final recommendation |
| `pillar_data_coverage_config` | Required data checklist |

### Real-Time Progress Tracking

WebSocket endpoint at `/api/scoring/ws` provides real-time updates:

```json
{
  "type": "scoring_progress",
  "company_id": "...",
  "stage": 3,
  "stage_name": "Evaluating Pillars",
  "progress": 45,
  "status": "processing",
  "current_pillar": "financial_health",
  "pillar_progress": {
    "financial_health": {
      "status": "completed",
      "progress": 100,
      "score": 4.2,
      "health_status": "green"
    },
    "gtm_engine": {
      "status": "processing",
      "progress": 50
    }
  }
}
```

**Stage Weights for Progress:**
- Stage 1 (Metric Extraction): 20%
- Stage 2 (Aggregation): 10%
- Stage 3 (Evaluation & Scoring): 40%
- Stage 4 (Flag Detection): 15%
- Stage 5 (BDE & Recommendation): 15%

### Conflict Resolution

**Metric Conflicts:**
1. Source Priority: Connector (100) > Document (50)
2. Same Priority: Newer date wins
3. Same Date: Higher confidence wins (10% threshold)
4. Unclear: Flagged for analyst review (`needs_analyst_review=true`)

### Performance Profile

| Stage | Typical Duration |
|-------|-----------------|
| Stage 1 (Metric Extraction) | 30-60s |
| Stage 2 (Aggregation) | 5s |
| Stage 3 (Eval/Scoring × 8 pillars) | 2-3 min |
| Stage 4 (Flag Detection) | 30s |
| Stage 5 (BDE + Recommendation) | 30s |
| **Total** | **3-5 minutes** |

### Key Design Decisions

1. **LLM Never Scores** - LLM evaluates criteria YES/NO, code assigns scores deterministically
2. **Metrics First** - Metrics extracted before evaluation (proper dependency flow)
3. **Evidence Traceability** - Every score links to evaluation → chunks (complete audit trail)
4. **Connector Priority** - Financial metrics prefer connector data (more authoritative)
5. **Deterministic Scoring** - Rubric-based, repeatable, auditable
6. **WebSocket Progress** - Real-time updates during multi-minute scoring

## Development Guidelines

### Code Style

**Frontend:**
- ESLint configured for React/TypeScript
- Prettier for formatting
- Component-based architecture

**Backend:**
- PEP 8 style guide
- Type hints throughout
- Async/await for I/O operations

### Project Structure

```
web-app/
├── main.py              # FastAPI app entry point
├── api/                 # Route handlers by module
│   ├── auth/
│   ├── document/
│   ├── chat/
│   └── ...
├── database/
│   ├── models/          # SQLModel definitions
│   └── connection.py    # DB connection management
├── config/              # Configuration classes
├── core/                # Core utilities (permissions)
└── alembic/             # Database migrations

frontend/
├── src/
│   ├── pages/           # Page components
│   ├── components/      # Reusable UI components
│   ├── api/             # API service modules
│   ├── context/         # React Context providers
│   ├── hooks/           # Custom React hooks
│   └── utils/           # Utility functions
└── vite.config.ts
```

### Git Workflow

1. Create feature branch from `development`
2. Make changes with descriptive commits
3. Create pull request to `development`
4. Code review required
5. Merge triggers CI/CD to dev environment
6. Promote to `staging` for testing
7. Promote to `main` for production

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Database connection failed | Wrong credentials or DB not running | Check `DATABASE_URL` in `.env`, ensure PostgreSQL is accessible |
| pgvector extension not found | Extension not installed | Run `CREATE EXTENSION vector;` in PostgreSQL |
| Document processing stuck | Azure Function not running or queue issue | Check Azure Function logs, verify queue connection |
| WebSocket not connecting | Redis not running or wrong URL | Check `REDIS_URL`, ensure Redis is accessible |
| Authentication fails | Azure AD misconfiguration | Verify `AZURE_AD_*` settings, check redirect URIs |
| Embeddings fail | OpenAI quota exceeded or wrong endpoint | Check Azure OpenAI quotas, verify endpoint URL |
| File upload fails | File too large or wrong type | Check `MAX_UPLOAD_SIZE_MB`, verify file extension |

### Logs Location

| Environment | Location |
|-------------|----------|
| Local Development | Console output via uvicorn |
| Azure App Service | Azure Portal → App Service → Log stream |
| Azure Functions | Azure Portal → Function App → Monitor |

### Health Checks

- **API Health**: `GET /health` returns `{"status": "healthy"}`
- **Database**: Check via Alembic migration status
- **Redis**: Connection test on startup
- **Azure Storage**: Connection test on first upload

## Monitoring

### Azure Application Insights

- Response times and error rates
- Dependency tracking (database, external APIs)
- Custom events for document processing
- User analytics from frontend

### Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold |
|--------|-------------------|-------------------|
| API Response Time | > 2s | > 5s |
| Error Rate | > 1% | > 5% |
| Document Processing Time | > 5 min | > 15 min |
| Database Connections | > 80% pool | > 95% pool |
| Queue Length | > 100 messages | > 500 messages |
