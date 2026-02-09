# User Manual - BDE (Business Data Extraction)

## Getting Started

### What is BDE?
BDE (Business Data Extraction) is an AI-powered platform designed to help you analyze business documents, extract key metrics, and generate comprehensive scoring for due diligence and acquisition analysis. You can upload documents, chat with your data using AI, connect to QuickBooks for financial data, and receive automated BDE scoring across Business, Development, and Environmental pillars.

### System Requirements
- **Browser:** A modern web browser (Chrome, Firefox, Safari, or Edge)
- **Internet:** A stable internet connection
- **Account:** Microsoft Azure AD account for authentication

## First Time Setup

### 1. Accessing the Application
1. Navigate to the application URL provided by your administrator
2. Click "Sign in with Microsoft"
3. Authenticate using your Microsoft account
4. If this is your first login, you may need to grant permissions

### 2. Interface Overview
After logging in, you will see the main dashboard with:
- **Sidebar Navigation:** Access to different sections (Dashboard, Documents, Companies, Chat, Connectors, Analysis)
- **Company Selector:** Switch between companies you're analyzing
- **User Menu:** Profile settings and logout option

## Core Features

### Feature 1: Company Management

**Purpose:** Organize your analysis by creating separate companies for each business you're evaluating.

**How to create a company:**
1. Navigate to **Companies** in the sidebar
2. Click **"New Company"**
3. Enter the company name
4. Click **"Create"**

**How to switch companies:**
1. Use the company selector dropdown in the header
2. Select the company you want to work with
3. All data (documents, chat, analysis) will filter to that company

---

### Feature 2: Document Upload & Management

**Purpose:** Upload business documents for AI analysis and scoring.

**Supported file types:**
| Type | Extensions |
|------|------------|
| PDF | .pdf |
| Word | .docx |
| Excel | .xlsx |
| PowerPoint | .pptx |
| Images | .png, .jpg, .jpeg |
| Audio | .mp3, .wav, .m4a |

**How to upload documents:**
1. Navigate to **Documents** in the sidebar
2. Click **"Upload Document"**
3. Select files from your computer (or drag and drop)
4. Select the target company
5. Click **"Upload"**

**Document processing:**
- After upload, documents are processed automatically
- You'll see a progress indicator showing processing status
- Processing extracts text, creates searchable chunks, and generates embeddings
- Status will change from "Pending" → "Processing" → "Completed"

**How to view documents:**
1. Go to **Documents**
2. Click on any document to see details
3. View extracted chunks, metadata, and download the original file

**How to delete documents:**
1. Go to **Documents**
2. Click the delete icon on the document row
3. Confirm deletion (this removes all associated data)

---

### Feature 3: AI Chat (Copilot)

**Purpose:** Ask questions about your uploaded documents and get AI-powered answers with source references.

**How to start a chat:**
1. Navigate to **Chat** in the sidebar
2. Click **"New Chat Session"**
3. Give your session a title
4. Select documents to include in the conversation
5. Click **"Create"**

**How to chat:**
1. Type your question in the input box at the bottom
2. Press Enter or click Send
3. The AI will search through your documents and provide an answer
4. Sources are shown below the answer (click to see the original text)

**Example questions:**
- "What was the revenue last quarter?"
- "Summarize the key risks mentioned in the reports"
- "What are the main products or services?"
- "Are there any legal issues mentioned?"

**Chat tips:**
- Be specific with your questions for better answers
- Reference specific time periods or document types when relevant
- Use follow-up questions to drill deeper into topics

---

### Feature 4: QuickBooks Integration

**Purpose:** Connect to QuickBooks Online to automatically import financial data for analysis.

**How to connect QuickBooks:**
1. Navigate to **Connectors** in the sidebar
2. Select a company
3. Click **"Connect QuickBooks"**
4. You'll be redirected to QuickBooks login
5. Sign in to your QuickBooks account
6. Authorize the connection
7. You'll be redirected back to BDE

**How to sync data:**
1. Go to **Connectors**
2. Find your connected QuickBooks account
3. Click **"Sync"**
4. Select which entities to sync (Invoices, Customers, Vendors, etc.)
5. Click **"Start Sync"**
6. Wait for sync to complete (progress shown in real-time)

**How to process synced data:**
1. After sync completes, click **"Ingest"**
2. Select entity types to process
3. Data will be chunked and made available for chat and scoring

**Viewing connector stats:**
- See total records synced
- View chunks created from QuickBooks data
- Check last sync status and date

---

### Feature 5: BDE Scoring & Analysis

**Purpose:** Generate comprehensive scoring across Business, Development, and Environmental pillars.

**How to run analysis:**
1. Ensure you have uploaded documents for the company
2. Navigate to **Analysis** in the sidebar
3. Select the company to analyze
4. Click **"Run Analysis"**
5. Watch the progress as scoring runs through each pillar

**Understanding the scores:**

