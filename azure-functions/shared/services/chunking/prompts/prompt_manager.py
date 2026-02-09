"""
Centralized prompt management for all chunking operations.
"""
from typing import Dict, Any, Optional

from shared.database.models.document import PILLAR_DESCRIPTIONS


class PromptManager:
    """
    Manages prompt templates for document and connector chunking.

    Provides entity-specific prompts for connectors and consistent
    document analysis prompts.
    """

    def __init__(self):
        self._pillar_descriptions = PILLAR_DESCRIPTIONS

    def get_prompt(
        self,
        source_type: str,
        entity_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get appropriate prompt for chunking operation.

        Args:
            source_type: 'document' or 'connector'
            entity_type: For connectors, the entity type (invoice, customer, etc.)
            context: Additional context for prompt formatting

        Returns:
            Formatted system prompt
        """
        context = context or {}
        pillar_list = self._format_pillar_list()

        if source_type == "document":
            return self._get_document_prompt(context, pillar_list)
        else:
            return self._get_connector_prompt(entity_type, context, pillar_list)

    def _format_pillar_list(self) -> str:
        """Format pillar descriptions for prompt"""
        return "\n".join([
            f"- {pillar.value}: {desc}"
            for pillar, desc in self._pillar_descriptions.items()
        ])

    def _get_document_prompt(self, context: dict, pillar_list: str) -> str:
        """Get document analysis prompt"""
        filename = context.get('document_filename', 'Unknown')
        total_pages = context.get('total_pages', 1)

        return f"""**CONTEXT**
You are analyzing business documents for Private Equity acquisition due diligence.
The extracted data directly impacts investment scoring, risk assessment, and acquisition recommendations.
Accuracy and correct pillar classification are critical — misclassified chunks lead to flawed decisions and wasted diligence effort.

**DOCUMENT**
- File: {filename}
- Current Page: {{page_number}} of {total_pages}
- Previous Pages Summary: {{accumulated_context}}

**ROLE**
Analyze the provided document page and extract all relevant business information into structured JSON chunks. 
Each chunk must represent a single, coherent business concept classified under exactly one BDE pillar. 
Group all content related to the same pillar—including sentences, metrics, tables, lists, and supporting context—into a single chunk regardless of length. 
**Never split semantically connected sentences, metrics, tables, or lists — all content that explains or supports the same pillar concept must remain together.**
Only split into separate chunks when the pillar, business question, or analytical focus clearly changes. 
Avoid creating one-liner chunks; if content belongs to the same pillar, it must remain together in one chunk.

**OBJECTIVE**
Produce accurate, traceable, pillar-correct data extraction that:
- Preserves exact wording, values, units, and time periods
- Includes confidence score reflecting extraction certainty
- Is explicitly present in the source document — no inference

Pillar correctness takes priority over completeness.

**BDE PILLAR DEFINITIONS**
{pillar_list}

**PILLAR CLASSIFICATION RULES (CRITICAL)**

1. **Identify Primary Business Question First**
   Before assigning any pillar, determine the primary business question the content answers. This ensures pillar assignment reflects analytical focus, not just keywords or metrics. Only assign a pillar if there is clear evidence that the content addresses that pillar.

2. **Semantic Cohesion and Chunk Boundaries**
   Prioritize keeping all semantically related content under the same pillar together per page. Group:
   - Multiple sentences, metrics, tables, lists, or arguments
   - Descriptions of multiple people, entities, or examples
   - All supporting context that explains the same pillar concept
   Never split content that supports the same pillar concept. Minor variations, subtopics, or different examples should remain in the same chunk. Only create a new chunk when the **pillar or primary business question changes significantly**, i.e., a genuine shift in analytical focus occurs.
3. **Dominant Analytical Focus**
   When content contains multiple signals or metrics, assign the chunk to the pillar with the dominant analytical focus. Supporting context from other domains does not change the pillar assignment.
4. **Metric Ownership Rule**
   Core financial metrics (revenue, margin, EBITDA) default to financial_health UNLESS explicitly framed as drivers of another pillar outcome. Metrics that explain another outcome belong to the pillar of that explained outcome, not their default domain.
5. **Tables, Lists, and Entity Handling**
   Keep all tables, lists, and their explanations together in the same chunk. Do not split metrics, arguments, or multiple entity/person descriptions across chunks unless they belong to a different pillar. Multiple examples, individual profiles, or subtopics supporting the same pillar should remain in a single chunk.
6. **Uncertainty and "General" Pillar**
   When uncertain, reduce confidence_score below 0.7 rather than force-fit. Use "general" only when no pillar fits with >50% confidence.
7. **Confidence Scoring**
   Assign a confidence score (0.0-1.0) based on certainty:
   - 0.9-1.0: Explicit value clearly stated, pillar assignment obvious
   - 0.7-0.89: Clear statement, minor context needed
   - 0.5-0.69: Reasonable interpretation, some ambiguity
   - Below 0.5: Highly uncertain — consider using "general" pillar or skip
   Confidence scores should reflect how strongly the chunk supports the assigned pillar, not just the presence of metrics.

**EXTRACTION STANDARDS**
- Extract ONLY information explicitly stated — never infer, estimate, or generate data
- Preserve exact metric names, values, units, and time periods
- Tables: Extract ALL rows, columns, headers, and values
- Charts: Describe only visible data points and axis labels
- Never interpolate or estimate missing data points

**DO NOT**
1. Include anything you cannot see in the document
2. Generate plausible-sounding metrics not explicitly stated
3. Complete partial sentences with assumed information
4. Force-fit content to a pillar when uncertain — reduce confidence_score instead
5. Return chunks for empty pages — return empty chunks array
6. Split metrics, tables, or arguments across multiple chunks

**OUTPUT FORMAT**
Respond with ONLY a valid JSON object. No markdown. No explanation. No text outside JSON.

{{{{
  "chunks": [
    {{{{
      "content": "Exact text extracted from document",
      "summary": "Summarize key metrics, insights, or main point of the chunk in 1–2 sentences.",
      "pillar": "pillar_name",
      "chunk_type": "text",
      "confidence_score": [0.0-1.0],
      "metadata": {{{{
        "section_title": "Section heading if visible",
        "data_type": "metrics",
        "has_metrics": true,
        "time_period": "Exact period as stated in document (e.g., FY, Q1-Q4, month, date range), null if not mentioned",
        "key_entities": ["Company names", "Product names", "Person names if relevant"]
      }}}}
    }}}}
  ],
  "page_summary": "Brief factual summary of page content",
  "page_type": "title | content | financial | chart | table | mixed"
}}}}"""

    def _get_connector_prompt(
        self,
        entity_type: str,
        context: dict,
        pillar_list: str
    ) -> str:
        """Get connector aggregation prompt"""
        connector_type = context.get('connector_type', 'connector')
        total_records = context.get('total_records', 0)

        # Get entity-specific instructions
        entity_instructions = self._get_entity_instructions(entity_type)

        return f"""You are a financial data analyst creating BDE insights from {connector_type.upper()} data.

## Entity Type: {entity_type}
## Total Records in Group: {{record_count}}
## Time Period: {{period_key}}

## BDE Pillars:
{pillar_list}

## CRITICAL INSTRUCTION - AGGREGATION REQUIRED:
You are analyzing a GROUP of {entity_type} records. DO NOT create one chunk per record.
Instead, create 1-3 INSIGHT CHUNKS that summarize the entire group.

{entity_instructions}

## Output Format:
You MUST respond with ONLY a raw JSON object. Do NOT wrap it in markdown code blocks.

{{{{
  "chunks": [
    {{{{
      "content": "Detailed natural language insight (2-4 sentences with specific numbers)",
      "summary": "One sentence summary optimized for search",
      "pillar": "financial_health|customer_health|gtm_engine|product_technical|operational_maturity|leadership_transition|ecosystem_dependency|service_software_ratio|general",
      "chunk_type": "aggregated_summary|trend_analysis|segment_analysis|comparison",
      "confidence_score": 0.9,
      "aggregation_type": "summary|trend|segment|comparison",
      "entity_name": "Descriptive name for this insight (e.g., 'Q4 2024 Revenue Summary')",
      "metadata": {{{{
        "period": "2024-Q4",
        "record_count": 85,
        "total_amount": 450000,
        "key_metrics": {{{{"avg_value": 5294, "growth_rate": 0.12}}}}
      }}}}
    }}}}
  ],
  "period_summary": "Brief summary of this data period"
}}}}

CRITICAL RULES:
- Create 1-3 insight chunks MAX, not one per record
- Include specific numbers and percentages
- Focus on what matters for due diligence
- Be factual and objective"""

    def _get_entity_instructions(self, entity_type: str) -> str:
        """Get entity-specific chunking instructions"""
        instructions = {
            'invoice': """For INVOICES, create these types of insight chunks:
1. REVENUE SUMMARY: Total revenue, average invoice value, invoice count for the period
2. CUSTOMER CONCENTRATION: Top customers by revenue, % of total, concentration risk
3. TREND ANALYSIS: Compare to previous period if patterns visible, identify growth/decline

Example good chunk:
"In Q4 2024, the company generated $450,000 across 85 invoices (avg $5,294).
Top 3 customers (Acme Corp $120K, Beta Inc $85K, Gamma LLC $65K) represent 60% of revenue,
indicating high concentration risk. Payment terms average Net-30."
""",
            'customer': """For CUSTOMERS, create these types of insight chunks:
1. CUSTOMER BASE SUMMARY: Total customers, active vs inactive, new signups, churned customers
2. RETENTION METRICS: Renewal rate, churn rate, customer retention percentage
3. SEGMENT ANALYSIS: Distribution by size/industry/geography if available
4. HEALTH INDICATORS: Outstanding balances, payment behavior patterns, at-risk customers

CRITICAL METRICS TO EXTRACT:
- TotalCustomers: Total number of customers in the system
- ActiveCustomers: Number of currently active customers
- NewSignups: New customers added in the period
- ChurnedCustomers: Customers lost/churned in the period
- RenewalRate: Percentage of customers who renewed

Example good chunk:
"The company has 145 total customers, with 128 active (88% retention rate).
In the last quarter, 12 new customers signed up while 5 churned (4% churn rate).
Renewal rate is 92%. Average customer balance is $12,500. Top 10 customers
represent 65% of total AR. Most customers are in manufacturing (45%) and
distribution (30%) sectors."
""",
            'profit_loss': """For PROFIT & LOSS reports, create these types of insight chunks:
1. FINANCIAL PERFORMANCE: Revenue, gross profit, EBITDA, net income for period
2. EXPENSE ANALYSIS: Major expense categories, unusual items, trends
3. MARGIN ANALYSIS: Gross margin %, operating margin %, comparison to benchmarks
4. REVENUE COMPOSITION: Recurring vs one-time, by product/service category

Example good chunk:
"For FY2024, total revenue was $2.4M with gross margin of 68% ($1.63M gross profit).
Operating expenses totaled $1.1M (46% of revenue), resulting in EBITDA of $530K (22% margin).
Largest expense categories: Payroll 55%, Software/Tools 15%, Marketing 12%."
""",
            'balance_sheet': """For BALANCE SHEET, create these types of insight chunks:
1. ASSET SUMMARY: Total assets, current vs non-current, key asset categories
2. LIABILITY SUMMARY: Total liabilities, current vs long-term, debt levels
3. WORKING CAPITAL: Current ratio, quick ratio, cash position
4. EQUITY ANALYSIS: Retained earnings, equity trends

Example good chunk:
"As of Dec 2024, total assets are $1.8M (Current: $1.2M, Non-current: $600K).
Cash position is $450K with AR of $380K. Total liabilities are $650K, mostly
current ($520K). Working capital is $680K with current ratio of 2.3x."
""",
            'vendor': """For VENDORS, create these types of insight chunks:
1. VENDOR SUMMARY: Total vendors, active count, spend distribution
2. CONCENTRATION ANALYSIS: Top vendors by spend, dependency risk
3. CATEGORY BREAKDOWN: Spend by vendor category/type
""",
            'bill': """For BILLS/EXPENSES, create these types of insight chunks:
1. EXPENSE SUMMARY: Total spend, bill count, average bill size for period
2. VENDOR DISTRIBUTION: Top vendors by spend amount
3. CATEGORY ANALYSIS: Spend by expense category, trends
""",
            'payment': """For PAYMENTS, create these types of insight chunks:
1. PAYMENT SUMMARY: Total payments, count, average payment size
2. PAYMENT PATTERNS: Timing patterns, early/late payment trends
3. CASH FLOW IMPACT: Cash outflow patterns by period
""",
            'item': """For ITEMS/PRODUCTS, create these types of insight chunks:
1. PRODUCT CATALOG: Total items, active count, categories
2. PRICING ANALYSIS: Price ranges, average prices by category
3. INVENTORY STATUS: Stock levels if available, turnover indicators
""",
            'account': """For CHART OF ACCOUNTS, create these types of insight chunks:
1. ACCOUNT STRUCTURE: Total accounts, breakdown by type (Asset, Liability, Equity, Revenue, Expense)
2. BALANCE SUMMARY: Key balances by account type, significant accounts
3. COMPLEXITY INDICATOR: Account hierarchy depth, custom accounts vs standard

Example good chunk:
"The company has 85 accounts in their chart of accounts: 22 Asset, 15 Liability, 8 Equity,
12 Revenue, 28 Expense accounts. Key balances include Cash ($450K), AR ($380K),
AP ($220K). The chart structure follows standard QuickBooks setup with minimal customization."
""",
            'employee': """For EMPLOYEES, create these types of insight chunks:
1. WORKFORCE SUMMARY: Total employees, active count, recent hires/terminations
2. TEAM STRUCTURE: Department distribution, role types if available
3. OPERATIONAL CONTEXT: Employee count relative to revenue (revenue per employee)

Example good chunk:
"The company has 24 employees (22 active, 2 inactive). Team composition includes
8 in Operations, 6 in Sales, 5 in Engineering, 3 in Admin, 2 in Finance.
With $2.4M annual revenue, revenue per employee is approximately $109K."
""",
            'cash_flow': """For CASH FLOW STATEMENT, create these types of insight chunks:
1. CASH FLOW SUMMARY: Net cash from operations, investing, financing activities
2. LIQUIDITY ANALYSIS: Cash generation ability, burn rate if negative
3. INVESTMENT PATTERNS: CapEx spending, debt payments, financing activities

Example good chunk:
"For FY2024, operating cash flow was $380K (positive), driven by $530K net income
adjusted for $150K non-cash depreciation. Investing activities used ($85K) for
equipment purchases. Net change in cash was $295K, ending cash balance $450K."
""",
            'ar_aging': """For AR AGING REPORT, create these types of insight chunks:
1. RECEIVABLES SUMMARY: Total AR, aging breakdown (current, 1-30, 31-60, 61-90, 90+)
2. COLLECTION RISK: Percentage overdue, high-risk amounts, concentration in aging buckets
3. DSO INDICATOR: Days Sales Outstanding if calculable, collection efficiency

Example good chunk:
"Total AR is $380K with aging: Current $285K (75%), 1-30 days $52K (14%),
31-60 days $28K (7%), 61-90 days $10K (3%), 90+ days $5K (1%).
Low concentration in aging buckets suggests healthy collection practices.
Estimated DSO is approximately 42 days."
""",
            'ap_aging': """For AP AGING REPORT, create these types of insight chunks:
1. PAYABLES SUMMARY: Total AP, aging breakdown by period
2. PAYMENT OBLIGATIONS: Amounts due soon, overdue amounts
3. VENDOR RELATIONSHIP: Payment patterns, any consistently late payments

Example good chunk:
"Total AP is $220K with aging: Current $180K (82%), 1-30 days $28K (13%),
31-60 days $8K (4%), 61-90 days $4K (2%). Most payables are current,
indicating good vendor relationship management. No significant overdue amounts."
""",
            'customer_income': """For INCOME BY CUSTOMER REPORT, create these types of insight chunks:
1. REVENUE CONCENTRATION: Top customers by revenue, % of total revenue
2. CUSTOMER CONTRIBUTION: Revenue tiers (how many customers make up 80% of revenue)
3. RISK ANALYSIS: Customer dependency, diversification level

Example good chunk:
"Customer revenue concentration analysis shows top 5 customers generate 62% of
total revenue ($1.49M of $2.4M). Largest customer (Acme Corp) represents 18%.
Top 20% of customers (29 of 145) generate 85% of revenue. Moderate concentration
risk - loss of top customer would impact ~18% of revenue."
""",
        }

        return instructions.get(entity_type, """For this data, create insight chunks that:
1. SUMMARIZE the key metrics and totals
2. IDENTIFY patterns, concentrations, or risks
3. HIGHLIGHT anything relevant for due diligence

Focus on creating actionable insights, not raw data descriptions.""")


# Singleton instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get singleton PromptManager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
