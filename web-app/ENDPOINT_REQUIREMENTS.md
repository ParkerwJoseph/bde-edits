# BDE Web App - Endpoint Requirements Document

## Executive Summary

This document provides a comprehensive review of:
1. All existing backend API endpoints
2. All frontend components and their data requirements
3. Hardcoded/static data that needs to be replaced with real API calls
4. Missing endpoints that need to be implemented
5. Action plan for removing static data

---

## 1. Existing Backend Endpoints

### Authentication (`/api/auth/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/auth/login` | Implemented | Azure OAuth redirect |
| POST | `/api/auth/logout` | Implemented | Logout user |
| GET | `/api/auth/me` | Implemented | Get current user |

### Scoring (`/api/scoring/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/api/scoring/companies/{id}/score` | Implemented | Trigger scoring pipeline |
| GET | `/api/scoring/companies/{id}/bde-score` | Implemented | Get overall BDE score + pillar scores |
| GET | `/api/scoring/companies/{id}/pillars/{pillar}` | Implemented | Get detailed pillar info |
| GET | `/api/scoring/companies/{id}/metrics` | Implemented | Get all extracted metrics |
| GET | `/api/scoring/companies/{id}/flags` | Implemented | Get red/yellow/green flags |
| GET | `/api/scoring/companies/{id}/recommendation` | Implemented | Get acquisition recommendation |
| GET | `/api/scoring/companies/{id}/data-sources` | Implemented | Get source documents |
| GET | `/api/scoring/companies/{id}/metrics-with-sources` | Implemented | Get metrics with source lineage |
| GET | `/api/scoring/companies/{id}/analysis-status` | Implemented | Get analysis status |
| GET | `/api/scoring/companies/{id}/document-count` | Implemented | Get document count |
| WS | `/api/scoring/ws` | Implemented | WebSocket for scoring progress |

### Companies (`/api/companies/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/api/companies` | Implemented | Create company |
| GET | `/api/companies` | Implemented | List companies |
| GET | `/api/companies/{id}` | Implemented | Get company details |
| PATCH | `/api/companies/{id}` | Implemented | Update company |
| DELETE | `/api/companies/{id}` | Implemented | Delete company |

### Documents (`/api/documents/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/api/documents/upload` | Implemented | Upload document |
| GET | `/api/documents/` | Implemented | List documents |
| GET | `/api/documents/{id}` | Implemented | Get document with chunks |
| GET | `/api/documents/{id}/status` | Implemented | Get processing status |
| GET | `/api/documents/{id}/chunks` | Implemented | Get document chunks |
| GET | `/api/documents/{id}/download` | Implemented | Get download URL |
| DELETE | `/api/documents/{id}` | Implemented | Delete document |
| WS | `/api/documents/ws` | Implemented | WebSocket for upload progress |

### Users (`/api/users/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/users` | Implemented | List users |
| GET | `/api/users/{id}` | Implemented | Get user |
| PUT | `/api/users/{id}/role` | Implemented | Update user role |
| PUT | `/api/users/{id}/status` | Implemented | Update user status |
| DELETE | `/api/users/{id}` | Implemented | Delete user |

### Tenants (`/api/tenants/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/tenants` | Implemented | List tenants |
| GET | `/api/tenants/{id}` | Implemented | Get tenant |
| POST | `/api/tenants` | Implemented | Create tenant |
| PUT | `/api/tenants/{id}` | Implemented | Update tenant |
| DELETE | `/api/tenants/{id}` | Implemented | Delete tenant |
| POST | `/api/tenants/{id}/onboarding` | Implemented | Send onboarding invite |

