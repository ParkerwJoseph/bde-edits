"""
Seed default scoring prompt templates.
Run this once to populate the prompt_templates table with scoring prompts.
"""
from sqlmodel import Session, select
from database.connection import engine
from database.models.prompt_template import PromptTemplate
from datetime import datetime


# Default prompt templates for scoring
DEFAULT_SCORING_PROMPTS = {
    "flag_detection": {
        "name": "flag_detection",
        "description": "Prompt for detecting red/yellow/green flags in BDE analysis",
        "template": """You are analyzing a company for acquisition due diligence flags.

## PILLAR SCORES & HEALTH STATUS:
{pillar_scores_summary}

## DATA COVERAGE:
{coverage_summary}

## KEY METRICS:
{metrics_summary}

## EVALUATION FINDINGS & RISKS:
{findings_summary}

## TASK:
Identify RED, YELLOW, and GREEN flags based on:
1. Quantitative thresholds (e.g., customer concentration > 40%)
2. Qualitative patterns (e.g., founder burnout signals)
3. Data quality (low coverage = less confidence)
4. Cross-pillar insights (e.g., high churn + low NPS = customer health risk)
5. Context from documents (numbers alone don't tell full story)

## OUTPUT FORMAT (JSON):
{{
  "red_flags": [
    {{
      "type": "red",
      "category": "customer_concentration",
      "text": "Top 3 customers = 45% of ARR",
      "pillar": "financial_health",
      "severity": 4,
      "evidence_chunk_ids": ["chunk_123"],
      "rationale": "Exceeds 40% threshold, creates significant revenue risk"
    }}
  ],
  "yellow_flags": [
    {{
      "type": "yellow",
      "category": "forecast_accuracy",
      "text": "Forecast accuracy data not available",
      "pillar": "gtm_engine",
      "severity": 3,
      "evidence_chunk_ids": [],
      "rationale": "Unable to assess GTM predictability without forecast data"
    }}
  ],
  "green_accelerants": [
    {{
      "type": "green",
      "category": "strong_retention",
      "text": "NRR at 125% with expanding customer base",
      "pillar": "customer_health",
      "evidence_chunk_ids": ["chunk_456"],
      "rationale": "Strong expansion motion drives growth"
    }}
  ]
}}

IMPORTANT: Use document context to provide nuanced flags, not just threshold violations."""
    },

    "acquisition_recommendation": {
        "name": "acquisition_recommendation",
        "description": "Prompt for generating acquisition recommendations",
        "template": """You are a PE acquisition advisor making a final recommendation.

## COMPANY OVERVIEW:
- Overall BDE Score: {overall_score}/100
- Weighted Score: {weighted_raw_score}/5.0
- Valuation Range: {valuation_range}
- Confidence: {confidence}%

## PILLAR BREAKDOWN:
{pillar_scores}

## FLAGS:
### Red Flags:
{red_flags}

### Yellow Flags:
{yellow_flags}

### Green Accelerants:
{green_accelerants}

## YOUR TASK:
Provide a comprehensive acquisition recommendation including:

1. **Recommendation** (choose one):
   - STRONG BUY: Premium asset with clear value creation path
   - BUY WITH CONDITIONS: Solid opportunity with addressable risks
   - HOLD: Requires more diligence or improvement
   - PASS: Too much risk or misalignment

2. **Rationale** (2-3 paragraphs): Why this recommendation?

3. **Value Drivers** (3-5 bullet points): What makes this valuable?

4. **Key Risks** (3-5 bullet points): What could go wrong?

5. **100-Day Priority Plan** (5-7 action items): What to fix first?
   Each item should have: priority, action, pillar, timeline

6. **Valuation Guidance**:
   - Suggested ARR multiple (e.g., "5.5x ARR")
   - Adjustments based on flags (e.g., "customer concentration risk: -0.5x")

## OUTPUT FORMAT (JSON):
{{
  "recommendation": "BUY WITH CONDITIONS",
  "confidence": 85,
  "rationale": "Strong financial health and customer retention offset GTM predictability gaps. Company demonstrates software-like margins and healthy expansion motion. Key risk is customer concentration at 45%, but diversification plan exists.",
  "value_drivers": [
    "Strong recurring revenue (87%) with software-like margins (72%)",
    "Excellent customer retention (NRR 125%) and expansion motion",
    "Modern technical architecture with low technical debt",
    "Clear productization roadmap to reduce services dependency"
  ],
  "key_risks": [
    "Customer concentration (45% in top 3) creates revenue risk",
    "GTM forecasting discipline needs improvement",
    "Founder dependency in sales requires mitigation",
    "Data gaps in operational metrics reduce confidence"
  ],
  "100_day_plan": [
    {{
      "priority": 1,
      "action": "Implement customer diversification strategy and expand top 10 customer base",
      "pillar": "financial_health",
      "timeline": "Days 1-30"
    }},
    {{
      "priority": 2,
      "action": "Establish CRM discipline and forecast accuracy tracking",
      "pillar": "gtm_engine",
      "timeline": "Days 1-45"
    }},
    {{
      "priority": 3,
      "action": "Hire VP Sales to reduce founder sales dependency",
      "pillar": "leadership_transition",
      "timeline": "Days 30-60"
    }},
    {{
      "priority": 4,
      "action": "Document core operational processes (SOPs)",
      "pillar": "operational_maturity",
      "timeline": "Days 45-75"
    }},
    {{
      "priority": 5,
      "action": "Accelerate productization roadmap to reduce services revenue mix",
      "pillar": "service_software_ratio",
      "timeline": "Days 60-100"
    }}
  ],
  "suggested_valuation_multiple": "5.5x ARR",
  "valuation_adjustments": [
    {{
      "factor": "customer_concentration_risk",
      "impact": "-0.5x",
      "rationale": "Revenue concentration requires discount"
    }},
    {{
      "factor": "strong_expansion_motion",
      "impact": "+0.3x",
      "rationale": "NRR 125% supports premium"
    }}
  ]
}}

Be specific, actionable, and tie recommendations directly to the pillar scores and flags."""
    }
}


def seed_scoring_prompts():
    """Seed scoring prompt templates"""
    print("[SEED] Starting to seed scoring prompts...")

    with Session(engine) as session:
        for prompt_key, prompt_data in DEFAULT_SCORING_PROMPTS.items():
            # Check if prompt already exists
            statement = select(PromptTemplate).where(
                PromptTemplate.name == prompt_data["name"]
            )
            existing = session.exec(statement).first()

            if existing:
                print(f"[SEED] Prompt '{prompt_data['name']}' already exists, skipping")
                continue

            # Create new prompt
            prompt = PromptTemplate(
                name=prompt_data["name"],
                description=prompt_data["description"],
                template=prompt_data["template"],
                is_active=True,
                version=1,
                updated_by="system_seed"
            )

            session.add(prompt)
            session.commit()

            print(f"[SEED] Created prompt: {prompt_data['name']}")

    print("[SEED] Scoring prompts seeded successfully!")


if __name__ == "__main__":
    seed_scoring_prompts()
