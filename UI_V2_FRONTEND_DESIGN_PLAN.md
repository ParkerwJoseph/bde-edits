# BDE UI V2 Frontend Design Implementation Plan

## Overview

This document outlines the plan to implement the new UI V2 visual design using our **existing tech stack**. The new UI reference (`new-ui-reference/`) serves as a **design guide only** - we will recreate the look and feel using our current React 19, CSS Modules, and Axios-based architecture.

**Important**: No changes to backend, database, or core libraries. This is purely a frontend visual redesign.

---

## 1. Tech Stack

| Layer | Technology | Status |
|-------|------------|--------|
| Framework | React 19.2.0 | **Keep** |
| Styling | CSS Modules | **Keep** |
| HTTP Client | Axios | **Keep** |
| Router | React Router 7.x | **Keep** |
| State | Context API | **Keep** |
| Auth | Azure AD OAuth | **Keep** |
| Icons | lucide-react | **Add** |
| Backend | FastAPI | **Keep** |

### New Dependency to Install:
```bash
npm install lucide-react
```

---

## 2. Design Reference Analysis

### 2.1 Key Visual Components from New UI

The reference UI showcases these key design patterns we need to implement:

#### **Home/Index Page** (`new-ui-reference/src/pages/Index.tsx`)
- Exit Readiness Hero - Large score display with confidence ring
- Pillar Strip - Horizontal row of 8 pillar buttons with scores
- Minimal Chat Bar - Sleek AI query input
- Top Exit Risks - Risk cards with severity indicators
- Multiple Improvers - Value driver cards (what moves the multiple)
- Signal Map - Value vs fragility matrix visualization
- AI Spotlight Alert - AI-suggested dashboard cards
- Dashboard Customizer - Enable/disable cards panel

#### **Owner Dashboard** (`new-ui-reference/src/pages/Dashboard.tsx`)
- Overall Health Summary chip with score, band, confidence
- Cash Watch indicator (runway, DSO)
- Today's Priorities - Alert cards with actions
- 8-Pillar Health Snapshot grid
- Work Tiles (Money In, Customers, Sales, Product/Ops)
- Right Rail (Changes, Tasks, Data Freshness, AI prompts)

#### **Analytics Page** (`new-ui-reference/src/pages/Analytics.tsx`)
- 8-Pillar Scorecard grid (clickable cards)
- Signal Map visualization (expandable)
- Trend Analysis charts (GrowthForecast, RevenueConcentration)
- Customizable/draggable card grid
- Edit mode for layout customization

#### **Scorecard Components** (`new-ui-reference/src/components/scorecard/`)
- Overall Card - Main score with valuation multiples
- Pillar Cards - Individual pillar scores with risks/accelerants
- KPI Strip - Key metrics display
- Header Ribbon - Company info with source coverage

---

## 3. Complete Component Inventory

### 3.1 Home Page Components (`src/components/home/`)

These components are used on the Index (Home) page - the Exit Readiness view:

| Component | Reference File | Description | Priority |
|-----------|---------------|-------------|----------|
| `ExitReadinessHero` | ExitReadinessHero.tsx | Main score with ring gauge, status badge, summary | **HIGH** |
| `ScoreFactors` | ScoreFactors.tsx | Pillar score pills shown in hero | **HIGH** |
| `PillarStrip` | PillarStrip.tsx | Horizontal 8-pillar button strip | **HIGH** |
| `MinimalChatBar` | MinimalChatBar.tsx | Simple AI chat input for dashboard | **HIGH** |
| `TopExitRisks` | TopExitRisks.tsx | Risk list with severity and actions | **HIGH** |
| `MultipleImprovers` | MultipleImprovers.tsx | What moves the valuation multiple | **HIGH** |
| `ValueFragilityMatrix` | ValueFragilityMatrix.tsx | Signal map (value vs fragility) | **MEDIUM** |
| `ExpandableSignalMap` | analytics/ExpandableSignalMap.tsx | Expandable version of signal map | **MEDIUM** |
| `ImmersiveChat` | ImmersiveChat.tsx | Full-screen chat experience | **MEDIUM** |
| `AiSpotlightAlert` | AiSpotlightAlert.tsx | AI-suggested cards alert | **LOW** |
| `DashboardCustomizer` | DashboardCustomizer.tsx | Card enable/disable panel | **LOW** |
| `HealthSnapshot` | (derived from Dashboard.tsx) | 8-pillar grid with actions | **HIGH** |
| `TodaysPriorities` | TodaysPriorities.tsx | Priority alerts with actions | **HIGH** |
| `WeeklyChanges` | WeeklyChanges.tsx | What changed this week | **MEDIUM** |
| `DataFreshness` | (derived from Dashboard.tsx) | Connector status indicators | **MEDIUM** |
| `GrowthForecast` | GrowthForecast.tsx | Growth trend chart | **LOW** |
| `RevenueConcentration` | RevenueConcentration.tsx | Revenue breakdown chart | **LOW** |
| `RevenueChart` | RevenueChart.tsx | Revenue vs target chart | **LOW** |
| `CustomerHealthGrid` | CustomerHealthGrid.tsx | Customer metrics grid | **LOW** |
| `RiskRadar` | RiskRadar.tsx | Risk across pillars | **LOW** |
| `WinLossChart` | WinLossChart.tsx | Win/loss analysis | **LOW** |

### 3.2 Analytics Components (`src/components/analytics/`)

| Component | Reference File | Description | Priority |
|-----------|---------------|-------------|----------|
| `AnalyticsCardRegistry` | analytics/AnalyticsCardRegistry.tsx | Card configs, renderers, helpers | **HIGH** |
| `AnalyticsCustomizer` | analytics/AnalyticsCustomizer.tsx | Sheet panel to toggle cards on/off | **HIGH** |
| `DraggableCard` | analytics/DraggableCard.tsx | Drag-and-drop card wrapper | **HIGH** |
| `ExpandableSignalMap` | analytics/ExpandableSignalMap.tsx | Expandable signal visualization | **MEDIUM** |
| `KPICard` | (in AnalyticsCardRegistry.tsx) | Small KPI metric card | **HIGH** |
| `GaugeCard` | (in AnalyticsCardRegistry.tsx) | Circular gauge visualization | **HIGH** |
| `ChartCard` | (in AnalyticsCardRegistry.tsx) | Sparkline bar chart | **MEDIUM** |
| `ComparisonCard` | (in AnalyticsCardRegistry.tsx) | Side-by-side comparison bars | **MEDIUM** |
| `HeatmapCard` | (in AnalyticsCardRegistry.tsx) | Grid intensity visualization | **LOW** |
| `TableCard` | (in AnalyticsCardRegistry.tsx) | List with status indicators | **MEDIUM** |

### 3.3 Common/UI Components (`src/components/common/`)

| Component | Reference File | Description | Priority |
|-----------|---------------|-------------|----------|
| `Tooltip` | ui/tooltip.tsx | Hover tooltip with content | **HIGH** |
| `ConfidenceMeter` | ui/confidence-meter.tsx | Confidence bar with % | **HIGH** |
| `KpiCard` | ui/kpi-card.tsx | KPI display with delta | **HIGH** |
| `Badge` | ui/badge.tsx | Score/status badges | **HIGH** |
| `Card` | ui/card.tsx | Card container variants | **HIGH** |
| `Button` | ui/button.tsx | Button variants | **HIGH** |
| `Sheet` | ui/sheet.tsx | Slide-out panel from edge | **HIGH** |
| `Switch` | ui/switch.tsx | Toggle on/off switch | **HIGH** |
| `ScrollArea` | ui/scroll-area.tsx | Custom scrollable area | **MEDIUM** |
| `Separator` | ui/separator.tsx | Divider line | **LOW** |
| `Popover` | ui/popover.tsx | Popover for dropdowns | **MEDIUM** |

### 3.4 Scorecard Components (`src/components/scorecard/`)

These components are used on the CompanyScorecard page:

| Component | Reference File | Description | Priority |
|-----------|---------------|-------------|----------|
| `HeaderRibbon` | scorecard/HeaderRibbon.tsx | Company header with period, last run, source coverage | **HIGH** |
| `OverallCard` | scorecard/OverallCard.tsx | Overall score display with valuation multiples | **HIGH** |
| `PillarCard` | scorecard/PillarCard.tsx | Individual pillar card with risks/accelerants | **HIGH** |
| `PillarGrid` | scorecard/PillarGrid.tsx | 8-pillar grid layout | **HIGH** |
| `KpiStrip` | scorecard/KpiStrip.tsx | Key metrics strip with sparklines | **MEDIUM** |
| `KpiChart` | scorecard/KpiChart.tsx | KPI sparkline chart | **MEDIUM** |
| `ActionsBar` | scorecard/ActionsBar.tsx | Run analysis, export, create follow-ups | **MEDIUM** |
| `RemediationSidebar` | scorecard/RemediationSidebar.tsx | Recommendations sidebar | **LOW** |

### 3.5 Layout Components (`src/components/layout/`)

| Component | Reference File | Description | Priority |
|-----------|---------------|-------------|----------|
| `AppLayout` | layout/AppLayout.tsx | Main layout wrapper | **HIGH** |
| `AppSidebar` | layout/AppSidebar.tsx | Navigation sidebar | **HIGH** |
| `CompanySelector` | (in AppSidebar.tsx) | Company dropdown selector | **HIGH** |
| `HeaderBell` | (in AppLayout.tsx) | Notification bell icon | **MEDIUM** |

### 3.6 Complete UI Components Inventory (`src/components/ui/`)

The reference UI has **58 UI primitive components**. Below is the full inventory with implementation status and phase mapping:

#### 3.6.1 Core UI Components (Phase 2 - COMPLETED)

| Component | Reference File | Description | Status | Notes |
|-----------|---------------|-------------|--------|-------|
| `Tooltip` | ui/tooltip.tsx | Hover tooltip | ✅ Done | Created in Phase 2 |
| `Badge` | ui/badge.tsx | Status/score badges | ✅ Done | Created in Phase 2 |
| `Button` | ui/button.tsx | Button variants | ✅ Done | Created in Phase 2 |
| `Card` | ui/card.tsx | Card container | ✅ Done | Created in Phase 2 |
| `ConfidenceMeter` | ui/confidence-meter.tsx | Confidence bar | ✅ Done | Created in Phase 2 |
| `KpiCard` | ui/kpi-card.tsx | KPI metric display | ✅ Done | Created in Phase 2 |

