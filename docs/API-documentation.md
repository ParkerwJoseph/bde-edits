# API Documentation - BDE (Business Data Extraction)

## Base URL
```
Production: https://your-app.azurewebsites.net/api
Development: http://localhost:8000/api
```

## Authentication
The API uses Microsoft Azure AD authentication with JWT tokens. All endpoints (except onboarding) require a valid Bearer token.

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

## Endpoints

### Auth

#### GET /auth/login
Redirects to Azure AD login page for authentication.

**Response:** Redirect to Azure authentication URL

---

#### GET /auth/callback
Handles OAuth callback from Azure AD after successful login.

**Query Parameters:**
- `code` (string): Authorization code from Azure AD

**Response:** Redirect to frontend with auth cookie set

---

#### GET /auth/me
Get current authenticated user with full details.

**Response:**
```json
{
  "id": "uuid",
  "azure_oid": "azure-object-id",
  "azure_tid": "azure-tenant-id",
  "email": "user@example.com",
  "display_name": "John Doe",
  "is_active": true,
  "first_login_at": "2025-01-15T10:00:00Z",
  "last_login_at": "2025-01-20T14:30:00Z",
  "created_at": "2025-01-15T10:00:00Z",
  "tenant": {
    "id": "tenant-uuid",
    "company_name": "Acme Corp"
  },
  "role": {
    "name": "admin",
    "level": 2
  },
  "permissions": ["documents:read", "documents:write", "chat:access"]
}
```

---

#### POST /auth/logout
Logout and clear session cookie.

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

#### GET /auth/permissions
Get all available permissions for frontend.

**Response:**
```json
{
  "permissions": [
    {
      "name": "documents:read",
      "category": "Documents",
      "description": "View documents"
    }
  ]
}
```

---

#### GET /auth/roles
Get all available roles.

**Response:**
```json
{
  "roles": [
    {
      "name": "admin",
      "level": 2,
      "label": "Administrator",
      "description": "Full access to tenant resources"
    }
  ]
}
```

---

### Tenants

#### POST /tenants
Create a new tenant. Requires Super Admin role.

**Request Body:**
```json
{
  "company_name": "Acme Corporation"
}
```

**Response:**
```json
{
  "id": "tenant-uuid",
  "azure_tenant_id": null,
  "company_name": "Acme Corporation",
  "status": "pending",
  "is_platform_tenant": false,
  "consent_timestamp": null,
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:00:00Z"
}
```

---

#### GET /tenants
List all tenants. Platform users only.

**Query Parameters:**
- `skip` (int, optional): Pagination offset (default: 0)
- `limit` (int, optional): Page size (default: 100)

**Response:**
```json
{
  "tenants": [...],
  "total": 25
}
```

---

#### GET /tenants/{tenant_id}
Get tenant details by ID.

**Response:** Tenant object

---

#### PUT /tenants/{tenant_id}
Update tenant details. Super Admin only.

**Request Body:**
```json
{
  "company_name": "New Company Name",
  "status": "active"
}
```

---

#### DELETE /tenants/{tenant_id}
Delete a tenant. Super Admin only.

**Response:** 204 No Content

---

#### POST /tenants/{tenant_id}/onboarding
Generate onboarding package for a tenant.

**Response:**
```json
{
  "tenant_id": "uuid",
  "company_name": "Acme Corp",
  "onboarding_url": "https://app.com/onboard/ABC123",
  "onboarding_code": "ABC123",
  "expires_at": "2025-01-27T10:00:00Z"
}
```

---

### Users

#### GET /users
List users. Platform admins see all users, tenant users see only their tenant.