### QuickBooks Connector (`/api/connectors/quickbooks/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/connectors/quickbooks/info` | Implemented | Get connector info |
| GET | `/api/connectors/quickbooks/` | Implemented | List connectors |
| GET | `/api/connectors/quickbooks/{id}` | Implemented | Get connector |
| PATCH | `/api/connectors/quickbooks/{id}` | Implemented | Update connector |
| DELETE | `/api/connectors/quickbooks/{id}` | Implemented | Delete connector |
| POST | `/api/connectors/quickbooks/oauth/start` | Implemented | Start OAuth flow |
| GET | `/api/connectors/quickbooks/{id}/entities` | Implemented | Get available entities |
| POST | `/api/connectors/quickbooks/{id}/sync` | Implemented | Trigger sync |
| GET | `/api/connectors/quickbooks/{id}/sync/{logId}` | Implemented | Get sync log |
| GET | `/api/connectors/quickbooks/{id}/sync-logs` | Implemented | List sync logs |
| POST | `/api/connectors/quickbooks/{id}/ingest` | Implemented | Ingest synced data |
| GET | `/api/connectors/quickbooks/{id}/stats` | Implemented | Get connector stats |

### Chat/Copilot (`/api/chat/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/api/chat/chat` | Implemented | Send chat message |
| POST | `/api/chat/search` | Implemented | RAG search |
| GET | `/api/chat/sessions` | Implemented | List sessions |
| POST | `/api/chat/sessions` | Implemented | Create session |
| GET/PATCH/DELETE | `/api/chat/sessions/{id}` | Implemented | Session CRUD |
| WS | `/api/chat/ws` | Implemented | WebSocket for streaming |