#### 3.6.2 Layout & Navigation Components (Phase 3)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `Sheet` | ui/sheet.tsx | Slide-out panel | 🔲 Pending | Phase 3 |
| `Sidebar` | ui/sidebar.tsx | Main navigation | 🔲 Pending | Phase 3 |
| `ScrollArea` | ui/scroll-area.tsx | Custom scrollable | 🔲 Pending | Phase 3 |
| `Separator` | ui/separator.tsx | Divider line | 🔲 Pending | Phase 3 |
| `Breadcrumb` | ui/breadcrumb.tsx | Navigation breadcrumbs | 🔲 Pending | Phase 3 |
| `NavigationMenu` | ui/navigation-menu.tsx | Nav menu component | ⏭️ Skip | Use existing sidebar |

#### 3.6.3 Form Components (Phase 4 - As Needed)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `Input` | ui/input.tsx | Text input | 🔲 Pending | Phase 4 |
| `Textarea` | ui/textarea.tsx | Multi-line input | 🔲 Pending | Phase 4 |
| `Select` | ui/select.tsx | Dropdown select | 🔲 Pending | Phase 4 |
| `Checkbox` | ui/checkbox.tsx | Checkbox input | 🔲 Pending | Phase 4 |
| `RadioGroup` | ui/radio-group.tsx | Radio buttons | 🔲 Pending | As needed |
| `Switch` | ui/switch.tsx | Toggle switch | 🔲 Pending | Phase 3 (Analytics) |
| `Slider` | ui/slider.tsx | Range slider | ⏭️ Skip | Not needed |
| `Label` | ui/label.tsx | Form label | 🔲 Pending | Phase 4 |
| `Form` | ui/form.tsx | Form wrapper | ⏭️ Skip | Use native forms |
| `Calendar` | ui/calendar.tsx | Date picker | ⏭️ Skip | Not needed initially |
| `InputOTP` | ui/input-otp.tsx | OTP input | ⏭️ Skip | Not needed |

#### 3.6.4 Feedback Components (Phase 4-5)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `Alert` | ui/alert.tsx | Alert message | 🔲 Pending | Phase 5 |
| `AlertDialog` | ui/alert-dialog.tsx | Confirmation dialog | 🔲 Pending | Phase 5 |
| `Dialog` | ui/dialog.tsx | Modal dialog | 🔲 Pending | Phase 4 |
| `Toast` | ui/toast.tsx | Toast notification | 🔲 Pending | Phase 5 |
| `Toaster` | ui/toaster.tsx | Toast container | 🔲 Pending | Phase 5 |
| `Popover` | ui/popover.tsx | Popover dropdown | 🔲 Pending | Phase 4 |
| `HoverCard` | ui/hover-card.tsx | Hover content card | ⏭️ Skip | Use Tooltip |
| `Sonner` | ui/sonner.tsx | Toast library | ⏭️ Skip | Use our Toast |

#### 3.6.5 Data Display Components (Phase 5-6)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `Table` | ui/table.tsx | Data table | 🔲 Pending | Phase 5 |
| `Tabs` | ui/tabs.tsx | Tab navigation | 🔲 Pending | Phase 5 |
| `Accordion` | ui/accordion.tsx | Collapsible sections | 🔲 Pending | Phase 6 |
| `Collapsible` | ui/collapsible.tsx | Collapsible content | 🔲 Pending | Phase 6 |
| `Progress` | ui/progress.tsx | Progress bar | 🔲 Pending | Phase 5 |
| `Skeleton` | ui/skeleton.tsx | Loading placeholder | 🔲 Pending | Phase 4 |
| `Avatar` | ui/avatar.tsx | User avatar | 🔲 Pending | Phase 3 |
| `AspectRatio` | ui/aspect-ratio.tsx | Aspect ratio box | ⏭️ Skip | Use CSS |

#### 3.6.6 Menu Components (As Needed)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `DropdownMenu` | ui/dropdown-menu.tsx | Dropdown menu | 🔲 Pending | Phase 4 |
| `ContextMenu` | ui/context-menu.tsx | Right-click menu | ⏭️ Skip | Not needed |
| `Menubar` | ui/menubar.tsx | Menu bar | ⏭️ Skip | Not needed |
| `Command` | ui/command.tsx | Command palette | ⏭️ Skip | Not needed |

#### 3.6.7 Advanced Components (Phase 6+)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `Chart` | ui/chart.tsx | Chart wrapper | 🔲 Pending | Phase 6 |
| `Carousel` | ui/carousel.tsx | Image carousel | ⏭️ Skip | Not needed |
| `Drawer` | ui/drawer.tsx | Bottom drawer | ⏭️ Skip | Use Sheet |
| `Resizable` | ui/resizable.tsx | Resizable panels | ⏭️ Skip | Not needed |
| `Pagination` | ui/pagination.tsx | Page navigation | 🔲 Pending | Phase 5 |
| `ToggleGroup` | ui/toggle-group.tsx | Toggle button group | 🔲 Pending | Phase 6 |
| `Toggle` | ui/toggle.tsx | Toggle button | 🔲 Pending | Phase 6 |

#### 3.6.8 Domain-Specific Components (Various Phases)

| Component | Reference File | Description | Status | Phase |
|-----------|---------------|-------------|--------|-------|
| `RiskList` | ui/risk-list.tsx | Risk items display | 🔲 Pending | Phase 4 (Home) |
| `WeightingBar` | ui/weighting-bar.tsx | Weight visualization | 🔲 Pending | Phase 6 |
| `SegmentFilter` | ui/segment-filter.tsx | Segment filter UI | 🔲 Pending | Phase 6 |
| `AlertsStrip` | ui/alerts-strip.tsx | Alert banner strip | 🔲 Pending | Phase 5 |
| `AcronymTooltip` | ui/acronym-tooltip.tsx | Acronym definitions | 🔲 Pending | Phase 4 |
| `DefinitionPopover` | ui/definition-popover.tsx | Term definitions | 🔲 Pending | Phase 6 |
| `CardTitleBadge` | ui/card-title-badge.tsx | Card header badge | 🔲 Pending | Phase 4 |

#### 3.6.9 UI Component Summary

| Category | Total | To Build | Skip | Done |
|----------|-------|----------|------|------|
| Core UI | 6 | 0 | 0 | 6 |
| Layout & Nav | 6 | 5 | 1 | 0 |
| Forms | 11 | 5 | 6 | 0 |
| Feedback | 8 | 5 | 3 | 0 |
| Data Display | 8 | 7 | 1 | 0 |
| Menus | 4 | 1 | 3 | 0 |
| Advanced | 7 | 4 | 3 | 0 |
| Domain-Specific | 7 | 7 | 0 | 0 |
| **Total** | **57** | **34** | **17** | **6** |

**Key Decisions:**
- **Skip 17 components**: Not needed for our use case or have simpler alternatives
- **Build 34 components**: Essential for the UI design (will be built as needed per phase)
- **6 already done**: Core components from Phase 2

### 3.7 Copilot Components (`src/components/copilot/`)

| Component | Reference File | Description | Priority |
|-----------|---------------|-------------|----------|
| `MinimalChatBar` | home/MinimalChatBar.tsx | Dashboard chat input | **HIGH** |
| `ImmersiveChat` | home/ImmersiveChat.tsx | Full-screen chat | **MEDIUM** |
| `ChatMessage` | (in ImmersiveChat.tsx) | Message with citations | **MEDIUM** |
| `QuickPrompts` | (in Copilot.tsx) | Suggested prompt buttons | **MEDIUM** |
| `CitationPanel` | (in Copilot.tsx) | Source documents panel | **MEDIUM** |

### 3.9 Hooks (`src/hooks/`)

| Hook | Reference File | Description | Priority |
|------|---------------|-------------|----------|
| `useAnalyticsLayout` | hooks/useAnalyticsLayout.ts | Analytics card state + localStorage persistence | **HIGH** |
| `useScorecard` | hooks/useScorecard.ts | Fetches scorecard data for a company | **HIGH** |
| `useKpiHistory` | hooks/useKpiHistory.ts | Fetches KPI history data | **MEDIUM** |
| `useAuth` | hooks/useAuth.tsx | Authentication state and methods | **HIGH** |
| `use-toast` | hooks/use-toast.ts | Toast notification hook | **MEDIUM** |
| `use-mobile` | hooks/use-mobile.tsx | Mobile device detection | **LOW** |

---

## 4. Pages Implementation Plan

### 4.1 Reference UI Pages Structure

The reference UI has the following page structure that we will implement:

| Route | Reference File | Description | Priority |
|-------|---------------|-------------|----------|
| `/` | `pages/Index.tsx` | **Home** - Exit Readiness Hero, Pillar Strip, Chat Bar, Top Risks, Signal Map, Multiple Improvers | **HIGH** |
| `/dashboard` | `pages/Dashboard.tsx` | **Owner Dashboard** - Health summary, Today's Priorities, 8-pillar snapshot, Work Tiles, Right Rail | **HIGH** |
| `/analytics` | `pages/Analytics.tsx` | **Analytics** - 8-pillar scorecard grid, Signal Map, Trend Analysis, Customizable cards grid | **HIGH** |
| `/analytics/pillar/:pillarId` | `pages/AnalyticsPillarDetail.tsx` | **Pillar Analytics** - Deep-dive into specific pillar analytics | **MEDIUM** |
| `/companies/:id` | `pages/CompanyScorecard.tsx` | **Company Scorecard** - Header ribbon, Overall card, Pillar grid, KPI strip, Actions bar | **HIGH** |
| `/companies/:id/pillar/:pillarId` | `pages/PillarDetail.tsx` | **Pillar Detail** - Detailed pillar view for a company | **HIGH** |
| `/copilot` | `pages/Copilot.tsx` | **AI Analyst** - Chat interface with quick prompts, citations, source documents panel | **MEDIUM** |
| `/ingestion` | `pages/Ingestion.tsx` | **Data Ingestion** - Upload files, manage connectors | **MEDIUM** |
| `/notifications` | `pages/Notifications.tsx` | **Notifications** - Alerts and priority actions | **LOW** |
| `/reports` | `pages/Reports.tsx` | **Reports** - PDF export and report generation | **LOW** |
| `/settings` | `pages/Settings.tsx` | **Settings** - User and app settings | **LOW** |
| `/metrics/:metricId` | `pages/MetricDetail.tsx` | **Metric Detail** - Deep-dive into specific metric | **LOW** |
| `/signals/:signalId` | `pages/SignalDetail.tsx` | **Signal Detail** - Deep-dive into specific signal | **LOW** |
| `/auth` | `pages/Auth.tsx` | **Login** - Authentication page | **HIGH** |

### 4.2 Pages to Keep As-Is (Admin)

These admin pages exist in our current codebase and don't need redesign:

- Tenants (`/tenants`) - admin
- Users (`/users`) - admin
- PromptManagement (`/prompts`) - admin
- Onboarding (`/onboarding/:code`)
- Forbidden (`/forbidden`)

### 4.3 Route Configuration (from App.tsx)

```typescript
// Reference: new-ui-reference/src/App.tsx
<Routes>
  <Route path="/auth" element={<Auth />} />
  <Route path="/" element={<ProtectedRoute><Index /></ProtectedRoute>} />
  <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
  <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
  <Route path="/analytics/pillar/:pillarId" element={<ProtectedRoute><AnalyticsPillarDetail /></ProtectedRoute>} />
  <Route path="/companies/:id" element={<ProtectedRoute><CompanyScorecard /></ProtectedRoute>} />
  <Route path="/companies/:id/pillar/:pillarId" element={<ProtectedRoute><PillarDetail /></ProtectedRoute>} />
  <Route path="/ingestion" element={<ProtectedRoute><Ingestion /></ProtectedRoute>} />
  <Route path="/copilot" element={<ProtectedRoute><Copilot /></ProtectedRoute>} />
  <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
  <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
  <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
  <Route path="/metrics/:metricId" element={<ProtectedRoute><MetricDetail /></ProtectedRoute>} />
  <Route path="/signals/:signalId" element={<ProtectedRoute><SignalDetail /></ProtectedRoute>} />
  <Route path="*" element={<NotFound />} />
</Routes>
```

### 4.4 Navigation Structure

```typescript
// Based on reference UI sidebar
export const NAV_ITEMS = [
  { id: 'home', label: 'Home', path: '/', icon: LayoutDashboard },
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: BarChart2 },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: BarChart3 },
  { id: 'copilot', label: 'AI Analyst', path: '/copilot', icon: Sparkles },
  { id: 'ingestion', label: 'Ingestion', path: '/ingestion', icon: Upload },
  { id: 'reports', label: 'Reports', path: '/reports', icon: FileText },
  { id: 'notifications', label: 'Notifications', path: '/notifications', icon: Bell },
  { id: 'settings', label: 'Settings', path: '/settings', icon: Settings },
];
```

---

## 5. Component Design Specifications

### 5.1 Exit Readiness Hero Component

**Location**: `src/components/home/ExitReadinessHero.tsx`

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  (top accent line - gradient)           │
│                                                                         │
│  ┌──────────┐   EXIT READINESS ⓘ                                       │
│  │   72     │                                                          │
│  │  ████    │   Revenue quality is strong with 115% NRR. Customer      │
│  │  ring    │   concentration (42% from top client) and founder-led    │
│  └──────────┘   sales create transition risk that buyers will price    │
│   ● Conditional  into the deal.                                        │
│                                                                         │
│                 → View details (on hover)                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [ScoreFactors: pillar pills with scores]                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Props**:
```typescript
interface ExitReadinessHeroProps {
  status?: 'ready' | 'conditional' | 'not-ready';
  headline?: string;
  summary?: string;
  confidenceScore?: number;  // 0-100
  hideScoreFactors?: boolean;
  pillarScores?: PillarScore[];
}
```

**Data Mapping**:
- `overall_score` from `/api/scoring/companies/:id/bde-score`
- `confidence` from same endpoint
- `recommendation` from `/api/scoring/companies/:id/recommendation`
- `pillar_scores` for ScoreFactors

**Ring Gauge Logic**:
```typescript
// Color bands: 10-30 red, 31-70 yellow, 71-99 green
const getScoreConfig = (score: number) => {
  if (score >= 71) return { label: 'Exit Ready', color: '#22c55e' };
  if (score >= 31) return { label: 'Conditional', color: '#f59e0b' };
  return { label: 'Not Ready', color: '#ef4444' };
};
```

---

### 5.2 Pillar Strip Component

**Location**: `src/components/home/PillarStrip.tsx`

**Visual Design**:
```
┌────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┐
│ 💰     │ 🎯     │ 👥     │ 🔧     │ ⚙️     │ 👔     │ 🌐     │ ↔️     │
│ 4.2    │ 3.6    │ 4.5    │ 3.8    │ 2.4    │ 3.2    │ 3.9    │ 4.0    │
│ [green]│[yellow]│ [green]│[yellow]│ [red]  │[yellow]│[yellow]│ [green]│
└────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┘
  (clickable - navigates to /analytics/pillar/:id)
  (tooltip shows pillar name + health status)
```

**Props**:
```typescript
interface PillarStripProps {
  pillarScores: {
    id: string;
    name: string;
    shortName: string;
    score: number;
    healthStatus: 'green' | 'yellow' | 'red';
  }[];
  onPillarClick?: (pillarId: string) => void;
}
```

**Health Status Logic**:
```typescript
// Score 1-5 scale
const getHealthStatus = (score: number): 'green' | 'yellow' | 'red' => {
  if (score >= 3.5) return 'green';
  if (score >= 2.5) return 'yellow';
  return 'red';
};
```

---

### 5.3 Top Exit Risks Component

**Location**: `src/components/home/TopExitRisks.tsx`

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ TOP EXIT RISKS                         Fix Window: 90d  │
├─────────────────────────────────────────────────────────────┤
│ 🔴 Customer concentration at 42%          [View Details →] │
│    Top 3 customers = 65% of ARR                            │
│    └─ Pillar: Customer                                     │
├─────────────────────────────────────────────────────────────┤
│ 🔴 Founder-led sales                      [View Details →] │
│    CEO closes 80% of enterprise deals                      │
│    └─ Pillar: Leadership                                   │
├─────────────────────────────────────────────────────────────┤
│ 🟡 ERP integration dependency             [View Details →] │
│    Single platform accounts for 90% of installs            │
│    └─ Pillar: Ecosystem                                    │
└─────────────────────────────────────────────────────────────┘
```

**Props**:
```typescript
interface TopExitRisksProps {
  risks: {
    id: string;
    type: 'red' | 'yellow';
    title: string;
    description: string;
    pillar: string;
    fixWindow?: string;
  }[];
  maxItems?: number;
}
```

**Data Mapping** from `/api/scoring/companies/:id/flags`:
- `red_flags[]` → Red risk items
- `yellow_flags[]` → Yellow risk items
- `flag.text` → Risk title
- `flag.rationale` → Risk description
- `flag.pillar` → Associated pillar

---

### 5.4 Multiple Improvers Component

**Location**: `src/components/home/MultipleImprovers.tsx`

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ 📈 WHAT MOVES THE MULTIPLE                                  │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌─────────────────────┐           │
│ │ +0.5-1.0× Multiple  │  │ +0.3-0.5× Multiple  │           │
│ │ ─────────────────── │  │ ─────────────────── │           │
│ │ Reduce customer     │  │ Build repeatable    │           │
│ │ concentration       │  │ sales playbook      │           │
│ │ below 25%           │  │                     │           │
│ │                     │  │                     │           │
│ │ [Start Plan →]      │  │ [Start Plan →]      │           │
│ └─────────────────────┘  └─────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

**Data Mapping** from `/api/scoring/companies/:id/recommendation`:
- `value_drivers[]` → Improvement items
- `100_day_plan[]` → Action items

---

### 5.5 Confidence Meter Component

**Location**: `src/components/ui/confidence-meter.tsx`

**Visual Design**:
```
Confidence  ████████░░  78%
            (color based on value: green ≥80, yellow ≥50, red <50)
```

**Props**:
```typescript
interface ConfidenceMeterProps {
  value: number;  // 0-100
  label?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}
```

---

### 5.6 KPI Card Component

**Location**: `src/components/ui/kpi-card.tsx`

**Visual Design**:
```
┌─────────────┐
│ ARR         │  (label)
│ $1.24M      │  (value with unit)
│   ↑ +8%     │  (delta with trend arrow)
└─────────────┘
```

**Props**:
```typescript
interface KpiCardProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: number;  // percentage change
  variant?: 'default' | 'compact';
}
```

---

### 5.7 Work Tiles Component

**Location**: `src/components/home/WorkTile.tsx`

**Visual Design**:
```
┌─────────────────────────────────────┐
│ 💰 Money In / Hygiene               │
├─────────────────────────────────────┤
│ ┌───────┐ ┌───────┐ ┌───────────┐  │
│ │ ARR   │ │Recurr │ │Gross Marg │  │
│ │$1.24M │ │ 72%   │ │   68%     │  │
│ │ ↑ +8% │ │       │ │           │  │
│ └───────┘ └───────┘ └───────────┘  │
├─────────────────────────────────────┤
│ AR Aging: DSO 52d    Top 3: 38%    │
├─────────────────────────────────────┤
│       [📧 Send Reminders]           │
└─────────────────────────────────────┘
```

**Work Tile Types**:
1. Money In / Hygiene (Financial)
2. Customers & Renewals (Customer)
3. Sales & Predictability (GTM)
4. Product & Ops (Product/Operations)


### 5.8 Minimal Chat Bar Component

**Location**: `src/components/copilot/MinimalChatBar.tsx`

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ ✨ Ask about exit readiness, risks, or valuation...    [→] │
└─────────────────────────────────────────────────────────────┘
  (clicking opens ImmersiveChat or navigates to /copilot)
```

**Props**:
```typescript
interface MinimalChatBarProps {
  placeholder?: string;
  onSubmit: (message: string) => void;
}
```

---

### 5.9 Sidebar Component Enhancements

**Location**: `src/components/layout/Sidebar.tsx`

**New Features**:
1. **Company Selector Dropdown** - Switch between companies
2. **Collapsible Mode** - Icon-only when collapsed
3. **BDE Logo** - Logo in header
4. **Active Route Highlight** - Pill/rounded style
5. **User Info in Footer** - Avatar, email, role

**Visual Design (Expanded)**:
```
┌─────────────────────┐
│ 🔷 BDE              │
│                     │
│ ┌─────────────────┐ │
│ │ Acme Corp    ▼  │ │  (company selector)
│ │ SaaS            │ │
│ └─────────────────┘ │
├─────────────────────┤
│ NAVIGATION          │
│                     │
│ ● Home              │  (active - filled pill)
│ ○ Analytics         │
│ ○ AI Analyst        │
│ ○ Ingestion         │
│ ○ Reports           │
│ ○ Settings          │
├─────────────────────┤
│ 👤 user@email.com   │
│    🛡️ Admin          │
│                     │
│ [Sign Out]          │
└─────────────────────┘
```

**Visual Design (Collapsed)**:
```
┌─────┐
│ 🔷  │
├─────┤
│ 🏠  │  (with tooltip on hover)
│ 📊  │
│ ✨  │
│ 📤  │
│ 📄  │
│ ⚙️  │
├─────┤
│ 👤  │
│[→]  │
└─────┘
```

