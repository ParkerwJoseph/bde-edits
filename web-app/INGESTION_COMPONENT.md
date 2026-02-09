# BDE Ingestion Component - Implementation Document

## Reference UI Location

```
/home/user/Projects/Docs/BDE UI V2/remix-of-remix-of-business-dashboard-79-main/src/pages/Ingestion.tsx
```

---

## 1. Reference UI Design

The Ingestion page has 3 main sections:

### 1.1 Upload Zone
- Centered upload area with dashed border
- Upload icon in a circular background
- Title: "Upload Documents"
- Description: "Drag and drop files here, or click to browse. Supports PDFs, spreadsheets, and text documents."

### 1.2 Document Coverage
- Grid of document type cards (5 columns on xl, 3 on lg, 2 on md, 1 on mobile)
- Each card shows:
  - Icon
  - Count (number)
  - Label
  - Description

**Document Types:**
| Icon | Label | Description |
|------|-------|-------------|
| FileText | PDF Documents | Board decks, reports, financials |
| Table2 | Spreadsheets | Financial models, data exports |
| Mail | Emails | Communication archives |
| FileAudio | Transcripts | Meeting notes, call transcripts |
| Database | CRM Exports | Pipeline and customer data |

### 1.3 Processing Jobs
- Card with title "Processing Jobs"
- Description: "Track document extraction and analysis status"
- Shows list of processing jobs or empty state

---

## 2. Implementation Structure

```
/pages/Ingestion.tsx
│
├── Uses existing:
│   ├── documentApi.ts (upload, list)
│   ├── useDocumentProgress.ts (WebSocket progress)
│   └── companyApi.ts (company selection)
│
└── Components:
    └── /components/ingestion/
        ├── index.ts
        ├── IngestionUploadZone.tsx    # Drag-drop upload area
        ├── DocumentCoverage.tsx       # Document type counts grid
        └── ProcessingJobs.tsx         # Processing status list
```

---

## 3. Component Specifications

### 3.1 IngestionUploadZone

Same as before - drag and drop area for file upload.

### 3.2 DocumentCoverage (NEW)

**Purpose:** Display counts of different document types

**Props:**
```typescript
interface DocumentCoverageProps {
  companyId: string;
}

interface DocumentTypeCount {
  icon: LucideIcon;
  label: string;
  count: number;
  description: string;
}
```

**Document Types:**
```typescript
const documentTypes = [
  { icon: FileText, label: 'PDF Documents', count: 0, description: 'Board decks, reports, financials' },
  { icon: Table2, label: 'Spreadsheets', count: 0, description: 'Financial models, data exports' },
  { icon: Mail, label: 'Emails', count: 0, description: 'Communication archives' },
  { icon: FileAudio, label: 'Transcripts', count: 0, description: 'Meeting notes, call transcripts' },
  { icon: Database, label: 'CRM Exports', count: 0, description: 'Pipeline and customer data' },
];
```

**Data Source:**
- Use `documentApi.list()` and count by file_type
- Map file_type to document type categories

### 3.3 ProcessingJobs (NEW)

**Purpose:** Show documents being processed and their status

**Props:**
```typescript
interface ProcessingJobsProps {
  jobs: ProcessingJob[];
  isLoading: boolean;
}

interface ProcessingJob {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  step?: number;
  stepName?: string;
  progress?: number;
  error?: string;
  startedAt?: string;
}
```

**Features:**
- List of currently processing documents
- Progress indicator for each
- Empty state: "No processing jobs yet. Upload documents to get started."

---

## 4. Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Ingestion Center                                            │
│ Breadcrumbs: Ingestion                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   UPLOAD ZONE                        │   │
│  │                      (📤)                            │   │
│  │              Upload Documents                        │   │
│  │     Drag and drop files here, or click to browse    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Document Coverage                                          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                   │
│  │ 12  │ │  8  │ │  0  │ │  3  │ │  0  │                   │
│  │ PDF │ │XLSX │ │Email│ │Trans│ │ CRM │                   │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Processing Jobs                                      │   │
│  │ Track document extraction and analysis status        │   │
│  │                                                      │   │
│  │ ┌────────────────────────────────────────────────┐  │   │
│  │ │ 📄 report.pdf    Analyzing...    ████░░░░ 45%  │  │   │
│  │ └────────────────────────────────────────────────┘  │   │
│  │ ┌────────────────────────────────────────────────┐  │   │
│  │ │ 📊 data.xlsx     Pending                       │  │   │
│  │ └────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. File Mapping

Map our file types to document categories:

| File Extension | Document Type |
|---------------|---------------|
| .pdf | PDF Documents |
| .docx, .doc | PDF Documents (treat as documents) |
| .xlsx, .xls | Spreadsheets |
| .pptx, .ppt | PDF Documents (presentations) |
| .mp3, .wav, .m4a, etc. | Transcripts |

---

## 6. Existing Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| POST `/api/documents/upload` | Upload document |
| GET `/api/documents/` | List documents (get counts) |
| WS `/api/documents/ws` | Real-time progress |

---

## 7. Files to Create/Update

**Create:**
- `components/ingestion/DocumentCoverage.tsx`
- `components/ingestion/ProcessingJobs.tsx`
- `styles/components/ingestion/DocumentCoverage.module.css`
- `styles/components/ingestion/ProcessingJobs.module.css`

**Update:**
- `pages/Ingestion.tsx` - Rewrite to match reference
- `components/ingestion/index.ts` - Update exports

**Remove:**
- `components/ingestion/IngestionConnectors.tsx`
- `components/ingestion/IngestionDocuments.tsx`
- `components/ingestion/IngestionFileList.tsx`
- `components/ingestion/IngestionFileItem.tsx`
- Related CSS files

---

## Document Metadata

- **Reference UI:** `/home/user/Projects/Docs/BDE UI V2/remix-of-remix-of-business-dashboard-79-main/src/pages/Ingestion.tsx`
- **Created:** 2026-01-27
- **Updated:** 2026-01-27
- **Version:** 2.0