### Prompts (`/api/prompts/`)
| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/prompts` | Implemented | Get prompts |
| PUT | `/api/prompts` | Implemented | Update prompts |
| POST | `/api/prompts/reset` | Implemented | Reset to defaults |
| GET | `/api/prompts/default` | Implemented | Get default prompts |

---

## 2. Hardcoded Data in Frontend Components

### CRITICAL - Components with 100% Hardcoded Data

#### 2.1 `AnalyticsPillarDetail.tsx` (Lines 54-216)
**Location:** `frontend/src/pages/AnalyticsPillarDetail.tsx`
**Issue:** Complete hardcoded data for all 8 pillars

```typescript
const PILLAR_DATA: Record<string, PillarConfig> = {
  financial_health: {
    score: 82, change: 5,
    metrics: [
      { name: 'ARR', value: '$1.7M', change: 24, trend: 'up' },
      { name: 'MRR', value: '$142K', change: 8, trend: 'up' },
      // ... more hardcoded
    ],
    insights: [
      { type: 'positive', text: 'Strong ARR growth outpacing industry benchmarks' },
      // ... more hardcoded
    ]
  },
  // ... 7 more pillars with hardcoded data
}
```

**Required API:** `GET /api/scoring/companies/{id}/pillars/{pillar}` (exists but needs enhancement)

**Data Missing from API Response:**
- `metrics[]` with name, value, change, trend
- `insights[]` with type (positive/warning/critical) and text
- `change` (score change from previous period)
- Score breakdown: data_coverage, metric_quality, trend_stability, benchmark_comparison

---

### HIGH PRIORITY - Components with Default/Mock Data

#### 2.2 `MultipleImprovers.tsx` (Lines 39-64)
**Location:** `frontend/src/components/home/MultipleImprovers.tsx`

```typescript
const DEFAULT_IMPROVERS: MultipleImprover[] = [
  {
    id: '1',
    action: 'Diversify top 5 customers',
    impactLabel: '+0.5x',
    progress: { current: 1, total: 3 },
    status: 'critical',
    categories: { impact: 'high', effort: 'medium', priority: 1 },
  },
  // ... more
];
```

**Required NEW Endpoint:**
```
GET /api/scoring/companies/{id}/improvers
Response: {
  improvers: [
    {
      id: string,
      action: string,
      impactLabel: string,      // e.g., "+0.5x"
      progress: { current: number, total: number },
      status: 'critical' | 'warning' | 'good',
      categories: {
        impact: 'high' | 'medium' | 'low',
        effort: 'high' | 'medium' | 'low',
        priority: number
      }
    }
  ]
}
```

---

#### 2.3 `TodaysPriorities.tsx` (Lines 31-56)
**Location:** `frontend/src/components/home/TodaysPriorities.tsx`

```typescript
const DEFAULT_PRIORITIES: Priority[] = [
  {
    id: '1',
    title: 'AR aging >60 days: $42K outstanding',
    category: 'financial',
    urgency: 'critical',
    action: 'Send reminders',
    metric: 'DSO',
  },
  // ... more
];
```

**Required NEW Endpoint:**
```
GET /api/scoring/companies/{id}/priorities
Response: {
  priorities: [
    {
      id: string,
      title: string,
      category: 'financial' | 'customer' | 'gtm' | 'ecosystem',
      urgency: 'critical' | 'warning' | 'info',
      action: string,
      metric?: string
    }
  ]
}
```

---

#### 2.4 `WeeklyChanges.tsx` (Lines 35-69)
**Location:** `frontend/src/components/home/WeeklyChanges.tsx`

```typescript
const DEFAULT_CHANGES: Change[] = [
  {
    id: '1',
    metric: 'Net Revenue Retention',
    acronym: 'NRR',
    previousValue: '108%',
    currentValue: '112%',
    change: 3.7,
    trend: 'up',
    isPositive: true,
    category: 'Customer',
  },
  // ... more
];
```

**Required NEW Endpoint:**
```
GET /api/scoring/companies/{id}/weekly-changes
Response: {
  changes: [
    {
      id: string,
      metric: string,
      acronym?: string,
      previousValue: string,
      currentValue: string,
      change: number,         // percentage
      trend: 'up' | 'down' | 'neutral',
      isPositive: boolean,    // whether trend direction is good
      category: string
    }
  ],
  period: {
    start: string,  // ISO date
    end: string     // ISO date
  }
}
```

---

#### 2.5 `DataCoverageCard.tsx` (Lines 37-42)
**Location:** `frontend/src/components/home/DataCoverageCard.tsx`

```typescript
const DEFAULT_COVERAGE_DATA: CoverageItem[] = [
  { label: 'Financial', icon: DollarSign, coverage: 92, docsCount: 24, lastUpdated: '2 days ago' },
  { label: 'Customer', icon: Users, coverage: 78, docsCount: 18, lastUpdated: '1 week ago' },
  { label: 'Product', icon: Package, coverage: 85, docsCount: 12, lastUpdated: '3 days ago' },
  { label: 'GTM', icon: TrendingUp, coverage: 64, docsCount: 8, lastUpdated: '2 weeks ago' },
];
```

**Required NEW Endpoint:**
```
GET /api/scoring/companies/{id}/data-coverage
Response: {
  coverage: [
    {
      pillar: string,           // 'financial_health', 'customer_health', etc.
      label: string,            // 'Financial', 'Customer', etc.
      coverage: number,         // 0-100 percentage
      docsCount: number,
      lastUpdated: string       // ISO date or relative string
    }
  ],
  overallCoverage: number
}
```

---

#### 2.6 `TopExitRisks.tsx` (Uses DEFAULT_RISKS)
**Location:** `frontend/src/components/home/TopExitRisks.tsx`

Currently receives data from `Home.tsx` which transforms flags, but also has:
```typescript
const DEFAULT_RISKS: Risk[] = [
  { id: '1', title: 'Revenue Concentration', value: '42%', delta: '+2% since Q3', severity: 'critical' },
  // ...
];
```

**Status:** Partially integrated - uses `flags` from API but has fallback hardcoded data

---

#### 2.7 `PillarStrip.tsx` (Uses DEFAULT_PILLARS)
**Location:** `frontend/src/components/home/PillarStrip.tsx`

```typescript
const DEFAULT_PILLARS = [
  { id: 'financial', score: 4.2 },
  { id: 'gtm', score: 3.6 },
  // ...
];
```

**Status:** Partially integrated - receives `pillars` prop from `Home.tsx` which transforms API data

---

#### 2.8 `GrowthForecast.tsx`
**Location:** `frontend/src/components/home/GrowthForecast.tsx`

Contains hardcoded monthly data:
```typescript
const data = [
  { month: 'MAY', growth: 1, fragility: 0 },
  { month: 'JUN', growth: 6, fragility: 2 },
  // ... through JAN forecast
];
```

**Required NEW Endpoint:**
```
GET /api/scoring/companies/{id}/growth-forecast
Response: {
  data: [
    {
      month: string,
      growth: number,
      fragility: number,
      isProjected: boolean
    }
  ],
  summary: string  // e.g., "Growth acceleration driven by 3 accounts."
}
```

---

#### 2.9 `RevenueConcentration.tsx`
**Location:** `frontend/src/components/home/RevenueConcentration.tsx`

```typescript
const CLIENTS = [
  { name: 'Client A', current: 42, growth: 8, atRisk: 5 },
  { name: 'Client B', current: 28, growth: 12, atRisk: 3 },
  // ...
];
```

**Required NEW Endpoint:**
```
GET /api/scoring/companies/{id}/revenue-concentration
Response: {
  clients: [
    {
      id: string,
      name: string,           // Can be anonymized: "Client A", "Client B"
      current: number,        // Current revenue percentage
      growth: number,         // Growth percentage
      atRisk: number          // At-risk percentage
    }
  ],
  totalClients: number,
  topNConcentration: number   // e.g., top 5 = 78%
}
```

---

#### 2.10 `PillarScorecard.tsx`
**Location:** `frontend/src/components/analytics/PillarScorecard.tsx`

```typescript
const DEFAULT_SCORES = {
  financial_health: { score: 84, health_status: 'green', confidence: 85, data_coverage: 90, trend: 'up' },
  gtm_engine: { score: 72, health_status: 'yellow', confidence: 72, data_coverage: 75, trend: 'flat' },
  // ... all 8 pillars
};
```

**Status:** Should use existing `GET /api/scoring/companies/{id}/bde-score` endpoint

---

#### 2.11 `Home.tsx` Fallback Text (Line 128)
**Location:** `frontend/src/pages/Home.tsx`

```typescript
summaryText = 'Revenue quality is strong. Customer concentration and founder-led sales create transition risk that buyers will price into the deal.';
```

**Status:** Falls back to hardcoded text when `recommendation?.rationale` is null

---

## 3. Missing Endpoints Summary

### New Endpoints Needed

| Priority | Endpoint | Purpose |
|----------|----------|---------|
| HIGH | `GET /api/scoring/companies/{id}/improvers` | Multiple improvers data |
| HIGH | `GET /api/scoring/companies/{id}/priorities` | Today's priorities |
| HIGH | `GET /api/scoring/companies/{id}/weekly-changes` | Weekly metric changes |
| HIGH | `GET /api/scoring/companies/{id}/data-coverage` | Data coverage by pillar |
| MEDIUM | `GET /api/scoring/companies/{id}/growth-forecast` | Growth forecast chart data |
| MEDIUM | `GET /api/scoring/companies/{id}/revenue-concentration` | Revenue concentration data |

### Existing Endpoints Needing Enhancement

| Endpoint | Enhancement Needed |
|----------|-------------------|
| `GET /api/scoring/companies/{id}/pillars/{pillar}` | Add `metrics[]`, `insights[]`, `change`, score breakdown |

---

## 4. Data Flow Analysis

### Current Flow (Home Page)
```
User selects Company
    ↓