---

## 6. Icons Strategy

### 6.1 Approach: Lucide React

We'll use **lucide-react** - a popular, well-maintained icon library with 500+ icons.

**Installation**:
```bash
npm install lucide-react
```

**Why lucide-react**:
- Same icons used in the reference UI design
- Tree-shakeable (only imports what you use, ~3-5KB impact)
- Full TypeScript support
- Consistent design across all icons
- Well-maintained (30k+ GitHub stars)
- No custom icon maintenance needed

### 6.2 Icons We'll Use

#### Pillar Icons (8 icons)
| Pillar | Icon | Import |
|--------|------|--------|
| Financial Health | DollarSign | `import { DollarSign } from 'lucide-react'` |
| GTM Engine | Target | `import { Target } from 'lucide-react'` |
| Customer Health | Users | `import { Users } from 'lucide-react'` |
| Product/Technical | Wrench | `import { Wrench } from 'lucide-react'` |
| Operations | BarChart3 | `import { BarChart3 } from 'lucide-react'` |
| Leadership | Briefcase | `import { Briefcase } from 'lucide-react'` |
| Ecosystem | Network | `import { Network } from 'lucide-react'` |
| Service to Software | ArrowRightLeft | `import { ArrowRightLeft } from 'lucide-react'` |

#### Navigation Icons (7 icons)
| Nav Item | Icon | Import |
|----------|------|--------|
| Home | LayoutDashboard | `import { LayoutDashboard } from 'lucide-react'` |
| Analytics | BarChart3 | `import { BarChart3 } from 'lucide-react'` |
| AI Analyst | Sparkles | `import { Sparkles } from 'lucide-react'` |
| Ingestion | Upload | `import { Upload } from 'lucide-react'` |
| Reports | FileText | `import { FileText } from 'lucide-react'` |
| Settings | Settings | `import { Settings } from 'lucide-react'` |
| Notifications | Bell | `import { Bell } from 'lucide-react'` |

#### UI/Action Icons
| Purpose | Icons |
|---------|-------|
| Navigation | ChevronRight, ChevronDown, ChevronLeft, ArrowRight |
| Actions | X, Send, RefreshCw, ExternalLink |
| Trends | TrendingUp, TrendingDown, Minus |
| Status | AlertTriangle, AlertCircle, Info, CheckCircle, Clock |
| Features | Mail, Calendar, Zap, Shield, Database, MessageSquare, Wallet |

### 6.3 Pillar Icon Mapping

```typescript
// src/constants/pillars.ts
import {
  DollarSign,
  Target,
  Users,
  Wrench,
  BarChart3,
  Briefcase,
  Network,
  ArrowRightLeft,
  LucideIcon,
} from 'lucide-react';

export const PILLAR_ICONS: Record<string, LucideIcon> = {
  financial_health: DollarSign,
  gtm_engine: Target,
  customer_health: Users,
  product_technical: Wrench,
  operational_maturity: BarChart3,
  leadership_transition: Briefcase,
  ecosystem_dependency: Network,
  service_software_ratio: ArrowRightLeft,
};

// Usage in component:
// const Icon = PILLAR_ICONS[pillarId];
// <Icon size={20} className={styles.icon} />
```

### 6.4 Navigation Icon Mapping

```typescript
// src/constants/navigation.ts
import {
  LayoutDashboard,
  BarChart3,
  Sparkles,
  Upload,
  FileText,
  Settings,
  LucideIcon,
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'home', label: 'Home', path: '/', icon: LayoutDashboard },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: BarChart3 },
  { id: 'copilot', label: 'AI Analyst', path: '/copilot', icon: Sparkles },
  { id: 'ingestion', label: 'Ingestion', path: '/ingestion', icon: Upload },
  { id: 'reports', label: 'Reports', path: '/reports', icon: FileText },
  { id: 'settings', label: 'Settings', path: '/settings', icon: Settings },
];

// Usage in Sidebar:
// {NAV_ITEMS.map(({ id, label, path, icon: Icon }) => (
//   <NavLink to={path}>
//     <Icon size={20} />
//     <span>{label}</span>
//   </NavLink>
// ))}
```

### 6.5 Icon Usage Examples

```tsx
// Import icons directly from lucide-react
import {
  DollarSign,
  TrendingUp,
  AlertTriangle,
  ChevronRight
} from 'lucide-react';

// Basic usage (default size 24px)
<DollarSign />

// With custom size
<DollarSign size={16} />

// With custom color
<TrendingUp color="var(--score-green)" />

// With className for CSS styling
<AlertTriangle className={styles.warningIcon} />

// With stroke width
<ChevronRight size={20} strokeWidth={2.5} />

// Dynamic pillar icon
const Icon = PILLAR_ICONS[pillar.id];
<Icon size={24} color={pillar.color} />
```

### 6.6 Icon Props Reference

All lucide-react icons accept these props:

```typescript
interface IconProps {
  size?: number | string;      // Default: 24
  color?: string;              // Default: 'currentColor'
  strokeWidth?: number;        // Default: 2
  absoluteStrokeWidth?: boolean;
  className?: string;
}
```

---

## 7. Constants & Configuration

### 7.1 Pillars Configuration

**Location**: `src/constants/pillars.ts`

```typescript
// Note: Icons are imported separately in PILLAR_ICONS (see Section 6.6)
// This keeps the config serializable for storage/API use

export const PILLARS = {
  financial_health: {
    id: 'financial_health',
    name: 'Financial Health',
    shortName: 'Financial',
    description: 'Revenue quality, margin structure, cash flow, and controls',
    weight: 0.20,
    order: 1,
    color: '#22c55e',
  },
  gtm_engine: {
    id: 'gtm_engine',
    name: 'Go-to-Market',
    shortName: 'GTM',
    description: 'ICP clarity, pipeline coverage, CRM hygiene, win rates',
    weight: 0.15,
    order: 2,
    color: '#3b82f6',
  },
  customer_health: {
    id: 'customer_health',
    name: 'Customer Success',
    shortName: 'Customer',
    description: 'GRR/NRR, adoption signals, support metrics, churn',
    weight: 0.15,
    order: 3,
    color: '#8b5cf6',
  },
  product_technical: {
    id: 'product_technical',
    name: 'Product & Technology',
    shortName: 'Product',
    description: 'Architecture, APIs, tech debt, security maturity',
    weight: 0.12,
    order: 4,
    color: '#06b6d4',
  },
  operational_maturity: {
    id: 'operational_maturity',
    name: 'Operations',
    shortName: 'Operations',
    description: 'Process maturity, systems, data hygiene, culture',
    weight: 0.10,
    order: 5,
    color: '#f59e0b',
  },
  leadership_transition: {
    id: 'leadership_transition',
    name: 'Leadership & Team',
    shortName: 'Leadership',
    description: 'Founder dependency, bench strength, governance',
    weight: 0.10,
    order: 6,
    color: '#ec4899',
  },
  ecosystem_dependency: {
    id: 'ecosystem_dependency',
    name: 'Ecosystem',
    shortName: 'Ecosystem',
    description: 'ERP alignment, API health, internalization risk',
    weight: 0.10,
    order: 7,
    color: '#f97316',
  },
  service_software_ratio: {
    id: 'service_software_ratio',
    name: 'Service to Software',
    shortName: 'S→SW',
    description: 'Software vs services mix, GM structure, productization',
    weight: 0.08,
    order: 8,
    color: '#84cc16',
  },
} as const;

export type PillarId = keyof typeof PILLARS;
```

### 7.2 Score Thresholds

**Location**: `src/constants/scores.ts`

```typescript
// Score color thresholds (0-5 scale)
export const SCORE_THRESHOLDS = {
  green: { min: 3.5 },   // 3.5-5.0 = Healthy
  yellow: { min: 2.5 },  // 2.5-3.5 = Needs Attention
  red: { max: 2.5 },     // 0-2.5 = At Risk
};

// Confidence color thresholds (0-100 scale)
export const CONFIDENCE_THRESHOLDS = {
  high: { min: 80 },    // 80-100 = High confidence
  medium: { min: 50 },  // 50-80 = Moderate
  low: { max: 50 },     // 0-50 = Low confidence
};

// Valuation bands
export const VALUATION_BANDS = [
  { band: 'Premium', minScore: 4.5, multiples: { low: 8, high: 12 } },
  { band: 'Strong', minScore: 4.0, multiples: { low: 6, high: 8 } },
  { band: 'Average', minScore: 3.0, multiples: { low: 4, high: 6 } },
  { band: 'Below Average', minScore: 2.0, multiples: { low: 2, high: 4 } },
  { band: 'Distressed', minScore: 0, multiples: { low: 0.5, high: 2 } },
];

// Exit readiness status thresholds (0-100 confidence scale)
export const EXIT_READINESS_THRESHOLDS = {
  ready: { min: 71 },       // 71-100 = Exit Ready
  conditional: { min: 31 }, // 31-70 = Conditional
  notReady: { max: 31 },    // 0-30 = Not Ready
};
```

### 7.3 Helper Functions

**Location**: `src/utils/scoreHelpers.ts`

```typescript
import { SCORE_THRESHOLDS, CONFIDENCE_THRESHOLDS, VALUATION_BANDS, EXIT_READINESS_THRESHOLDS } from '../constants/scores';

// Get health status color from score (0-5 scale)
export function getHealthStatus(score: number): 'green' | 'yellow' | 'red' {
  if (score >= SCORE_THRESHOLDS.green.min) return 'green';
  if (score >= SCORE_THRESHOLDS.yellow.min) return 'yellow';
  return 'red';
}

// Get confidence level from percentage
export function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= CONFIDENCE_THRESHOLDS.high.min) return 'high';
  if (confidence >= CONFIDENCE_THRESHOLDS.medium.min) return 'medium';
  return 'low';
}

// Get valuation band from score
export function getValuationBand(score: number) {
  for (const band of VALUATION_BANDS) {
    if (score >= band.minScore) return band;
  }
  return VALUATION_BANDS[VALUATION_BANDS.length - 1];
}

// Get exit readiness status
export function getExitReadinessStatus(confidenceScore: number): 'ready' | 'conditional' | 'not-ready' {
  if (confidenceScore >= EXIT_READINESS_THRESHOLDS.ready.min) return 'ready';
  if (confidenceScore >= EXIT_READINESS_THRESHOLDS.conditional.min) return 'conditional';
  return 'not-ready';
}

// Get score color config for ring gauge
export function getScoreColorConfig(score: number) {
  if (score >= 71) {
    return {
      label: 'Exit Ready',
      color: '#22c55e',
      glowColor: 'rgba(34, 197, 94, 0.3)',
    };
  }
  if (score >= 31) {
    return {
      label: 'Conditional',
      color: '#f59e0b',
      glowColor: 'rgba(245, 158, 11, 0.3)',
    };
  }
  return {
    label: 'Not Ready',
    color: '#ef4444',
    glowColor: 'rgba(239, 68, 68, 0.3)',
  };
}

// Convert 0-100 score to 0-5 scale
export function to5Scale(score100: number): number {
  return (score100 / 100) * 5;
}

// Format metric value with unit
export function formatMetricValue(value: number, unit?: string): string {
  if (unit === '$' || unit === 'USD') {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  }
  if (unit === '%') return `${value}%`;
  if (unit === 'days') return `${value}d`;
  if (unit === 'x') return `${value.toFixed(1)}×`;
  return value.toLocaleString();
}
```

