# BDE Scoring System Implementation

## Overview

This is the complete implementation of the **Business Due Diligence Evaluation (BDE) Scoring System**. The system analyzes document chunks and extracts structured metrics to generate comprehensive acquisition scores and recommendations.

## Architecture

### **5-Stage Pipeline**

```
STAGE 1: Metric Extraction (LLM)
  → Extracts structured signals from document chunks
  → Stores in company_metrics table

STAGE 2: Pillar Aggregation (Code)
  → Fetches chunks + metrics per pillar
  → Calculates data coverage (deterministic)

STAGE 3A: Pillar Evaluation (LLM)
  → LLM evaluates criteria (meets green/yellow/red)
  → Does NOT assign numeric scores

STAGE 3B: Deterministic Scoring (Code)
  → Applies rubric rules to compute 0-5 scores
  → 100% deterministic and repeatable

STAGE 4: Flag Detection (LLM)
  → Detects red/yellow/green flags
  → Uses exposed prompts from database

STAGE 5: BDE Calculator (Math + LLM)
  → 5A: Calculate weighted score (pure math)
  → 5B: Generate acquisition recommendation (LLM)
```

## Key Design Principles

### ✅ **LLM Never Scores**
- LLM evaluates criteria (YES/NO questions)
- Code applies deterministic rules to assign scores
- Ensures repeatability and auditability

### ✅ **Metrics Extracted BEFORE Scoring**
- Stage 1 runs first (metrics are INPUTS)
- Metrics inform evaluation and scoring
- Proper dependency flow

### ✅ **Evidence Traceability**
- Every score links to evaluation
- Every evaluation links to chunks
- Complete audit trail

### ✅ **Prompts Are Exposed**
- Admins can edit prompts via UI
- Stored in `prompt_templates` table
- Same system as RAG prompts

### ✅ **Conflict Resolution**
- Metrics with different dates/values handled
- Most recent wins, flagged for review if unclear
- Historical values preserved

## Database Models

### Core Tables

- **`company_metrics`**: Extracted signals (Stage 1 output)
- **`pillar_data_coverage_config`**: Required data points checklist
- **`pillar_evaluation_criteria`**: LLM criteria assessment (Stage 3A)
- **`company_pillar_scores`**: Computed scores (Stage 3B)
- **`company_flags`**: Red/yellow/green flags (Stage 4)
- **`company_bde_scores`**: Overall weighted scores (Stage 5A)
- **`acquisition_recommendations`**: LLM recommendations (Stage 5B)

## API Endpoints

### Trigger Scoring
```
POST /api/scoring/companies/{company_id}/score
Body: { "recompute": false }
```

### Get BDE Score
```
GET /api/scoring/companies/{company_id}/bde-score
Response: {
  "overall_score": 78,
  "valuation_range": "5-7x ARR",
  "pillar_scores": {...}
}
```

### Get Pillar Details
```
GET /api/scoring/companies/{company_id}/pillars/{pillar}
Response: {
  "score": 4.2,
  "health_status": "green",
  "justification": "...",
  "key_findings": [...],
  "risks": [...]
}
```

### Get Metrics
```
GET /api/scoring/companies/{company_id}/metrics
Response: {
  "metrics": {
    "ARR": { "current_value": {...}, "historical": [...] }
  },
  "conflicts": [...]
}
```

### Get Flags
```
GET /api/scoring/companies/{company_id}/flags
Response: {
  "red_flags": [...],
  "yellow_flags": [...],
  "green_accelerants": [...]
}
```

### Get Recommendation
```
GET /api/scoring/companies/{company_id}/recommendation
Response: {
  "recommendation": "BUY WITH CONDITIONS",
  "rationale": "...",
  "value_drivers": [...],
  "key_risks": [...],
  "100_day_plan": [...]
}
```

## Setup Instructions

### 1. Run Database Migrations
```bash
# Apply new tables
alembic revision --autogenerate -m "Add BDE scoring tables"
alembic upgrade head
```

### 2. Seed Prompt Templates
```bash
cd web-app/database
python seed_scoring_prompts.py
```

### 3. Register API Routes
Add to `web-app/main.py`:
```python
from api.scoring import routes as scoring_routes

app.include_router(
    scoring_routes.router,
    prefix="/api/scoring",
    tags=["scoring"]
)
```

### 4. Test the Pipeline
```python
from services.scoring import ScoringOrchestrationService

orchestration = ScoringOrchestrationService()
result = await orchestration.score_company(
    db=session,
    company_id="...",
    tenant_id="...",
    recompute=True
)

print(f"Overall Score: {result['overall_score']}/100")
print(f"Valuation: {result['valuation_range']}")
```

## Metric Definitions