**Overall BDE Score:**
- Combined score from all three pillars
- Weighted based on pillar importance
- Includes confidence level (High, Medium, Low)

**Pillar Scores:**

| Pillar | What It Measures |
|--------|-----------------|
| **Business** | Revenue, profitability, customer base, market position |
| **Development** | Technology, IP, team capabilities, scalability |
| **Environmental** | Compliance, sustainability, regulatory risks |

**Score breakdown:**
- **Score (0-100):** Overall pillar health
- **Health Status:** Healthy, Moderate, or At Risk
- **Key Findings:** Important discoveries from documents
- **Risks:** Identified concerns
- **Data Gaps:** Missing information for complete assessment

**Viewing detailed results:**
1. Click on any pillar to see detailed breakdown
2. View supporting evidence from documents
3. See extracted metrics with source references

**Flags:**
- **Red Flags:** Serious concerns requiring attention
- **Yellow Flags:** Moderate concerns to monitor
- **Green Accelerants:** Positive factors that add value

**Recommendations:**
- Overall acquisition recommendation (Proceed, Caution, Pass)
- Suggested valuation adjustments
- 100-day plan items

**Re-running analysis:**
- If you upload new documents, you'll see "New Documents Available"
- Click "Re-run Analysis" to incorporate new data
- Previous scores are retained for comparison

---

### Feature 6: Prompt Customization

**Purpose:** Customize how the AI responds in chat sessions.

**How to customize prompts:**
1. Navigate to **Settings** → **Prompts**
2. View the current active prompt template
3. Click **"Edit"** to modify
4. Update the template text
5. Click **"Save"**

**Reset to default:**
- Click **"Reset to Default"** to restore the original prompt

---

## User Roles & Permissions

### Role Types

| Role | Access Level |
|------|-------------|
| **Super Admin** | Full platform access, manage all tenants |
| **Tenant Admin** | Full access within tenant, manage users |
| **Admin** | Manage companies, documents, run analysis |
| **User** | View access, basic chat functionality |

### What each role can do:

**User:**
- View documents and companies
- Use chat feature
- View analysis results

**Admin:**
- All User permissions
- Upload and delete documents
- Create and manage companies
- Run BDE analysis
- Connect and manage connectors

**Tenant Admin:**
- All Admin permissions
- Manage users within the tenant
- Assign roles to users

---

## Troubleshooting

### Common Issues

#### "Document processing failed"
**Cause:** The file may be corrupted or in an unsupported format.
**Solution:**
1. Ensure the file opens correctly on your computer
2. Try re-uploading the file
3. If it's a scanned PDF, ensure it has readable text
4. Check file size is under 50MB

#### "No results found" in chat
**Cause:** Your question may not match any content in the documents, or documents aren't processed yet.
**Solution:**
1. Check that documents have "Completed" status
2. Rephrase your question with different keywords
3. Ensure the right documents are selected for the chat session
4. Try a broader question first, then narrow down

#### "Analysis cannot run"
**Cause:** No documents uploaded or documents still processing.
**Solution:**
1. Upload at least one document for the company
2. Wait for all documents to complete processing
3. Check the Analysis Status page for requirements

#### "QuickBooks connection failed"
**Cause:** Authorization was denied or expired.
**Solution:**
1. Try disconnecting and reconnecting
2. Ensure you have admin access to the QuickBooks account
3. Check that popup blockers aren't preventing the OAuth flow

#### "Session expired" or "Unauthorized"
**Cause:** Your login session has expired.
**Solution:**
1. Click "Sign in" to re-authenticate
2. If issues persist, clear browser cookies and try again

---

## Tips & Best Practices

### Document Uploads
- Upload complete, well-organized documents for best results
- Name files descriptively (e.g., "Q4-2024-Financial-Report.pdf")
- Include a variety of document types for comprehensive analysis
- Upload financial statements, contracts, org charts, and strategic plans

### Using Chat Effectively
- Start with broad questions, then get more specific
- Ask about specific metrics: "What was EBITDA in 2024?"
- Request comparisons: "How did revenue change from 2023 to 2024?"
- Ask for summaries: "Summarize the key terms of the customer contracts"

### Getting Better Scores
- Upload documents covering all three pillars (Business, Development, Environmental)
- Include recent financial statements for accurate business scoring
- Provide technology documentation for development scoring
- Include compliance and sustainability reports for environmental scoring
- More documents = more comprehensive analysis

### Managing Multiple Companies
- Create separate companies for each acquisition target
- Keep document organization clean within each company
- Run analysis separately for each to get tailored results

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send chat message |
| `Ctrl + /` | Focus search |
| `Esc` | Close modal/dialog |

---

## Support & Help

For any issues not covered in this manual:
1. Check the in-app help section
2. Contact your system administrator
3. Open a support ticket through your organization's IT helpdesk

---

**Last Updated:** January 2025