---

## 8. CSS Design System

### 8.1 Color Palette

```css
/* src/index.css - CSS Variables */

:root {
  /* Score Colors */
  --score-green: #22c55e;
  --score-green-bg: rgba(34, 197, 94, 0.1);
  --score-green-border: rgba(34, 197, 94, 0.3);

  --score-yellow: #f59e0b;
  --score-yellow-bg: rgba(245, 158, 11, 0.1);
  --score-yellow-border: rgba(245, 158, 11, 0.3);

  --score-red: #ef4444;
  --score-red-bg: rgba(239, 68, 68, 0.1);
  --score-red-border: rgba(239, 68, 68, 0.3);

  /* KPI Colors (alias for semantic use) */
  --kpi-strong: var(--score-green);
  --kpi-watch: var(--score-yellow);
  --kpi-at-risk: var(--score-red);

  /* Chart Colors */
  --chart-1: #3b82f6;
  --chart-2: #8b5cf6;
  --chart-3: #06b6d4;
  --chart-4: #f97316;
  --chart-5: #ec4899;

  /* Background */
  --bg-background: #ffffff;
  --bg-card: #ffffff;
  --bg-card-elevated: #ffffff;
  --bg-muted: #f4f4f5;
  --bg-accent: #f4f4f5;

  /* Foreground/Text */
  --text-foreground: #09090b;
  --text-primary: #09090b;
  --text-secondary: #71717a;
  --text-muted: #a1a1aa;

  /* Border */
  --border-default: #e4e4e7;
  --border-muted: #f4f4f5;

  /* Primary (for buttons, links) */
  --primary: #18181b;
  --primary-foreground: #fafafa;

  /* Sidebar */
  --sidebar-bg: #fafafa;
  --sidebar-border: #e4e4e7;
  --sidebar-foreground: #09090b;
  --sidebar-accent: #f4f4f5;
}

/* Dark mode */
[data-theme="dark"] {
  --bg-background: #09090b;
  --bg-card: #18181b;
  --bg-card-elevated: #27272a;
  --bg-muted: #27272a;
  --bg-accent: #27272a;

  --text-foreground: #fafafa;
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;

  --border-default: #3f3f46;
  --border-muted: #27272a;

  --primary: #fafafa;
  --primary-foreground: #18181b;

  --sidebar-bg: #18181b;
  --sidebar-border: #27272a;
  --sidebar-foreground: #fafafa;
  --sidebar-accent: #27272a;
}
```

### 8.2 Animation Classes

```css
/* src/styles/animations.css */

/* Fade in */
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

/* Staggered fade in */
.animate-fade-in-delayed-1 { animation: fadeIn 0.3s ease-out 0.1s both; }
.animate-fade-in-delayed-2 { animation: fadeIn 0.3s ease-out 0.2s both; }
.animate-fade-in-delayed-3 { animation: fadeIn 0.3s ease-out 0.3s both; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Ring draw animation (for score gauge) */
.animate-ring-draw {
  animation: ringDraw 0.6s ease-out forwards;
}

@keyframes ringDraw {
  from { stroke-dashoffset: var(--ring-circumference); }
  to { stroke-dashoffset: var(--ring-offset); }
}

/* Pulse for notifications */
.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Spin for loading */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

### 8.3 Common CSS Classes

```css
/* src/styles/Common.module.css */