CompanyContext.selectCompany(id)
    ↓
Home.tsx calls useHomePageData(companyId)
    ↓
Hook fetches in parallel:
  - scoringApi.getBDEScore(companyId)         ✅ REAL DATA
  - scoringApi.getFlags(companyId)            ✅ REAL DATA
  - scoringApi.getRecommendation(companyId)   ✅ REAL DATA
  - scoringApi.getAnalysisStatus(companyId)   ✅ REAL DATA
    ↓
Components receive data:
  - ExitReadinessHero: ✅ Uses real score/recommendation
  - PillarStrip: ✅ Uses real pillar_scores (with fallback)
  - TopExitRisks: ✅ Uses real flags (with fallback)
  - MultipleImprovers: ❌ HARDCODED DEFAULT
  - TodaysPriorities: ❌ HARDCODED DEFAULT
  - WeeklyChanges: ❌ HARDCODED DEFAULT
  - DataCoverageCard: ❌ HARDCODED DEFAULT
```

### Current Flow (Analytics Page)
```
User navigates to Analytics
    ↓
Analytics.tsx calls useBDEScore(companyId)
    ↓
Components receive data:
  - PillarScorecard: ✅ Uses real pillar_scores (with fallback)
  - GrowthForecast: ❌ HARDCODED
  - RevenueConcentration: ❌ HARDCODED
```

### Current Flow (Pillar Detail Page)
```
User clicks pillar → /analytics/pillar/{pillarId}
    ↓