### Financial Health Signals
- ARR, MRR, RecurringRevenuePct
- GrossMarginPct, EBITDA_MarginPct
- BurnRateMonthly, RunwayMonths
- TopCustomerConcentrationPct

### GTM Engine Signals
- ICPDefined, PipelineCoverageRatio
- WinRatePct, AvgSalesCycleDays
- ForecastAccuracyPct, CRMDisciplineScore

### Customer Health Signals
- GRR, NRR, ChurnRatePct
- NPS, ExpansionRevenuePct
- AtRiskCustomerCount

### And 5 more pillars... (see metric_extraction_service.py)

## Scoring Rules

### Score Mapping (0-5 scale)
- **5.0**: Exceptional (Top 10%) - Reserved for perfection
- **4.0-4.75**: Strong (Top 25%)
- **3.0-3.9**: Adequate (Middle 50%)
- **2.0-2.9**: Weak (Bottom 25%)
- **1.0-1.9**: Fragile (Bottom 10%)
- **0.0**: Insufficient data

### Health Status
- **GREEN**: Score ≥ 4.0
- **YELLOW**: Score 2.5-3.9
- **RED**: Score < 2.5

### Weighted BDE Score
```
Overall =
  (Financial Health × 0.20) +
  (GTM Engine × 0.15) +
  (Customer Health × 0.15) +
  (Product/Tech × 0.15) +
  (Operational × 0.10) +
  (Leadership × 0.10) +
  (Ecosystem × 0.10) +
  (Service/Software × 0.05)

Convert to 0-100: Overall × 20
```

### Valuation Ranges
- **4.25-5.0** → 6-10x ARR (Premium)
- **3.75-4.24** → 5-7x ARR (Above-market)
- **3.00-3.74** → 3-5x ARR (Standard)
- **2.00-2.99** → 1.5-3x ARR (Discounted)
- **< 2.0** → Walk-away

## Customization

### Adding New Metrics
1. Edit `PILLAR_METRIC_DEFINITIONS` in `metric_extraction_service.py`
2. Add to `pillar_data_coverage_config` table
3. Re-run extraction for companies

### Modifying Prompts
1. Go to Admin UI → Settings → Prompts
2. Select prompt (flag_detection, acquisition_recommendation)
3. Edit template
4. Save (automatically versioned)

### Adjusting Scoring Logic
- Edit `_calculate_pillar_score()` in `scoring_services.py`
- Modify threshold values, penalties, or bonuses
- Changes apply immediately to new scores

## Monitoring

### Check Scoring Status
```sql
-- Get latest BDE scores
SELECT
    c.name,
    s.overall_score,
    s.valuation_range,
    s.calculated_at
FROM company_bde_scores s
JOIN companies c ON c.id = s.company_id
WHERE s.is_current = true
ORDER BY s.calculated_at DESC;
```

### View Pillar Breakdown
```sql
-- Get pillar scores for a company
SELECT
    pillar,
    score,
    health_status,
    data_coverage_percent,
    confidence
FROM company_pillar_scores
WHERE company_id = '...' AND is_current = true;
```

### Check Flags
```sql
-- Get active flags
SELECT
    flag_type,
    flag_category,
    flag_text,
    pillar,
    severity
FROM company_flags
WHERE company_id = '...' AND is_active = true
ORDER BY severity DESC;
```

## Troubleshooting

### Scoring Fails
- Check logs for LLM errors
- Verify chunks exist for company
- Ensure metrics were extracted
- Check data coverage (< 30% triggers failure)

### Low Confidence Scores
- Add more documents to company
- Re-run extraction with `recompute=true`
- Check for missing critical metrics

### Conflicting Metrics
- Review flagged metrics in UI
- Analyst resolves conflicts manually
- Or accept most recent value

## Performance

### Approximate Timing
- **Stage 1** (Metric Extraction): ~30-60 seconds
- **Stage 2** (Aggregation): ~5 seconds
- **Stage 3** (Evaluation + Scoring): ~2-3 minutes (8 pillars × LLM calls)
- **Stage 4** (Flag Detection): ~30 seconds
- **Stage 5** (Recommendation): ~30 seconds
- **Total**: ~3-5 minutes per company

### Optimization Tips
- Run in background (async)
- Cache aggregated pillar data
- Batch multiple companies
- Use faster LLM model (haiku) for non-critical stages

## Future Enhancements

- [ ] A/B test different prompts
- [ ] Human-in-the-loop score adjustments
- [ ] Comparative analysis (company vs company)
- [ ] Trend tracking (score changes over time)
- [ ] Export to PDF report
- [ ] Email notifications on scoring completion
- [ ] Webhook integration

## Support

For questions or issues:
- Check logs in `/var/log/bde/scoring.log`
- Review database state in tables above
- Contact dev team

---

**Implementation Date**: January 2026
**Version**: 1.0
**Status**: Production Ready