/* Card Styles */
.cardElevated {
  background: var(--bg-card-elevated);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.cardInteractive {
  composes: cardElevated;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cardInteractive:hover {
  border-color: var(--chart-1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

/* Score Badges */
.scoreBadge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
}

.scoreBadgeGreen {
  background: var(--score-green-bg);
  color: var(--score-green);
  border: 1px solid var(--score-green-border);
}

.scoreBadgeYellow {
  background: var(--score-yellow-bg);
  color: var(--score-yellow);
  border: 1px solid var(--score-yellow-border);
}

.scoreBadgeRed {
  background: var(--score-red-bg);
  color: var(--score-red);
  border: 1px solid var(--score-red-border);
}

/* Typography */
.tLabel {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.tCaption {
  font-size: 12px;
  color: var(--text-secondary);
}

.tTitle {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.tSubtitle {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.tScore {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.tScoreLg {
  font-size: 48px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

/* Utility */
.tabularNums {
  font-variant-numeric: tabular-nums;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scrollbarHide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbarHide::-webkit-scrollbar {
  display: none;
}
```

---

## 9. Analytics Page Customization System

The Analytics page features a comprehensive customizable card system with drag-and-drop reordering, localStorage persistence, and a sheet-based customizer panel.

### 9.1 Card Configuration Interface

**Location**: `src/components/analytics/AnalyticsCardRegistry.tsx`

```typescript
export interface AnalyticsCardConfig {
  id: string;           // Unique identifier (e.g., "arr-card", "revenue-trend")
  title: string;        // Display title (e.g., "ARR", "Revenue Trend")
  description: string;  // Card description
  category: "kpi" | "chart" | "gauge" | "table" | "heatmap" | "comparison";
  size: "sm" | "md" | "lg" | "xl";
  enabled: boolean;     // Whether card is visible
  order: number;        // Display order (0-indexed)
}
```

### 9.2 Default Analytics Cards

```typescript
export const DEFAULT_ANALYTICS_CARDS: AnalyticsCardConfig[] = [
  // KPI Cards (size: sm)
  { id: "arr-card", title: "ARR", description: "Annual Recurring Revenue", category: "kpi", size: "sm", enabled: true, order: 0 },
  { id: "mrr-card", title: "MRR", description: "Monthly Recurring Revenue", category: "kpi", size: "sm", enabled: true, order: 1 },
  { id: "nrr-card", title: "NRR", description: "Net Revenue Retention", category: "kpi", size: "sm", enabled: true, order: 2 },
  { id: "cac-card", title: "CAC", description: "Customer Acquisition Cost", category: "kpi", size: "sm", enabled: true, order: 3 },
  { id: "ltv-card", title: "LTV", description: "Lifetime Value", category: "kpi", size: "sm", enabled: false, order: 4 },
  { id: "churn-card", title: "Churn Rate", description: "Monthly churn percentage", category: "kpi", size: "sm", enabled: true, order: 5 },

  // Gauge Cards (size: md)
  { id: "health-gauge", title: "Business Health", description: "Overall health score", category: "gauge", size: "md", enabled: true, order: 6 },
  { id: "runway-gauge", title: "Runway", description: "Months of cash remaining", category: "gauge", size: "md", enabled: true, order: 7 },
  { id: "pipeline-gauge", title: "Pipeline Coverage", description: "Pipeline vs quota ratio", category: "gauge", size: "md", enabled: false, order: 8 },

  // Chart Cards (size: lg)
  { id: "revenue-trend", title: "Revenue Trend", description: "12-month revenue history", category: "chart", size: "lg", enabled: true, order: 9 },
  { id: "growth-chart", title: "Growth Trajectory", description: "YoY growth comparison", category: "chart", size: "lg", enabled: true, order: 10 },
  { id: "cohort-chart", title: "Cohort Retention", description: "Customer cohort analysis", category: "chart", size: "lg", enabled: false, order: 11 },

  // Comparison Cards (size: md)
  { id: "win-loss", title: "Win/Loss Ratio", description: "Deal outcomes breakdown", category: "comparison", size: "md", enabled: true, order: 12 },
  { id: "benchmark", title: "Industry Benchmark", description: "Performance vs peers", category: "comparison", size: "md", enabled: true, order: 13 },

  // Heatmap Cards (size: lg)
  { id: "activity-heatmap", title: "Activity Heatmap", description: "Customer engagement patterns", category: "heatmap", size: "lg", enabled: true, order: 14 },
  { id: "risk-heatmap", title: "Risk Distribution", description: "Risk concentration map", category: "heatmap", size: "lg", enabled: false, order: 15 },

  // Table Cards (size: lg)
  { id: "top-accounts", title: "Top Accounts", description: "Highest value customers", category: "table", size: "lg", enabled: true, order: 16 },
  { id: "at-risk", title: "At-Risk Accounts", description: "Accounts needing attention", category: "table", size: "lg", enabled: true, order: 17 },
  { id: "recent-deals", title: "Recent Deals", description: "Latest closed opportunities", category: "table", size: "lg", enabled: false, order: 18 },
];
```

### 9.3 Card Size & Grid Configuration

```typescript
// Grid span mapping (CSS classes)
export function getCardGridSpan(size: AnalyticsCardConfig["size"]): string {
  switch (size) {
    case "sm": return "col-span-1";              // 1 column
    case "md": return "col-span-1 md:col-span-2"; // 1 on mobile, 2 on desktop
    case "lg": return "col-span-2 md:col-span-2"; // 2 columns
    case "xl": return "col-span-2 md:col-span-2"; // 2 columns (full width possible)
    default: return "col-span-1";
  }
}

// Card height classes
export function getCardHeight(size: AnalyticsCardConfig["size"]): string {
  switch (size) {
    case "sm": return "h-[140px]";
    case "md": return "h-[180px]";
    case "lg": return "h-[220px]";
    case "xl": return "h-[260px]";
    default: return "h-[140px]";
  }
}
```

### 9.4 Category Labels

```typescript
import { Gauge, LineChart, Activity, BarChart3, ThermometerSun, GitCompare } from 'lucide-react';

export const CATEGORY_LABELS: Record<AnalyticsCardConfig["category"], { label: string; icon: LucideIcon }> = {
  kpi: { label: "KPI Metrics", icon: Gauge },
  chart: { label: "Charts", icon: LineChart },
  gauge: { label: "Gauges", icon: Activity },
  table: { label: "Tables", icon: BarChart3 },
  heatmap: { label: "Heatmaps", icon: ThermometerSun },
  comparison: { label: "Comparisons", icon: GitCompare },
};
```

### 9.5 Card Renderer Components

Each category has a dedicated renderer component:

```typescript
// KPI Card - Small metric display
export function KPICard({ id }: { id: string }) {
  // Shows: title, value, change percentage, trend arrow
  // Data: KPI_DATA[id] → { value: "$1.7M", change: 24, trend: "up" }
}

// Gauge Card - Circular progress visualization
export function GaugeCard({ id }: { id: string }) {
  // Shows: title, circular SVG gauge, value in center, status label
  // Data: GAUGE_DATA[id] → { value: 78, max: 100, label: "Score", status: "good" }
}

// Chart Card - Bar/line chart visualization
export function ChartCard({ id }: { id: string }) {
  // Shows: title, sparkline bar chart (12 bars for months)
  // Uses simple div-based bars with height percentages
}

// Comparison Card - Progress bar comparisons
export function ComparisonCard({ id }: { id: string }) {
  // Shows: title, two progress bars (e.g., Won vs Lost, You vs Industry)
}

// Heatmap Card - Grid intensity visualization
export function HeatmapCard({ id }: { id: string }) {
  // Shows: title, 5x4 grid (days × time slots) with varying opacity
}

// Table Card - List with status indicators
export function TableCard({ id }: { id: string }) {
  // Shows: title, list of items with name, value, status dot
}

// Main renderer factory
export function renderAnalyticsCard(config: AnalyticsCardConfig) {
  switch (config.category) {
    case "kpi": return <KPICard id={config.id} />;
    case "gauge": return <GaugeCard id={config.id} />;
    case "chart": return <ChartCard id={config.id} />;
    case "comparison": return <ComparisonCard id={config.id} />;
    case "heatmap": return <HeatmapCard id={config.id} />;
    case "table": return <TableCard id={config.id} />;
    default: return null;
  }
}
```

### 9.6 useAnalyticsLayout Hook

**Location**: `src/hooks/useAnalyticsLayout.ts`

```typescript
const STORAGE_KEY = "analytics-dashboard-layout";

export function useAnalyticsLayout() {
  const [cards, setCards] = useState<AnalyticsCardConfig[]>(() => {
    // Load from localStorage on initial render, merge with defaults
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return mergeWithDefaults(JSON.parse(saved));
    }
    return [...DEFAULT_ANALYTICS_CARDS];
  });

  // Auto-save to localStorage on changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
  }, [cards]);

  const updateCards = useCallback((newCards: AnalyticsCardConfig[]) => {
    setCards(newCards);
  }, []);

  const resetToDefaults = useCallback(() => {
    setCards([...DEFAULT_ANALYTICS_CARDS]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const moveCard = useCallback((dragIndex: number, hoverIndex: number) => {
    // Reorder enabled cards, update order values, sort
    setCards((prevCards) => {
      const enabledCards = prevCards.filter(c => c.enabled);
      const dragCard = enabledCards[dragIndex];
      if (!dragCard) return prevCards;

      const newEnabledCards = [...enabledCards];
      newEnabledCards.splice(dragIndex, 1);
      newEnabledCards.splice(hoverIndex, 0, dragCard);

      return prevCards.map(card => {
        const newIndex = newEnabledCards.findIndex(c => c.id === card.id);
        return newIndex !== -1 ? { ...card, order: newIndex } : card;
      }).sort((a, b) => a.order - b.order);
    });
  }, []);

  const enabledCards = cards.filter(c => c.enabled).sort((a, b) => a.order - b.order);

  return { cards, enabledCards, updateCards, resetToDefaults, moveCard };
}

// Merge saved layout with defaults (handles new cards added later)
function mergeWithDefaults(saved: AnalyticsCardConfig[]): AnalyticsCardConfig[] {
  const savedIds = new Set(saved.map(c => c.id));
  const merged = [...saved];
  DEFAULT_ANALYTICS_CARDS.forEach(defaultCard => {
    if (!savedIds.has(defaultCard.id)) merged.push(defaultCard);
  });
  return merged.sort((a, b) => a.order - b.order);
}
```

### 9.7 DraggableCard Component

**Location**: `src/components/analytics/DraggableCard.tsx`

Uses HTML5 native drag-and-drop API (no external library needed).

```typescript
interface DraggableCardProps {
  card: AnalyticsCardConfig;
  index: number;
  onMove: (dragIndex: number, hoverIndex: number) => void;
  onRemove: (cardId: string) => void;
  isEditMode: boolean;
}

export function DraggableCard({ card, index, onMove, onRemove, isEditMode }: DraggableCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  // Drag handlers
  const handleDragStart = (e: React.DragEvent) => {
    if (!isEditMode) return;
    setIsDragging(true);
    e.dataTransfer.setData("application/analytics-card", index.toString());
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDrop = (e: React.DragEvent) => {
    if (!isEditMode) return;
    e.preventDefault();
    const dragIndex = parseInt(e.dataTransfer.getData("application/analytics-card"), 10);
    if (!isNaN(dragIndex) && dragIndex !== index) {
      onMove(dragIndex, index);
    }
  };

  return (
    <div
      ref={ref}
      draggable={isEditMode}
      onDragStart={handleDragStart}
      onDragEnd={() => setIsDragging(false)}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={cn(
        getCardGridSpan(card.size),
        getCardHeight(card.size),
        "relative group bg-card border border-border rounded-xl p-4",
        isDragging && "opacity-50 scale-[0.98]",
        isDragOver && "border-primary border-2 bg-primary/5",
        isEditMode && "cursor-grab active:cursor-grabbing"
      )}
    >
      {/* Edit Mode Controls - Remove button */}
      {isEditMode && (
        <button
          onClick={() => onRemove(card.id)}
          className="absolute -top-2 -right-2 p-1.5 rounded-full bg-destructive opacity-0 group-hover:opacity-100"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Drag Handle */}
      {isEditMode && (
        <div className="absolute top-2 left-2 opacity-40 group-hover:opacity-100">
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </div>
      )}

      {/* Card Content */}
      <div className={cn("h-full overflow-hidden", isEditMode && "pl-5")}>
        {renderAnalyticsCard(card)}
      </div>
    </div>
  );
}
```

### 9.8 AnalyticsCustomizer Component

**Location**: `src/components/analytics/AnalyticsCustomizer.tsx`

A Sheet/slide-out panel for managing card visibility.

```typescript
interface AnalyticsCustomizerProps {
  cards: AnalyticsCardConfig[];
  onCardsChange: (cards: AnalyticsCardConfig[]) => void;
  onReset: () => void;
}

export function AnalyticsCustomizer({ cards, onCardsChange, onReset }: AnalyticsCustomizerProps) {
  const [open, setOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(Object.keys(CATEGORY_LABELS))
  );

  // Toggle individual card
  const handleToggle = (cardId: string) => {
    onCardsChange(cards.map(card =>
      card.id === cardId ? { ...card, enabled: !card.enabled } : card
    ));
  };

  // Quick actions
  const enableAll = () => onCardsChange(cards.map(c => ({ ...c, enabled: true })));
  const disableAll = () => onCardsChange(cards.map(c => ({ ...c, enabled: false })));

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings2 /> Customize <Badge>{enabledCount}</Badge>
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Customize Analytics</SheetTitle>
          <SheetDescription>Toggle cards on/off. Changes saved automatically.</SheetDescription>
        </SheetHeader>

        {/* Quick Actions: Show All | Hide All | Reset */}
        <div className="flex gap-2">
          <Button onClick={enableAll}>Show All</Button>
          <Button onClick={disableAll}>Hide All</Button>
          <Button onClick={onReset}>Reset</Button>
        </div>

        <ScrollArea>
          {/* Grouped by category with collapsible sections */}
          {categories.map(category => (
            <div key={category}>
              <button onClick={() => toggleCategory(category)}>
                {CATEGORY_LABELS[category].label} ({enabledInCategory}/{total})
              </button>
              {isExpanded && categoryCards.map(card => (
                <div key={card.id}>
                  <span>{card.title}</span>
                  <Badge>{card.size}</Badge>
                  <Switch checked={card.enabled} onChange={() => handleToggle(card.id)} />
                </div>
              ))}
            </div>
          ))}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
```

### 9.9 Required UI Components

These UI primitives are needed for the analytics customization system:

| Component | Description | Implementation |
|-----------|-------------|----------------|
| `Sheet` | Slide-out panel from edge of screen | CSS + state (no library needed) |
| `Switch` | Toggle switch for on/off | `<input type="checkbox">` styled |
| `ScrollArea` | Custom scrollable container | CSS `overflow: auto` with custom scrollbar |
| `Badge` | Small label/count indicator | Already in plan |

**Sheet Component (CSS Modules implementation)**:

```css
/* Sheet.module.css */
.sheetOverlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 50;
  opacity: 0;
  transition: opacity 0.2s;
}
.sheetOverlay.open { opacity: 1; }

.sheetContent {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 400px;
  background: var(--bg-card);
  border-left: 1px solid var(--border-default);
  transform: translateX(100%);
  transition: transform 0.3s ease;
  z-index: 51;
}
.sheetContent.open { transform: translateX(0); }
```

**Switch Component (CSS Modules implementation)**:

```css
/* Switch.module.css */
.switch {
  position: relative;
  width: 36px;
  height: 20px;
  background: var(--bg-muted);
  border-radius: 9999px;
  cursor: pointer;
  transition: background 0.2s;
}
.switch.checked { background: var(--primary); }

.switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: white;
  border-radius: 50%;
  transition: transform 0.2s;
}
.switch.checked::after { transform: translateX(16px); }
```

### 9.10 Analytics Page Integration

**Location**: `src/pages/Analytics.tsx`

```typescript
const Analytics = () => {
  const [isEditMode, setIsEditMode] = useState(false);
  const { cards, enabledCards, updateCards, resetToDefaults, moveCard } = useAnalyticsLayout();

  const handleRemoveCard = (cardId: string) => {
    updateCards(cards.map(card =>
      card.id === cardId ? { ...card, enabled: false } : card
    ));
  };

  return (
    <AppLayout title="Analytics">
      {/* Header with Edit Mode Toggle + Customizer */}
      <header>
        <Button onClick={() => setIsEditMode(!isEditMode)}>
          {isEditMode ? <><Check /> Done</> : <><Pencil /> Edit Layout</>}
        </Button>
        <AnalyticsCustomizer cards={cards} onCardsChange={updateCards} onReset={resetToDefaults} />
      </header>

      {/* Edit Mode Banner */}
      {isEditMode && (
        <div className="bg-primary/10 border border-primary/20 p-3 rounded-lg">
          <LayoutGrid /> Edit Mode Active - Drag cards to reorder, click × to remove
        </div>
      )}

      {/* 8-Pillar Scorecard Section */}
      <section>{/* Pillar grid - same as before */}</section>

      {/* Signal Map + Trend Analysis */}
      <section>{/* ExpandableSignalMap + GrowthForecast + RevenueConcentration */}</section>

      {/* Customizable Cards Grid */}
      <section>
        <h2>Custom Dashboard ({enabledCards.length} of {cards.length} cards)</h2>
        {enabledCards.length === 0 ? (
          <div className="empty-state">No cards enabled - Click Customize to add</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {enabledCards.map((card, index) => (
              <DraggableCard
                key={card.id}
                card={card}
                index={index}
                onMove={moveCard}
                onRemove={handleRemoveCard}
                isEditMode={isEditMode}
              />
            ))}
          </div>
        )}
      </section>
    </AppLayout>
  );
};
```

---

## 10. Data Flow & API Mapping

### 10.1 Dashboard Data Requirements

| UI Component | API Endpoint | Data Used |
|--------------|--------------|-----------|
| Exit Readiness Hero | `/api/scoring/companies/:id/bde-score` | overall_score, confidence, valuation_range |
| Exit Readiness Hero | `/api/scoring/companies/:id/recommendation` | recommendation, rationale |
| Pillar Strip | `/api/scoring/companies/:id/bde-score` | pillar_scores |
| Top Exit Risks | `/api/scoring/companies/:id/flags` | red_flags, yellow_flags |
| Multiple Improvers | `/api/scoring/companies/:id/recommendation` | value_drivers, 100_day_plan |
| KPI Cards / Work Tiles | `/api/scoring/companies/:id/metrics` | metrics |
| Data Freshness | `/api/scoring/companies/:id/analysis-status` | has_score, last_scored_at |
| Health Snapshot | `/api/scoring/companies/:id/bde-score` | pillar_scores |
| Today's Priorities | `/api/scoring/companies/:id/flags` | red_flags (severity sorted) |

### 10.2 Company Selection Flow

```
1. User logs in
2. Fetch company list: GET /api/companies
3. Store selected company in Context/localStorage
4. All scoring endpoints use selected company ID
5. Company selector updates context → triggers data refresh
```

---

## 11. Implementation Order

### Phase 1: Foundation ✅ COMPLETED
1. ✅ Install lucide-react
2. ✅ Add CSS variables to `index.css`
3. ✅ Create `src/styles/animations.css`
4. ✅ Create `src/lib/constants.ts` (pillars, scores, thresholds)
5. ✅ Create `src/lib/scorecard-utils.ts` (helper functions)
6. ✅ Update `Common.module.css` with new classes

### Phase 2: Core UI Components ✅ COMPLETED
1. ✅ `Tooltip.tsx` + CSS
2. ✅ `ConfidenceMeter.tsx` + CSS
3. ✅ `KpiCard.tsx` + CSS
4. ✅ `Badge.tsx` + CSS
5. ✅ `Button.tsx` + CSS
6. ✅ `Card.tsx` + CSS
7. ✅ `index.ts` barrel export

### Phase 3: Layout Components (NEXT)
**Goal**: Set up the app shell with new sidebar and layout

**UI Components to build:**
1. `Sheet.tsx` + CSS - Slide-out panel (needed for mobile nav, customizer)
2. `Switch.tsx` + CSS - Toggle switch (needed for settings, customizer)
3. `Avatar.tsx` + CSS - User avatar display
4. `Separator.tsx` + CSS - Visual divider
5. `ScrollArea.tsx` + CSS - Custom scrollable container

**Layout Components:**
6. `AppSidebar.tsx` + CSS - New sidebar with company selector, collapsible
7. `AppLayout.tsx` + CSS - Main layout wrapper
8. Update routing for new nav structure

### Phase 4: Home Page Components
**Goal**: Build the Exit Readiness (Home) page

**UI Components to build:**
1. `Skeleton.tsx` + CSS - Loading placeholders
2. `Dialog.tsx` + CSS - Modal dialog
3. `Popover.tsx` + CSS - Popover dropdown
4. `DropdownMenu.tsx` + CSS - Dropdown menus

**Home Components:**
5. `ExitReadinessHero.tsx` + CSS (with ring gauge)
6. `ScoreFactors.tsx` + CSS
7. `PillarStrip.tsx` + CSS
8. `TopExitRisks.tsx` + CSS
9. `MultipleImprovers.tsx` + CSS
10. `MinimalChatBar.tsx` + CSS

**Page Assembly:**
11. Create `Index.tsx` (Home page)
12. Wire up API calls
13. Add loading states

### Phase 5: Dashboard & Owner View
**Goal**: Build the Owner Dashboard page

**UI Components to build:**
1. `Table.tsx` + CSS - Data tables
2. `Tabs.tsx` + CSS - Tab navigation
3. `Progress.tsx` + CSS - Progress bars
4. `Alert.tsx` + CSS - Alert messages
5. `Toast.tsx` / `Toaster.tsx` + CSS - Notifications

**Dashboard Components:**
6. `HealthSnapshot.tsx` + CSS - 8-pillar grid
7. `WorkTile.tsx` + CSS - Work category tiles
8. `TodaysPriorities.tsx` + CSS - Priority alerts
9. `WeeklyChanges.tsx` + CSS - Recent changes
10. `DataFreshness.tsx` + CSS - Connector status

**Page Assembly:**
11. Create `Dashboard.tsx` (Owner Dashboard)
12. Wire up API calls

### Phase 6: Analytics Page & Customization
**Goal**: Build the customizable Analytics page

**UI Components to build:**
1. `Accordion.tsx` + CSS - Collapsible sections
2. `Collapsible.tsx` + CSS - Collapsible content
3. `Pagination.tsx` + CSS - Page navigation
4. `Toggle.tsx` / `ToggleGroup.tsx` + CSS - Toggle buttons

**Analytics Components:**
5. `AnalyticsCardRegistry.tsx` - Card configs + 6 renderers
6. `useAnalyticsLayout.ts` hook - State + localStorage
7. `DraggableCard.tsx` - Drag-and-drop wrapper
8. `AnalyticsCustomizer.tsx` - Card toggle panel
9. `ValueFragilityMatrix.tsx` (Signal Map) + CSS
10. `ExpandableSignalMap.tsx` + CSS

**Page Assembly:**
11. Create `Analytics.tsx` page
12. Create `AnalyticsPillarDetail.tsx` page

### Phase 7: Company Scorecard
**Goal**: Build the Company Scorecard page

**Scorecard Components:**
1. `HeaderRibbon.tsx` + CSS - Company header
2. `OverallCard.tsx` + CSS - Overall score display
3. `PillarCard.tsx` + CSS - Individual pillar cards
4. `PillarGrid.tsx` + CSS - 8-pillar grid layout
5. `KpiStrip.tsx` + CSS - Key metrics strip
6. `ActionsBar.tsx` + CSS - Action buttons

**Page Assembly:**
7. Create `CompanyScorecard.tsx` page
8. Create `PillarDetail.tsx` page

### Phase 8: Copilot & Remaining Pages
**Goal**: Enhance AI chat and build remaining pages

**Copilot Components:**
1. `ImmersiveChat.tsx` + CSS - Full-screen chat
2. `ChatMessage.tsx` + CSS - Message with citations
3. `QuickPrompts.tsx` + CSS - Suggested prompts
4. `CitationPanel.tsx` + CSS - Source documents

**Pages:**
5. Enhance `Copilot.tsx` page
6. Create `Ingestion.tsx` page
7. Create `Reports.tsx` page
8. Create `Notifications.tsx` page
9. Create `Settings.tsx` page

### Phase 9: Polish & Testing
**Goal**: Final polish and comprehensive testing

1. Responsive design adjustments
2. Dark mode testing
3. Animation polish
4. Cross-browser testing
5. Permission checks
6. Performance optimization
7. Accessibility review

### Implementation Summary

| Phase | Focus | UI Components | Page Components | Status |
|-------|-------|---------------|-----------------|--------|
| 1 | Foundation | - | - | ✅ Done |
| 2 | Core UI | 6 | - | ✅ Done |
| 3 | Layout | 5 | 2 | 🔲 Next |
| 4 | Home Page | 4 | 6 | 🔲 Pending |
| 5 | Dashboard | 5 | 6 | 🔲 Pending |
| 6 | Analytics | 4 | 6 | 🔲 Pending |
| 7 | Scorecard | - | 8 | 🔲 Pending |
| 8 | Copilot | - | 9 | 🔲 Pending |
| 9 | Polish | - | - | 🔲 Pending |
| **Total** | | **24** | **37** | |

---

## 12. File Structure (Aligned with Reference UI)

The file structure follows the reference UI organization (`new-ui-reference/src/`):

```
frontend/src/
├── components/
│   │
│   ├── ui/                          # UI Primitives (ref: components/ui/)
│   │   ├── accordion.tsx
│   │   ├── alert.tsx
│   │   ├── avatar.tsx
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── checkbox.tsx
│   │   ├── collapsible.tsx
│   │   ├── confidence-meter.tsx     # Confidence bar display
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── input.tsx
│   │   ├── kpi-card.tsx             # KPI metric card
│   │   ├── label.tsx
│   │   ├── popover.tsx
│   │   ├── progress.tsx
│   │   ├── scroll-area.tsx
│   │   ├── select.tsx
│   │   ├── separator.tsx
│   │   ├── sheet.tsx                # Slide-out panel
│   │   ├── skeleton.tsx
│   │   ├── switch.tsx               # Toggle switch
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   ├── textarea.tsx
│   │   ├── toast.tsx
│   │   ├── toaster.tsx
│   │   ├── tooltip.tsx
│   │   └── use-toast.ts
│   │
│   ├── home/                        # Home/Index page components (ref: components/home/)
│   │   ├── index.ts                 # Barrel export
│   │   ├── ExitReadinessHero.tsx    # Main hero with score ring
│   │   ├── ScoreFactors.tsx         # Pillar score pills
│   │   ├── PillarStrip.tsx          # Horizontal pillar buttons
│   │   ├── MinimalChatBar.tsx       # Simple chat input
│   │   ├── ImmersiveChat.tsx        # Full-screen chat
│   │   ├── TopExitRisks.tsx         # Risk list with actions
│   │   ├── MultipleImprovers.tsx    # Value drivers
│   │   ├── ValueFragilityMatrix.tsx # Signal map (value vs fragility)
│   │   ├── DashboardCustomizer.tsx  # Card toggle panel
│   │   ├── AiSpotlightAlert.tsx     # AI-suggested cards
│   │   ├── TodaysPriorities.tsx     # Priority alerts
│   │   ├── WeeklyChanges.tsx        # What changed this week
│   │   ├── GrowthForecast.tsx       # Growth trend chart
│   │   ├── RevenueChart.tsx         # Revenue vs target
│   │   ├── RevenueConcentration.tsx # Revenue breakdown
│   │   ├── CustomerHealthGrid.tsx   # Customer metrics
│   │   ├── RiskRadar.tsx            # Risk across pillars
│   │   ├── WinLossChart.tsx         # Win/loss analysis
│   │   ├── PipelineBreakdown.tsx    # Sales pipeline
│   │   ├── HealthRingScore.tsx      # Ring gauge
│   │   └── ConfidenceScore.tsx      # Confidence display
│   │
│   ├── analytics/                   # Analytics page components (ref: components/analytics/)
│   │   ├── AnalyticsCardRegistry.tsx  # Card configs + 6 renderers
│   │   ├── AnalyticsCustomizer.tsx    # Card toggle sheet
│   │   ├── DraggableCard.tsx          # Drag-and-drop wrapper
│   │   ├── ExpandableSignalMap.tsx    # Expandable signal map
│   │   ├── PillarAnalytics.tsx        # Pillar analytics view
│   │   └── index.ts
│   │
│   ├── scorecard/                   # Company scorecard components (ref: components/scorecard/)
│   │   ├── index.ts
│   │   ├── HeaderRibbon.tsx         # Company header with sources
│   │   ├── OverallCard.tsx          # Overall score with valuation
│   │   ├── PillarCard.tsx           # Individual pillar card
│   │   ├── PillarGrid.tsx           # 8-pillar grid layout
│   │   ├── KpiStrip.tsx             # Key metrics strip
│   │   ├── KpiChart.tsx             # KPI sparkline chart
│   │   ├── ActionsBar.tsx           # Action buttons bar
│   │   └── RemediationSidebar.tsx   # Recommendations sidebar
│   │
│   ├── layout/                      # Layout components (ref: components/layout/)
│   │   ├── AppLayout.tsx            # Main layout wrapper
│   │   ├── AppSidebar.tsx           # Navigation sidebar
│   │   └── index.ts
│   │
│   ├── icons/                       # Custom icons (ref: components/icons/)
│   │   └── ChatSendIcon.tsx
│   │
│   └── NavLink.tsx                  # Navigation link component
│
├── lib/                             # Utilities (ref: src/lib/)
│   ├── utils.ts                     # cn() and other utils
│   ├── constants.ts                 # PILLARS, score colors, etc.
│   ├── scorecard-utils.ts           # Scorecard helper functions
│   └── acronyms.ts                  # Acronym definitions
│
├── hooks/                           # Custom hooks (ref: src/hooks/)
│   ├── useAnalyticsLayout.ts        # Analytics card state + localStorage
│   ├── useScorecard.ts              # Scorecard data fetching
│   ├── useKpiHistory.ts             # KPI history data
│   ├── useAuth.tsx                  # Authentication hook
│   ├── use-toast.ts                 # Toast notifications
│   └── use-mobile.tsx               # Mobile detection
│
├── types/                           # TypeScript types (ref: src/types/)
│   └── scorecard.ts                 # Scorecard types
│
├── context/
│   ├── AuthContext.tsx              # Keep
│   ├── PermissionContext.tsx        # Keep
│   └── CompanyContext.tsx           # New (selected company)
├── pages/
│   ├── Index.tsx                    # Home - Exit Readiness (ref: pages/Index.tsx)
│   ├── Dashboard.tsx                # Owner Dashboard (ref: pages/Dashboard.tsx)
│   ├── Analytics.tsx                # Analytics page (ref: pages/Analytics.tsx)
│   ├── AnalyticsPillarDetail.tsx    # Pillar analytics (ref: pages/AnalyticsPillarDetail.tsx)
│   ├── CompanyScorecard.tsx         # Company scorecard (ref: pages/CompanyScorecard.tsx)
│   ├── PillarDetail.tsx             # Company pillar detail (ref: pages/PillarDetail.tsx)
│   ├── Copilot.tsx                  # AI Analyst chat (ref: pages/Copilot.tsx)
│   ├── Ingestion.tsx                # Data ingestion (ref: pages/Ingestion.tsx)
│   ├── Notifications.tsx            # Alerts page (ref: pages/Notifications.tsx)
│   ├── Reports.tsx                  # Reports page (ref: pages/Reports.tsx)
│   ├── Settings.tsx                 # Settings (ref: pages/Settings.tsx)
│   ├── MetricDetail.tsx             # Metric deep-dive (ref: pages/MetricDetail.tsx)
│   ├── SignalDetail.tsx             # Signal deep-dive (ref: pages/SignalDetail.tsx)
│   ├── Auth.tsx                     # Login page (ref: pages/Auth.tsx)
│   ├── NotFound.tsx                 # 404 page (ref: pages/NotFound.tsx)
│   └── admin/                       # Keep existing admin pages
│       ├── Tenants.tsx
│       ├── Users.tsx
│       └── PromptManagement.tsx
├── styles/
│   ├── animations.css               # New
│   ├── Common.module.css            # Enhanced
│   ├── Dashboard.module.css         # Redesigned
│   └── components/
│       ├── common/
│       │   ├── Tooltip.module.css
│       │   ├── ConfidenceMeter.module.css
│       │   └── KpiCard.module.css
│       ├── dashboard/
│       │   ├── ExitReadinessHero.module.css
│       │   ├── PillarStrip.module.css
│       │   ├── TopExitRisks.module.css
│       │   ├── MultipleImprovers.module.css
│       │   ├── HealthSnapshot.module.css
│       │   ├── WorkTile.module.css
│       │   └── ValueFragilityMatrix.module.css
│       ├── analytics/
│       │   ├── AnalyticsCardRegistry.module.css
│       │   ├── AnalyticsCustomizer.module.css
│       │   ├── DraggableCard.module.css
│       │   ├── ExpandableSignalMap.module.css
│       │   └── Sheet.module.css
│       ├── copilot/
│       │   ├── MinimalChatBar.module.css
│       │   ├── ImmersiveChat.module.css
│       │   └── ChatMessage.module.css
│       └── layout/
│           └── Sidebar.module.css
├── utils/
│   ├── api.ts                       # Keep
│   ├── scoreHelpers.ts              # New
│   └── fileUtils.ts                 # Keep
└── index.css                        # Enhanced (CSS variables)
```

---

## 13. Reference Files Location

The design reference is located at:
```
/home/user/Projects/Docs/BDE UI V2/remix-of-remix-of-business-dashboard-79-main/
```

**Key files for visual reference**:

| Component | Reference File |
|-----------|---------------|
| Home Page Layout | `src/pages/Index.tsx` |
| Owner Dashboard | `src/pages/Dashboard.tsx` |
| Analytics Page | `src/pages/Analytics.tsx` |
| Exit Readiness Hero | `src/components/home/ExitReadinessHero.tsx` |
| Score Factors | `src/components/home/ScoreFactors.tsx` |
| Pillar Strip | `src/components/home/PillarStrip.tsx` |
| Top Exit Risks | `src/components/home/TopExitRisks.tsx` |
| Multiple Improvers | `src/components/home/MultipleImprovers.tsx` |
| Minimal Chat Bar | `src/components/home/MinimalChatBar.tsx` |
| Immersive Chat | `src/components/home/ImmersiveChat.tsx` |
| Signal Map | `src/components/home/ValueFragilityMatrix.tsx` |
| Confidence Meter | `src/components/ui/confidence-meter.tsx` |
| KPI Card | `src/components/ui/kpi-card.tsx` |
| Sidebar | `src/components/layout/AppSidebar.tsx` |
| Layout | `src/components/layout/AppLayout.tsx` |
| Constants | `src/lib/constants.ts` |
| Score Utils | `src/lib/scorecard-utils.ts` |
| **Analytics Customization** | |
| Analytics Card Registry | `src/components/analytics/AnalyticsCardRegistry.tsx` |
| Analytics Customizer | `src/components/analytics/AnalyticsCustomizer.tsx` |
| Draggable Card | `src/components/analytics/DraggableCard.tsx` |
| Expandable Signal Map | `src/components/analytics/ExpandableSignalMap.tsx` |
| useAnalyticsLayout Hook | `src/hooks/useAnalyticsLayout.ts` |
| Sheet Component | `src/components/ui/sheet.tsx` |
| Switch Component | `src/components/ui/switch.tsx` |
| ScrollArea Component | `src/components/ui/scroll-area.tsx` |

---

## 14. Success Criteria

### Must Have (P0)
- [ ] Dashboard shows Exit Readiness Hero with animated ring gauge
- [ ] 8-pillar strip displays all pillar scores with health colors
- [ ] Pillar strip is clickable and navigates to pillar details
- [ ] Top Exit Risks display from flags API (red and yellow)
- [ ] Minimal chat bar present on dashboard
- [ ] Sidebar has company selector dropdown
- [ ] Sidebar is collapsible to icon-only mode
- [ ] All components responsive (mobile/tablet/desktop)
- [ ] No breaking changes to existing functionality
- [ ] Permissions still enforced correctly

### Should Have (P1)
- [ ] Multiple Improvers section shows value drivers
- [ ] KPI cards show key metrics with deltas
- [ ] Health snapshot grid with 8 pillars
- [ ] Work tiles for Financial, Customer, GTM, Product
- [ ] Confidence meter component working
- [ ] Today's Priorities section
- [ ] Data freshness indicators

### Nice to Have (P2)
- [ ] Dark mode support
- [ ] Signal Map visualization
- [ ] Immersive chat mode
- [ ] Weekly changes section
- [ ] Dashboard customizer
- [ ] AI spotlight alerts
- [ ] Staggered animations

---

## 15. Questions to Clarify with Client

1. **Score Display Scale**: Should we show 0-100 (current backend) or convert to 0-5 (new design)?
2. **Dark Mode**: Is dark mode required for initial release?
3. **Mobile Priority**: What percentage of users are on mobile?
4. **Home vs Dashboard**: Should `/` and `/dashboard` be different pages or same?
5. **Analytics Page**: Is this replacing existing scoring detail pages or additional?
6. **Notifications Page**: Is this in scope? What triggers notifications?
7. **Reports Page**: Is PDF export in scope for this release?
8. **Company Selector**: Should all users see all companies or respect permissions?

---

*Document created: January 26, 2026*
*Last updated: January 26, 2026*
*Updates: Added complete UI component inventory (Section 3.6), revised implementation phases with component mapping*
*Purpose: Frontend Design Implementation Guide*
*Reference: /home/user/Projects/Docs/BDE UI V2/remix-of-remix-of-business-dashboard-79-main/*