**Query Parameters:**
- `tenant_id` (uuid, optional): Filter by tenant
- `skip` (int, optional): Pagination offset
- `limit` (int, optional): Page size

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "John Doe",
      "is_active": true,
      "first_login_at": "2025-01-15T10:00:00Z",
      "last_login_at": "2025-01-20T14:30:00Z",
      "created_at": "2025-01-15T10:00:00Z",
      "tenant_name": "Acme Corp",
      "role_name": "admin"
    }
  ],
  "total": 50
}
```

---

#### GET /users/{user_id}
Get user details by ID.

---

#### PUT /users/{user_id}/role
Update user's role.

**Request Body:**
```json
{
  "role_name": "admin"
}
```

---

#### PUT /users/{user_id}/status
Enable or disable user account.

**Request Body:**
```json
{
  "is_active": false
}
```

---

#### DELETE /users/{user_id}
Delete a user.

**Response:** 204 No Content

---

### Companies

#### POST /companies
Create a new company for current tenant.

**Request Body:**
```json
{
  "name": "Target Company LLC"
}
```

**Response:**
```json
{
  "id": "company-uuid",
  "tenant_id": "tenant-uuid",
  "name": "Target Company LLC",
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:00:00Z"
}
```

---

#### GET /companies
List all companies for current tenant.

**Query Parameters:**
- `skip` (int, optional): Pagination offset
- `limit` (int, optional): Page size

**Response:**
```json
{
  "companies": [...],
  "total": 10
}
```

---

#### GET /companies/{company_id}
Get company details.

---

#### PATCH /companies/{company_id}
Update company details.

**Request Body:**
```json
{
  "name": "Updated Company Name"
}
```

---

#### DELETE /companies/{company_id}
Delete a company and all associated data (documents, chunks, scores).

**Response:** 204 No Content

---

### Documents

#### POST /documents/upload
Upload a document for processing.

**Request:** `multipart/form-data`
- `file`: Document file (PDF, DOCX, XLSX, PPTX, images, audio)
- `company_id`: Target company UUID

**Response:**
```json
{
  "document_id": "doc-uuid",
  "filename": "report.pdf",
  "status": "pending",
  "message": "Document uploaded successfully"
}
```

---

#### GET /documents
List all documents for tenant.

**Query Parameters:**
- `status` (string, optional): Filter by status (pending, processing, completed, failed)
- `file_type` (string, optional): Filter by file type
- `company_id` (uuid, optional): Filter by company
- `skip`, `limit`: Pagination

**Response:**
```json
{
  "documents": [
    {
      "id": "doc-uuid",
      "tenant_id": "tenant-uuid",
      "company_id": "company-uuid",
      "uploaded_by": "user-uuid",
      "filename": "unique-filename.pdf",
      "original_filename": "report.pdf",
      "file_type": "pdf",
      "file_size": 1048576,
      "status": "completed",
      "total_pages": 25,
      "processed_pages": 25,
      "document_type": "Financial Report",
      "document_title": "Q4 2024 Financial Report",
      "document_summary": "Quarterly financial summary...",
      "created_at": "2025-01-20T10:00:00Z",
      "updated_at": "2025-01-20T10:15:00Z"
    }
  ],
  "total": 100
}
```

---

#### GET /documents/{document_id}
Get document with its chunks.

**Response:**
```json
{
  "document": {...},
  "chunks": [...],
  "chunk_count": 45
}
```

---

#### GET /documents/{document_id}/status
Get processing status of a document.

**Response:**
```json
{
  "document_id": "doc-uuid",
  "status": "processing",
  "total_pages": 25,
  "processed_pages": 12,
  "error_message": null,
  "chunk_count": 24
}
```

---

#### GET /documents/{document_id}/chunks
Get chunks for a document with filtering.

**Query Parameters:**
- `pillar` (string, optional): Filter by BDE pillar (business, development, environmental)
- `chunk_type` (string, optional): Filter by chunk type
- `page_number` (int, optional): Filter by page number

---

#### GET /documents/{document_id}/download
Get signed URL to download/preview document.

**Response:**
```json
{
  "download_url": "https://storage.blob.core.windows.net/...",
  "filename": "report.pdf",
  "content_type": "application/pdf"
}
```

---

#### DELETE /documents/{document_id}
Delete document and its chunks.

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

---

#### WebSocket /documents/ws
Real-time document processing progress.

**Usage:**
1. Connect to WebSocket
2. Send tenant_id after connection
3. Receive progress updates:
```json
{
  "type": "progress",
  "document_id": "doc-uuid",
  "status": "processing",
  "processed_pages": 12,
  "total_pages": 25
}
```

---

### Chat

#### GET /chat/sessions
List all chat sessions for current user.

**Query Parameters:**
- `company_id` (uuid, optional): Filter by company
- `skip`, `limit`: Pagination

**Response:**
```json
{
  "sessions": [
    {
      "id": "session-uuid",
      "user_id": "user-uuid",
      "company_id": "company-uuid",
      "title": "Revenue Analysis",
      "document_ids": ["doc-1", "doc-2"],
      "created_at": "2025-01-20T10:00:00Z",
      "updated_at": "2025-01-20T14:30:00Z"
    }
  ],
  "total": 15
}
```

---

#### POST /chat/sessions
Create a new chat session.

**Request Body:**
```json
{
  "title": "Financial Review",
  "company_id": "company-uuid",
  "document_ids": ["doc-1", "doc-2"]
}
```

---

#### GET /chat/sessions/{session_id}
Get chat session with all messages.

---

#### PATCH /chat/sessions/{session_id}
Update chat session title or documents.

**Request Body:**
```json
{
  "title": "Updated Title",
  "document_ids": ["doc-1", "doc-2", "doc-3"]
}
```

---

#### DELETE /chat/sessions/{session_id}
Delete chat session and messages.

---

#### POST /chat/chat
Chat with documents using RAG.

**Request Body:**
```json
{
  "query": "What was the revenue in Q4?",
  "session_id": "session-uuid",
  "company_id": "company-uuid",
  "document_ids": ["doc-1", "doc-2"],
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "According to the Q4 Financial Report, revenue was $2.5M...",
  "sources": [
    {
      "document_id": "doc-1",
      "filename": "Q4-report.pdf",
      "page_number": 3
    }
  ],
  "chunks": [...],
  "usage_stats": {
    "prompt_tokens": 1500,
    "completion_tokens": 200
  },
  "session_id": "session-uuid"
}
```

---

#### POST /chat/search
Semantic search across document chunks.

**Request Body:**
```json
{
  "query": "revenue growth",
  "document_ids": ["doc-1", "doc-2"],
  "top_k": 10,
  "similarity_threshold": 0.7
}
```

**Response:**
```json
{
  "chunks": [...],
  "total": 10
}
```

---

#### WebSocket /chat/ws
WebSocket for streaming chat responses.

---

### Connectors (QuickBooks)

#### GET /connectors/info
Get QuickBooks connector info and configuration status.

**Response:**
```json
{
  "connector_type": "quickbooks",
  "display_name": "QuickBooks Online",
  "description": "Connect to QuickBooks for financial data",
  "is_configured": true
}
```

---

#### GET /connectors
List all QuickBooks connector configurations for tenant.

**Query Parameters:**
- `company_id` (uuid, optional): Filter by company

---

#### POST /connectors/oauth/start
Start QuickBooks OAuth flow.

**Request Body:**
```json
{
  "company_id": "company-uuid"
}
```

**Response:**
```json
{
  "authorization_url": "https://appcenter.intuit.com/connect/oauth2...",
  "state": "random-state-string"
}
```

---

#### GET /connectors/oauth/callback
Handle QuickBooks OAuth callback (internal use).

---

#### GET /connectors/{connector_id}/entities
Discover available entities from QuickBooks.

**Query Parameters:**
- `refresh` (bool, optional): Force refresh from QuickBooks

**Response:**
```json
{
  "entities": [
    {
      "name": "Invoice",
      "count": 150,
      "last_updated": "2025-01-20T10:00:00Z"
    },
    {
      "name": "Customer",
      "count": 45
    }
  ],
  "company_info": {
    "name": "Acme Corp",
    "country": "US"
  }
}
```

---

#### POST /connectors/{connector_id}/sync
Start syncing data from QuickBooks.

**Request Body:**
```json
{
  "entities": ["Invoice", "Customer", "Vendor"],
  "full_sync": false
}
```

**Response:**
```json
{
  "sync_log_id": "sync-uuid",
  "status": "started",
  "message": "Sync started for 3 entities"
}
```

---

#### GET /connectors/{connector_id}/sync/{sync_log_id}
Get status of sync operation.

**Response:**
```json
{
  "id": "sync-uuid",
  "status": "completed",
  "sync_type": "incremental",
  "entities_requested": ["Invoice", "Customer"],
  "entities_completed": ["Invoice", "Customer"],
  "total_records_fetched": 195,
  "total_records_processed": 195,
  "started_at": "2025-01-20T10:00:00Z",
  "completed_at": "2025-01-20T10:05:00Z",
  "error_message": null
}
```

---

#### POST /connectors/{connector_id}/ingest
Queue raw QuickBooks data for processing into chunks.

**Request Body:**
```json
{
  "entity_types": ["Invoice", "Customer"]
}
```

---

#### GET /connectors/{connector_id}/stats
Get statistics for QuickBooks connector.

**Response:**
```json
{
  "connector_id": "connector-uuid",
  "connector_type": "quickbooks",
  "connector_status": "connected",
  "external_company_name": "Target Company",
  "raw_data_records": 195,
  "unprocessed_records": 0,
  "processed_records": 195,
  "chunks_created": 450,
  "sync_operations": 5,
  "last_sync_at": "2025-01-20T10:05:00Z",
  "last_sync_status": "completed"
}
```

---

#### WebSocket /connectors/ws/{tenant_id}
WebSocket for real-time ingestion progress updates.

---

### Scoring

#### POST /scoring/companies/{company_id}/score
Trigger BDE scoring pipeline. Progress updates via WebSocket.

**Request Body:**
```json
{
  "recompute": false
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Scoring pipeline started",
  "company_id": "company-uuid",
  "job_started": true
}
```

---

#### GET /scoring/companies/{company_id}/bde-score
Get overall BDE score for company.

**Response:**
```json
{
  "company_id": "company-uuid",
  "overall_score": 78.5,
  "weighted_raw_score": 235.5,
  "valuation_range": {
    "min": 2500000,
    "max": 3500000
  },
  "confidence": "high",
  "calculated_at": "2025-01-20T10:30:00Z",
  "pillar_scores": {
    "business": 82,
    "development": 75,
    "environmental": 78
  }
}
```

---

#### GET /scoring/companies/{company_id}/pillars/{pillar}
Get detailed scoring for a specific pillar (business, development, environmental).

**Response:**
```json
{
  "pillar": "business",
  "score": 82,
  "health_status": "healthy",
  "justification": "Strong revenue growth and customer retention...",
  "data_coverage_percent": 85,
  "confidence": "high",
  "key_findings": ["Revenue grew 25% YoY", "Customer churn below 5%"],
  "risks": ["Concentration in single market"],
  "data_gaps": ["Missing employee retention data"],
  "evidence_chunk_ids": ["chunk-1", "chunk-2"]
}
```

---

#### GET /scoring/companies/{company_id}/metrics
Get all extracted metrics for company.

**Response:**
```json
{
  "metrics": {
    "revenue": {"value": 2500000, "source": "Q4-report.pdf"},
    "employee_count": {"value": 45, "source": "HR-summary.docx"}
  },
  "conflicts": []
}
```

---

#### GET /scoring/companies/{company_id}/flags
Get all detected flags (red, yellow, green).

**Response:**
```json
{
  "red_flags": [
    {"flag": "High customer concentration", "details": "Top 3 customers = 60% revenue"}
  ],
  "yellow_flags": [
    {"flag": "Limited geographic diversity"}
  ],
  "green_accelerants": [
    {"flag": "Strong recurring revenue", "details": "80% ARR"}
  ]
}
```

---

#### GET /scoring/companies/{company_id}/recommendation
Get acquisition recommendation.

**Response:**
```json
{
  "recommendation": "proceed",
  "confidence": "high",
  "rationale": "Strong fundamentals with manageable risks...",
  "value_drivers": ["Recurring revenue", "Market position"],
  "key_risks": ["Customer concentration"],
  "100_day_plan": ["Diversify customer base", "Expand to new markets"],
  "suggested_valuation_multiple": 4.5,
  "valuation_adjustments": ["+0.5x for recurring revenue"],
  "generated_at": "2025-01-20T10:30:00Z"
}
```

---

#### GET /scoring/companies/{company_id}/analysis-status
Get analysis status to check if scoring can run.

**Response:**
```json
{
  "company_id": "company-uuid",
  "has_score": true,
  "is_running": false,
  "last_scored_at": "2025-01-20T10:30:00Z",
  "document_count": 15,
  "last_scored_doc_count": 12,
  "has_new_documents": true,
  "has_new_connector_data": false,
  "connector_count": 1,
  "can_run_analysis": true,
  "message": "New documents available for analysis"
}
```

---

#### WebSocket /scoring/ws
WebSocket for real-time scoring pipeline progress.

**Usage:**
1. Connect to WebSocket
2. Send tenant_id after connection
3. Receive progress updates:
```json
{
  "type": "scoring_progress",
  "company_id": "company-uuid",
  "stage": "extracting_metrics",
  "progress": 45,
  "message": "Processing Business pillar..."
}
```

---

### Prompts

#### GET /prompt
Get active RAG prompt template.

**Response:**
```json
{
  "id": "prompt-uuid",
  "name": "default_rag",
  "description": "Default RAG prompt for document Q&A",
  "template": "You are an AI assistant...",
  "is_active": true,
  "version": 3,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-20T14:00:00Z",
  "updated_by": "user-uuid"
}
```

---

#### PUT /prompt
Update RAG prompt template.

**Request Body:**
```json
{
  "template": "You are a helpful AI assistant..."
}
```

---

#### POST /prompt/reset
Reset RAG prompt to default template.

---

#### GET /prompt/default
Get default RAG prompt for reference.

**Response:**
```json
{
  "template": "You are an AI assistant helping users..."
}
```

---

### Onboarding

#### GET /onboarding/validate/{code}
Validate onboarding code without starting the flow.

**Response:**
```json
{
  "valid": true,
  "tenant_id": "tenant-uuid",
  "company_name": "Acme Corp",
  "error": null
}
```

---

#### GET /onboarding/start/{code}
Start Azure AD admin consent flow for tenant onboarding.

**Response:** Redirect to Microsoft admin consent page

---

#### GET /onboarding/callback
Handle Azure AD admin consent callback (internal use).

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 409 | Conflict - Resource already exists |
| 422 | Validation Error |
| 500 | Internal Server Error |

## Error Format

```json
{
  "detail": "Error message describing the issue"
}
```

Validation errors return additional details:
```json
{
  "detail": [
    {
      "loc": ["body", "company_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Code Examples

### Python (Upload Document)
```python
import requests

headers = {"Authorization": f"Bearer {access_token}"}

# Upload a document
with open("report.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/documents/upload",
        headers=headers,
        files={"file": f},
        data={"company_id": "company-uuid"}
    )
print(response.json())
```

### Python (Chat with Documents)
```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/api/chat/chat",
    headers=headers,
    json={
        "query": "What is the company revenue?",
        "company_id": "company-uuid",
        "document_ids": ["doc-1", "doc-2"],
        "top_k": 5
    }
)
print(response.json())
```

### cURL (Get BDE Score)
```bash
curl -X GET \
  "http://localhost:8000/api/scoring/companies/{company_id}/bde-score" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### JavaScript (WebSocket Connection)
```javascript
const ws = new WebSocket("ws://localhost:8000/api/documents/ws");

ws.onopen = () => {
  ws.send(JSON.stringify({ tenant_id: "your-tenant-id" }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Progress update:", data);
};
```

## Rate Limiting

Rate limiting should be configured at the infrastructure level (Azure API Management or similar). The application does not implement rate limiting internally.

## Support

- **API Documentation (Swagger):** http://localhost:8000/docs
- **Issues:** Contact the development team or open a ticket in the project repository.