AnalyticsPillarDetail.tsx
    ↓
Data source: ❌ 100% HARDCODED PILLAR_DATA object
    ↓
Does NOT call usePillarDetail() hook
```

---

## 5. Action Plan

### Phase 1: Critical Fixes (Remove Hardcoded Display Data)

#### Step 1.1: Fix AnalyticsPillarDetail.tsx
1. Import and use `usePillarDetail` hook
2. Enhance backend endpoint `/api/scoring/companies/{id}/pillars/{pillar}` to return:
   - `metrics[]` array
   - `insights[]` array
   - `change` (delta from previous period)
3. Show loading/error states
4. Remove `PILLAR_DATA` constant

#### Step 1.2: Create New Endpoints
1. **`GET /api/scoring/companies/{id}/improvers`**
   - Source: Derive from flags, recommendations, and scoring data
   - Returns prioritized list of actions that improve valuation

2. **`GET /api/scoring/companies/{id}/priorities`**
   - Source: Derive from flags, metrics with critical thresholds
   - Returns time-sensitive action items

3. **`GET /api/scoring/companies/{id}/weekly-changes`**
   - Source: Compare current metrics vs 7 days ago
   - Returns metric deltas with trend analysis

4. **`GET /api/scoring/companies/{id}/data-coverage`**
   - Source: Aggregate from documents by pillar
   - Returns coverage percentage per pillar

### Phase 2: Medium Priority (Charts and Visualizations)

#### Step 2.1: Create Remaining Endpoints
1. **`GET /api/scoring/companies/{id}/growth-forecast`**
   - Source: Historical metrics + projections

2. **`GET /api/scoring/companies/{id}/revenue-concentration`**
   - Source: Customer/revenue metrics from documents

### Phase 3: Component Integration

#### Step 3.1: Update Home Page Components
1. Pass data to `MultipleImprovers` from new API
2. Pass data to `TodaysPriorities` from new API
3. Pass data to `WeeklyChanges` from new API
4. Pass data to `DataCoverageCard` from new API

#### Step 3.2: Update Analytics Components
1. Pass data to `GrowthForecast` from new API
2. Pass data to `RevenueConcentration` from new API

### Phase 4: Remove All Fallbacks

1. Remove `DEFAULT_*` constants from all components
2. Replace with proper loading/empty states
3. Show "No data available" when API returns empty

---

## 6. Frontend Component Props Reference

### Components Already Accepting Data Props

| Component | Prop | Type | Currently Used? |
|-----------|------|------|-----------------|
| `MultipleImprovers` | `improvers` | `MultipleImprover[]` | No (uses DEFAULT) |
| `TodaysPriorities` | `priorities` | `Priority[]` | No (uses DEFAULT) |
| `WeeklyChanges` | `changes` | `Change[]` | No (uses DEFAULT) |
| `DataCoverageCard` | `coverageData` | `CoverageItem[]` | No (uses DEFAULT) |
| `TopExitRisks` | `risks` | `Risk[]` | Yes (from flags) |
| `PillarStrip` | `pillars` | `Pillar[]` | Yes (from bde-score) |
| `PillarScorecard` | `scores` | `Record<string, Score>` | Partial |

---

## 7. API Response Format Standards

All new endpoints should follow this format:

```typescript
// Success Response
{
  "data": { ... },      // The actual data
  "meta": {
    "timestamp": "ISO8601",
    "company_id": "string"
  }
}

// Error Response
{
  "error": {
    "code": "string",
    "message": "string",
    "details": { ... }
  }
}
```

---

## 8. Testing Checklist

After implementation, verify:

- [ ] Home page loads without hardcoded data visible
- [ ] Analytics page loads without hardcoded data visible
- [ ] Pillar detail page shows real data from API
- [ ] All components show loading states during fetch
- [ ] All components show empty states when no data
- [ ] No `DEFAULT_*` data appears in production
- [ ] Console shows no API 404 errors
- [ ] Score changes reflect actual data updates

---

## Document Metadata

- **Created:** 2026-01-27
- **Author:** Claude Code Analysis
- **Version:** 1.0
- **Last Updated:** 2026-01-27
