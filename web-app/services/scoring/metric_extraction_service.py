"""
Stage 1: Metric Extraction Service
Extracts structured metrics (signals) from document chunks using LLM.
"""
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from sqlmodel import Session, select
from database.models.scoring import CompanyMetric
from database.models.document import DocumentChunk, BDEPillar
from database.models.connector import ConnectorChunk, MetricSourceType, METRIC_SOURCE_PRIORITY
from services.llm_client import get_llm_client
from utils.logger import get_logger

logger = get_logger(__name__)


class MetricExtractionService:
    """
    Extracts structured metrics (signals) from document chunks.
    Metrics are INPUTS to scoring (extracted BEFORE evaluation).

    Based on official BDE Pillar Signal Lists.
    """

    # Official BDE Pillar-Specific Signals from rubric documents - COMPLETE LIST
    PILLAR_METRIC_DEFINITIONS = {
        "financial_health": [
            # Core Revenue Metrics
            {"name": "ARR", "type": "numeric", "unit": "$", "description": "Annual recurring revenue baseline"},
            {"name": "MRR", "type": "numeric", "unit": "$", "description": "Monthly recurring revenue"},
            {"name": "RecurringRevenuePct", "type": "percentage", "unit": "%", "description": "% of revenue that is recurring vs one-time (GREEN >50%, YELLOW 20-50%, RED <20%)"},
            {"name": "RevenueGrowthRateYoY", "type": "percentage", "unit": "%", "description": "Top-line momentum year-over-year"},
            # Retention Metrics (cross-pillar with customer_health)
            {"name": "GRR", "type": "percentage", "unit": "%", "description": "Gross Revenue Retention (GREEN >90%, YELLOW 80-90%, RED <80%)"},
            {"name": "NRR", "type": "percentage", "unit": "%", "description": "Net Revenue Retention with expansion (GREEN >110%, YELLOW ~100%, RED <95%)"},
            {"name": "ChurnRatePct", "type": "percentage", "unit": "%", "description": "Annual logo or revenue churn rate"},
            {"name": "LogoChurnRatePct", "type": "percentage", "unit": "%", "description": "Customer count churn rate"},
            {"name": "RevenueChurnRatePct", "type": "percentage", "unit": "%", "description": "Revenue-based churn rate"},
            # Margin Metrics
            {"name": "GrossMarginPct", "type": "percentage", "unit": "%", "description": "Product vs services efficiency (software target 70-90%)"},
            {"name": "EBITDA_MarginPct", "type": "percentage", "unit": "%", "description": "Profitability signal (GREEN 15-25%, YELLOW 5-15%, RED <5%)"},
            # Revenue Mix (cross-pillar with service_software_ratio)
            {"name": "SoftwareRevenuePct", "type": "percentage", "unit": "%", "description": "Software/SaaS revenue % (GREEN 70-90%+, YELLOW 40-60%, RED <40%)"},
            {"name": "ServicesRevenuePct", "type": "percentage", "unit": "%", "description": "Professional services revenue %"},
            {"name": "ServicesGrossMarginPct", "type": "percentage", "unit": "%", "description": "Professional services margin (target 30-50%)"},
            # Cash & Capital Metrics
            {"name": "BurnRateMonthly", "type": "numeric", "unit": "$/month", "description": "Cash consumption rate"},
            {"name": "RunwayMonths", "type": "numeric", "unit": "months", "description": "Survivability without capital"},
            {"name": "CashConversionCycle", "type": "numeric", "unit": "days", "description": "Days from cash out to cash in"},
            {"name": "WorkingCapitalNeeds", "type": "numeric", "unit": "$", "description": "Capital required for operations"},
            # Concentration & Risk Metrics
            {"name": "TopCustomerConcentrationPct", "type": "percentage", "unit": "%", "description": "Top 3 customer revenue % (GREEN <25%, YELLOW 25-40%, RED >40%)"},
            {"name": "Top10CustomerConcentrationPct", "type": "percentage", "unit": "%", "description": "Top 10 customer revenue concentration"},
            # AR & Collections
            {"name": "ARDays", "type": "numeric", "unit": "days", "description": "Accounts receivable days (GREEN <45, YELLOW 60-90, RED >90)"},
            {"name": "ARAging90PlusPct", "type": "percentage", "unit": "%", "description": "% of AR over 90 days - collection risk"},
            # Pricing & Contract Metrics
            {"name": "PricingGrowthPct", "type": "percentage", "unit": "%", "description": "Annual pricing increase % (GREEN >5%)"},
            {"name": "ContractLengthAvgMonths", "type": "numeric", "unit": "months", "description": "Average contract length - stickiness indicator"},
            {"name": "RemainingPerformanceObligations", "type": "numeric", "unit": "$", "description": "Contracted future revenue"},
            # Qualitative
            {"name": "RevenuePredictabilityNotes", "type": "text", "unit": "", "description": "Volatility, lumpiness, seasonality indicators"},
            {"name": "FinancialHygieneNotes", "type": "text", "unit": "", "description": "Clean books, audit readiness, GAAP compliance"},
            # Account Lists (cross-pillar with customer_health - relevant for revenue concentration/risk)
            {"name": "TopAccountsList", "type": "json", "unit": "", "description": "List of top accounts from any table showing accounts/customers ranked by revenue, value, or importance. Extract ALL columns as-is using snake_case keys. Example: [{account_name: string, revenue: number, ...any other columns}]. Include all rows found."},
            {"name": "AtRiskAccountsList", "type": "json", "unit": "", "description": "List of at-risk accounts from any table showing churning, declining, or problematic accounts. Extract ALL columns as-is using snake_case keys. Example: [{account_name: string, risk_reason: string, ...any other columns}]. Include all rows found."},
            # Time-Series / Trend Metrics (extracted from monthly/quarterly/yearly reports)
            {"name": "RevenueTrend", "type": "json", "unit": "$", "description": "Revenue over time. Extract when monthly, quarterly, or yearly revenue data is available. Format: {type: 'time_series', frequency: 'monthly'|'quarterly'|'yearly', data: {period_label: numeric_value, ...}, total: number}. Include ALL periods found."},
            {"name": "CostOfSalesTrend", "type": "json", "unit": "$", "description": "Cost of sales/COGS over time. Format: {type: 'time_series', frequency: 'monthly'|'quarterly'|'yearly', data: {period_label: numeric_value, ...}, total: number}"},
            {"name": "GrossProfitTrend", "type": "json", "unit": "$", "description": "Gross profit over time (Revenue - COGS). Format: {type: 'time_series', frequency: 'monthly'|'quarterly'|'yearly', data: {period_label: numeric_value, ...}, total: number}"},
            {"name": "OperatingExpensesTrend", "type": "json", "unit": "$", "description": "Total operating expenses over time. Format: {type: 'time_series', frequency: 'monthly'|'quarterly'|'yearly', data: {period_label: numeric_value, ...}, total: number}"},
            {"name": "NetIncomeTrend", "type": "json", "unit": "$", "description": "Net income/loss over time. Format: {type: 'time_series', frequency: 'monthly'|'quarterly'|'yearly', data: {period_label: numeric_value, ...}, total: number}"},
            {"name": "GrossMarginTrend", "type": "json", "unit": "%", "description": "Gross margin percentage over time. Format: {type: 'time_series', frequency: 'monthly'|'quarterly'|'yearly', data: {period_label: numeric_value, ...}}. Calculate from gross profit / revenue for each period if not directly stated."},
            {"name": "RevenueByCategory", "type": "json", "unit": "$", "description": "Revenue broken down by category/line item with time-series for each. Format: {type: 'categorized_time_series', categories: {category_name: {data: {period: value, ...}, total: number}, ...}}. Extract when multiple revenue line items have periodic data."},
            {"name": "ExpenseByCategory", "type": "json", "unit": "$", "description": "Expenses broken down by category with time-series for each. Format: {type: 'categorized_time_series', categories: {category_name: {data: {period: value, ...}, total: number}, ...}}. Extract when multiple expense line items have periodic data."},
        ],
        "gtm_engine": [
            # Revenue Metrics (cross-pillar with financial_health)
            {"name": "ARR", "type": "numeric", "unit": "$", "description": "Annual recurring revenue baseline"},
            {"name": "MRR", "type": "numeric", "unit": "$", "description": "Monthly recurring revenue"},
            # ICP & Targeting
            {"name": "ICPDefined", "type": "boolean", "unit": "", "description": "Clear ICP definition exists with sub-vertical, ERP version, module dependency"},
            {"name": "ICPClarityScore", "type": "ordinal", "unit": "1-5", "description": "How well-defined is the ideal customer profile"},
            # Pipeline Metrics
            {"name": "PipelineCoverageRatio", "type": "numeric", "unit": "x", "description": "Pipeline ÷ quota (GREEN 3-5x, YELLOW inconsistent, RED <2x)"},
            {"name": "PipelineByStage", "type": "json", "unit": "", "description": "Distribution across sales stages"},
            {"name": "WeightedPipelineValue", "type": "numeric", "unit": "$", "description": "Probability-weighted pipeline value"},
            # Conversion Funnel Metrics
            {"name": "LeadToMQLPct", "type": "percentage", "unit": "%", "description": "Lead to Marketing Qualified Lead conversion"},
            {"name": "MQLToSQLPct", "type": "percentage", "unit": "%", "description": "MQL to Sales Qualified Lead conversion"},
            {"name": "SQLToClosePct", "type": "percentage", "unit": "%", "description": "SQL to Closed Won conversion"},
            {"name": "WinRatePct", "type": "percentage", "unit": "%", "description": "Deals won ÷ deals closed (won + lost)"},
            {"name": "CloseRatePct", "type": "percentage", "unit": "%", "description": "Opportunities closed ÷ total opportunities"},
            # Sales Efficiency
            {"name": "AvgSalesCycleDays", "type": "numeric", "unit": "days", "description": "Average days from opportunity to close"},
            {"name": "AvgDealSize", "type": "numeric", "unit": "$", "description": "Average contract value - monetization power"},
            # Unit Economics (primary GTM metrics, cross-pillar with customer_health)
            {"name": "CAC", "type": "numeric", "unit": "$", "description": "Customer Acquisition Cost - total sales & marketing spend ÷ new customers (GREEN <1/3 LTV, YELLOW 1/3-1/2 LTV, RED >1/2 LTV)"},
            {"name": "CACPaybackMonths", "type": "numeric", "unit": "months", "description": "Months to recover CAC (GREEN <12, YELLOW 12-18, RED >18)"},
            {"name": "LTVtoCACRatio", "type": "numeric", "unit": "x", "description": "LTV ÷ CAC ratio (GREEN >3x, YELLOW 2-3x, RED <2x)"},
            # Forecasting
            {"name": "ForecastAccuracyPct", "type": "percentage", "unit": "%", "description": "Forecast vs actual variance (GREEN ±10-15%, YELLOW 20-40%, RED guesswork)"},
            {"name": "ForecastVariancePct", "type": "percentage", "unit": "%", "description": "Historical variance from forecasts"},
            # Channel & Lead Gen
            {"name": "InboundLeadVelocity", "type": "numeric", "unit": "leads/month", "description": "Monthly inbound lead volume"},
            {"name": "OutboundCapabilityScore", "type": "ordinal", "unit": "1-5", "description": "Outbound sales capability maturity"},
            {"name": "InboundOutboundMix", "type": "json", "unit": "", "description": "Channel balance - inbound vs outbound vs partner"},
            {"name": "PartnerSourcedRevenuePct", "type": "percentage", "unit": "%", "description": "Revenue from partner referrals"},
            {"name": "PartnerReferralVolume", "type": "numeric", "unit": "referrals/month", "description": "Monthly partner referral count"},
            # Process & Discipline
            {"name": "CRMDisciplineScore", "type": "ordinal", "unit": "1-5", "description": "CRM hygiene & usage discipline"},
            {"name": "SalesPlaybookExists", "type": "boolean", "unit": "", "description": "Documented sales playbook available"},
            {"name": "SalesRepRampTimeDays", "type": "numeric", "unit": "days", "description": "Time for new rep to reach productivity"},
            # Deal Lists (JSON arrays for analytics cards)
            {"name": "RecentDealsList", "type": "json", "unit": "", "description": "List of deals from any table showing deals, opportunities, or sales. Extract ALL columns as-is using snake_case keys. Example: [{deal_name: string, value: number, ...any other columns}]. Include all rows found."},
        ],
        "customer_health": [
            # Customer Base Metrics
            {"name": "TotalCustomers", "type": "numeric", "unit": "", "description": "Total number of customers"},
            {"name": "ActiveCustomers", "type": "numeric", "unit": "", "description": "Number of active customers"},
            {"name": "NewSignups", "type": "numeric", "unit": "", "description": "New customer signups in period (monthly/quarterly)"},
            {"name": "ChurnedCustomers", "type": "numeric", "unit": "", "description": "Number of customers churned in period"},
            {"name": "RenewalRate", "type": "percentage", "unit": "%", "description": "Customer renewal rate (% of customers who renewed)"},
            # Retention Metrics
            {"name": "GRR", "type": "percentage", "unit": "%", "description": "Gross Revenue Retention (GREEN >90%, YELLOW 80-90%, RED <80%)"},
            {"name": "NRR", "type": "percentage", "unit": "%", "description": "Net Revenue Retention with expansion (GREEN >110%, YELLOW ~100%, RED <95%)"},
            {"name": "ChurnRatePct", "type": "percentage", "unit": "%", "description": "Annual logo or revenue churn rate"},
            {"name": "LogoChurnRatePct", "type": "percentage", "unit": "%", "description": "Customer count churn rate"},
            {"name": "RevenueChurnRatePct", "type": "percentage", "unit": "%", "description": "Revenue-based churn rate"},
            # Expansion Metrics
            {"name": "ExpansionRevenuePct", "type": "percentage", "unit": "%", "description": "Upsell / cross-sell as % of total revenue"},
            {"name": "MultiModulePenetrationPct", "type": "percentage", "unit": "%", "description": "% of customers using multiple modules"},
            {"name": "AddOnAttachmentRatePct", "type": "percentage", "unit": "%", "description": "% of customers buying add-ons"},
            # Customer Value Metrics (cross-pillar with gtm_engine for LTV:CAC)
            {"name": "LTV", "type": "numeric", "unit": "$", "description": "Customer Lifetime Value - average revenue per customer × gross margin × average customer lifespan"},
            {"name": "ARPU", "type": "numeric", "unit": "$", "description": "Average Revenue Per User/Account"},
            {"name": "ARPUGrowthPct", "type": "percentage", "unit": "%", "description": "ARPU growth rate year-over-year"},
            {"name": "LTVtoCACRatio", "type": "numeric", "unit": "x", "description": "LTV ÷ CAC ratio (GREEN >3x, YELLOW 2-3x, RED <2x) - cross-pillar with gtm_engine"},
            {"name": "CAC", "type": "numeric", "unit": "$", "description": "Customer Acquisition Cost (cross-pillar with gtm_engine for LTV:CAC analysis)"},
            # Concentration Metrics (cross-pillar with financial_health)
            {"name": "TopCustomerConcentrationPct", "type": "percentage", "unit": "%", "description": "Top 3 customer revenue % (GREEN <25%, YELLOW 25-40%, RED >40%)"},
            {"name": "Top3CustomerConcentrationPct", "type": "percentage", "unit": "%", "description": "Top 3 customers revenue % (GREEN <20%, YELLOW 20-35%, RED >35-40%)"},
            {"name": "Top10CustomerConcentrationPct", "type": "percentage", "unit": "%", "description": "Top 10 customer revenue concentration"},
            {"name": "CustomerConcentrationPct", "type": "percentage", "unit": "%", "description": "General customer dependency risk"},
            {"name": "AtRiskCustomerCount", "type": "numeric", "unit": "", "description": "Customers showing churn signals"},
            {"name": "AtRiskRevenuePct", "type": "percentage", "unit": "%", "description": "Revenue at risk from at-risk customers"},
            # Satisfaction & Sentiment
            {"name": "NPS", "type": "numeric", "unit": "", "description": "Net Promoter Score (-100 to 100)"},
            {"name": "CSAT", "type": "numeric", "unit": "", "description": "Customer Satisfaction Score (1-5 or 1-10)"},
            {"name": "ERPMarketplaceRating", "type": "numeric", "unit": "stars", "description": "Rating on ERP marketplace (1-5 stars)"},
            {"name": "ERPMarketplaceReviewCount", "type": "numeric", "unit": "", "description": "Number of marketplace reviews"},
            {"name": "CustomerSentimentNotes", "type": "text", "unit": "", "description": "Qualitative customer sentiment indicators"},
            # Adoption & Usage
            {"name": "ActiveUserPct", "type": "percentage", "unit": "%", "description": "% of licensed users actively logging in"},
            {"name": "FeatureAdoptionDepth", "type": "ordinal", "unit": "Low/Med/High", "description": "Depth of feature usage - light vs deep"},
            {"name": "AdoptionIndicators", "type": "json", "unit": "", "description": "Usage, engagement, module penetration signals"},
            # Support Metrics
            {"name": "SupportTicketVolume", "type": "numeric", "unit": "tickets/month", "description": "Monthly support ticket volume"},
            {"name": "TicketBacklogCount", "type": "numeric", "unit": "", "description": "Open ticket backlog size"},
            {"name": "SupportInteractionsPerUser", "type": "numeric", "unit": "", "description": "Support burden per user"},
            {"name": "TicketResolutionTimeDays", "type": "numeric", "unit": "days", "description": "Average ticket resolution time"},
            # Process
            {"name": "RenewalProcessDefined", "type": "boolean", "unit": "", "description": "Formal renewal process exists"},
            {"name": "CSSegmentationExists", "type": "boolean", "unit": "", "description": "Customer success tiering/segmentation"},
            # Account Lists (JSON arrays for analytics cards)
            {"name": "TopAccountsList", "type": "json", "unit": "", "description": "List of top accounts from any table showing accounts/customers ranked by revenue, value, or importance. Extract ALL columns as-is using snake_case keys. Example: [{account_name: string, revenue: number, ...any other columns}]. Include all rows found."},
            {"name": "AtRiskAccountsList", "type": "json", "unit": "", "description": "List of at-risk accounts from any table showing churning, declining, or problematic accounts. Extract ALL columns as-is using snake_case keys. Example: [{account_name: string, risk_reason: string, ...any other columns}]. Include all rows found."},
            # Cohort Retention & Churn Time-Series (extracted from monthly/quarterly reports)
            {"name": "CohortRetentionTrend", "type": "json", "unit": "%", "description": "Customer retention rate over time (monthly or quarterly). Extract when periodic retention/renewal rate data is available. Format: {type: 'time_series', frequency: 'monthly'|'quarterly', data: {period_label: retention_pct, ...}}. Values are percentages (e.g. 95.0 means 95%). Include ALL periods found. If only absolute counts are available, calculate retention % as (customers_end / customers_start) * 100."},
            {"name": "ChurnTrend", "type": "json", "unit": "%", "description": "Customer churn rate over time (monthly or quarterly). Extract when periodic churn data is available. Format: {type: 'time_series', frequency: 'monthly'|'quarterly', data: {period_label: churn_pct, ...}}. Values are percentages (e.g. 5.0 means 5% churn). Include ALL periods found. Can be derived as 100 - retention_pct if retention is available but churn is not."},
            {"name": "CustomerCountTrend", "type": "json", "unit": "", "description": "Total customer count over time. Extract when periodic customer count data is available. Format: {type: 'time_series', frequency: 'monthly'|'quarterly', data: {period_label: count, ...}}. Useful for cohort analysis — shows absolute customer base changes over time."},
            {"name": "NewCustomersTrend", "type": "json", "unit": "", "description": "New customers acquired per period. Format: {type: 'time_series', frequency: 'monthly'|'quarterly', data: {period_label: count, ...}}. Shows customer acquisition velocity over time."},
            {"name": "ChurnedCustomersTrend", "type": "json", "unit": "", "description": "Customers lost/churned per period. Format: {type: 'time_series', frequency: 'monthly'|'quarterly', data: {period_label: count, ...}}. Shows churn velocity over time."},
        ],
        "product_technical": [
            # Reliability & Performance
            {"name": "UptimePct", "type": "percentage", "unit": "%", "description": "Platform uptime (target 99.9%+)"},
            {"name": "AvgResponseTimeMs", "type": "numeric", "unit": "ms", "description": "Average API/page response time"},
            {"name": "ErrorRatePct", "type": "percentage", "unit": "%", "description": "Error rate - stability indicator"},
            {"name": "IncidentFrequency", "type": "numeric", "unit": "per month", "description": "Production incidents per month"},
            # Architecture & Code Quality
            {"name": "ArchitectureType", "type": "enum", "unit": "Modular/Mixed/Monolithic", "description": "Code architecture pattern"},
            {"name": "TechDebtLevel", "type": "ordinal", "unit": "Low/Med/High", "description": "Technical debt burden"},
            {"name": "CodeDocumentationQuality", "type": "ordinal", "unit": "1-5", "description": "Code and system documentation quality"},
            {"name": "TestCoveragePct", "type": "percentage", "unit": "%", "description": "Automated test coverage percentage"},
            # Integration & APIs
            {"name": "APIType", "type": "enum", "unit": "REST/GraphQL/SOAP/None", "description": "Primary API architecture"},
            {"name": "APIDocumentationExists", "type": "boolean", "unit": "", "description": "API documentation available"},
            {"name": "ERPVersionCompatibility", "type": "json", "unit": "", "description": "Supported ERP versions (v10, v11, cloud)"},
            {"name": "IntegrationFragilityScore", "type": "ordinal", "unit": "1-5", "description": "How often integrations break (1=fragile, 5=robust)"},
            # Scalability
            {"name": "MultiTenantCapable", "type": "boolean", "unit": "", "description": "True multi-tenant architecture"},
            {"name": "ScalabilityConstraints", "type": "text", "unit": "", "description": "Known scaling limitations"},
            {"name": "InfrastructureType", "type": "enum", "unit": "Cloud/Hybrid/OnPrem", "description": "Infrastructure deployment model"},
            # Security & Compliance
            {"name": "SecurityCompliance", "type": "enum", "unit": "SOC2/ISO27001/Both/None", "description": "Security certifications"},
            {"name": "PenTestingDone", "type": "boolean", "unit": "", "description": "Penetration testing completed"},
            {"name": "PenTestResults", "type": "text", "unit": "", "description": "Penetration test findings summary"},
            {"name": "EncryptionAtRest", "type": "boolean", "unit": "", "description": "Data encrypted at rest"},
            {"name": "EncryptionInTransit", "type": "boolean", "unit": "", "description": "Data encrypted in transit"},
            {"name": "DRPlanExists", "type": "boolean", "unit": "", "description": "Disaster recovery plan documented"},
            # Engineering Team
            {"name": "DeployFrequency", "type": "numeric", "unit": "per month", "description": "Release frequency - engineering velocity"},
            {"name": "BusFactorRisk", "type": "ordinal", "unit": "None/Some/High", "description": "Single point of failure developer risk"},
            {"name": "EngineeringTeamSize", "type": "numeric", "unit": "", "description": "Number of engineers"},
            {"name": "CodeReviewPractice", "type": "boolean", "unit": "", "description": "Code review process in place"},
            {"name": "QAAutomationLevel", "type": "ordinal", "unit": "1-5", "description": "QA automation maturity"},
            # Roadmap
            {"name": "RoadmapDeliveryPct", "type": "percentage", "unit": "%", "description": "% of roadmap delivered on time (RED <50%)"},
            {"name": "RoadmapRealism", "type": "ordinal", "unit": "1-5", "description": "Roadmap planning realism"},
            {"name": "InfraModernityScore", "type": "ordinal", "unit": "1-5", "description": "Cloud, CI/CD, observability maturity"},
        ],
        "operational_maturity": [
            # Process Documentation
            {"name": "CoreProcessesDocumented", "type": "boolean", "unit": "", "description": "SOPs documented for core functions"},
            {"name": "SOPCoveragePct", "type": "percentage", "unit": "%", "description": "% of functions with documented SOPs"},
            {"name": "InternalWikiExists", "type": "boolean", "unit": "", "description": "Knowledge base or wiki available"},
            # Operating Cadence
            {"name": "WeeklyLeadershipReview", "type": "boolean", "unit": "", "description": "Weekly leadership review meetings"},
            {"name": "MonthlyKPIReview", "type": "boolean", "unit": "", "description": "Monthly KPI review discipline"},
            {"name": "QuarterlyPlanningCadence", "type": "boolean", "unit": "", "description": "Quarterly planning rhythm exists"},
            {"name": "CrossFunctionalCadenceScore", "type": "ordinal", "unit": "1-5", "description": "Inter-team alignment maturity"},
            # Systems & Data
            {"name": "SystemsIntegrated", "type": "boolean", "unit": "", "description": "Core systems (CRM, PSA, billing) connected"},
            {"name": "ManualDataReentryRequired", "type": "boolean", "unit": "", "description": "Swivel-chair data re-entry exists"},
            {"name": "CRMDataAccuracyScore", "type": "ordinal", "unit": "1-5", "description": "CRM data quality/accuracy"},
            {"name": "FinancialDataAccuracy", "type": "ordinal", "unit": "1-5", "description": "Financial data reliability"},
            {"name": "RealTimeDashboardsExist", "type": "boolean", "unit": "", "description": "Real-time operational dashboards"},
            # Delivery & Implementation
            {"name": "OnboardingTimeDays", "type": "numeric", "unit": "days", "description": "Average customer onboarding time"},
            {"name": "StandardImplementationPct", "type": "percentage", "unit": "%", "description": "% of implementations that are standard vs custom"},
            {"name": "ImplementationBottlenecks", "type": "text", "unit": "", "description": "Known implementation bottlenecks"},
            {"name": "TimeToValueDays", "type": "numeric", "unit": "days", "description": "Days until customer sees value"},
            # Efficiency Metrics
            {"name": "ServicesGrossMarginPct", "type": "percentage", "unit": "%", "description": "Professional services margin (target 30-50%)"},
            {"name": "ProjectOverrunFrequency", "type": "percentage", "unit": "%", "description": "% of projects that overrun"},
            {"name": "UtilizationRatePct", "type": "percentage", "unit": "%", "description": "Professional services utilization"},
            {"name": "DeliveryDependencyOnIndividuals", "type": "ordinal", "unit": "High/Med/Low", "description": "Key person dependency in delivery"},
            # Support Operations
            {"name": "TicketResolutionTimeAvg", "type": "numeric", "unit": "hours", "description": "Average ticket resolution time"},
            {"name": "SupportBacklogSize", "type": "numeric", "unit": "", "description": "Current support ticket backlog"},
            {"name": "ProactiveVsReactiveCSPct", "type": "percentage", "unit": "%", "description": "% of CS activity that is proactive"},
            # Organizational
            {"name": "RoleClarity", "type": "ordinal", "unit": "1-5", "description": "Role and responsibility clarity"},
            {"name": "HiringProcessDefined", "type": "boolean", "unit": "", "description": "Formal hiring process exists"},
            {"name": "LeadershipBenchDepth", "type": "ordinal", "unit": "1-5", "description": "Backup coverage for key roles"},
            {"name": "InternalToolingMaturity", "type": "ordinal", "unit": "1-5", "description": "Internal tools and automation"},
            # Culture
            {"name": "TeamMorale", "type": "ordinal", "unit": "1-5", "description": "Team morale assessment"},
            {"name": "TurnoverRatePct", "type": "percentage", "unit": "%", "description": "Annual employee turnover"},
            {"name": "MetricsDrivenCulture", "type": "boolean", "unit": "", "description": "Decisions driven by data vs intuition"},
        ],
        "leadership_transition": [
            # Founder Dependency
            {"name": "FounderDailyInvolvementHours", "type": "numeric", "unit": "hours", "description": "Founder hours per day in operations"},
            {"name": "FounderSalesDependencyPct", "type": "percentage", "unit": "%", "description": "% of revenue dependent on founder sales"},
            {"name": "FounderProductDependency", "type": "boolean", "unit": "", "description": "Founder holds product vision/decisions"},
            {"name": "FounderCustomerRelationshipDependency", "type": "boolean", "unit": "", "description": "Key customer relationships with founder only"},
            {"name": "FounderTechnicalKnowledgeDependency", "type": "boolean", "unit": "", "description": "Critical technical knowledge with founder only"},
            {"name": "FounderERPPartnerDependency", "type": "boolean", "unit": "", "description": "ERP partner relationships founder-only"},
            {"name": "FounderPricingDependency", "type": "boolean", "unit": "", "description": "Pricing decisions require founder"},
            {"name": "FounderEscalationDependency", "type": "boolean", "unit": "", "description": "Escalated support requires founder"},
            # Leadership Team
            {"name": "LeadershipTeamSize", "type": "numeric", "unit": "", "description": "Number of leadership team members"},
            {"name": "LeadershipBenchCoverage", "type": "numeric", "unit": "", "description": "Roles with capable backup"},
            {"name": "LeadershipTeamAlignment", "type": "ordinal", "unit": "1-5", "description": "Leadership team cohesion"},
            {"name": "SecondInCommandIdentified", "type": "boolean", "unit": "", "description": "Clear #2 identified"},
            {"name": "FunctionalLeadsCoverage", "type": "json", "unit": "", "description": "Which functions have dedicated leads"},
            # Succession & Transition
            {"name": "SuccessionPlanExists", "type": "boolean", "unit": "", "description": "Documented succession plan"},
            {"name": "FounderExitTimelineDefined", "type": "boolean", "unit": "", "description": "Clear founder exit timeline"},
            {"name": "InterimLeadershipCapable", "type": "boolean", "unit": "", "description": "Team can operate without founder"},
            {"name": "TransitionReadinessScore", "type": "ordinal", "unit": "1-5", "description": "Overall transition readiness"},
            # Knowledge & Decision Making
            {"name": "InstitutionalKnowledgeDocumented", "type": "boolean", "unit": "", "description": "Key knowledge written down vs tribal"},
            {"name": "PricingLogicDocumented", "type": "boolean", "unit": "", "description": "Pricing rationale documented"},
            {"name": "CustomerHistoryAccessible", "type": "boolean", "unit": "", "description": "Customer history in systems vs founder memory"},
            {"name": "DecisionMakingStyle", "type": "enum", "unit": "DataDriven/Mostly/Reactive/Emotional", "description": "Decision-making discipline"},
            {"name": "DecisionCentralizationScore", "type": "ordinal", "unit": "1-5", "description": "How centralized are decisions (1=founder-only, 5=distributed)"},
            # Culture & Relationships
            {"name": "CultureHealthScore", "type": "ordinal", "unit": "1-5", "description": "Organizational culture health"},
            {"name": "PsychologicalSafetyLevel", "type": "ordinal", "unit": "1-5", "description": "Team psychological safety"},
            {"name": "KeyRelationshipsDistributed", "type": "boolean", "unit": "", "description": "Customer/partner relationships held by team"},
            {"name": "ConflictManagementMaturity", "type": "ordinal", "unit": "1-5", "description": "How well team handles conflict"},
            # Founder Psychology
            {"name": "FounderBurnoutSignals", "type": "boolean", "unit": "", "description": "Founder showing burnout signs"},
            {"name": "FounderEmotionalReadiness", "type": "ordinal", "unit": "1-5", "description": "Founder psychological readiness to exit"},
            {"name": "FounderIdentityTiedToBusiness", "type": "boolean", "unit": "", "description": "Founder identity strongly tied to company"},
            {"name": "KeyPersonRiskNotes", "type": "text", "unit": "", "description": "Single points of failure description"},
            # Talent Pipeline
            {"name": "PromotableInternalTalent", "type": "boolean", "unit": "", "description": "Internal candidates for leadership roles"},
            {"name": "RecruitingAbility", "type": "ordinal", "unit": "1-5", "description": "Ability to attract talent"},
        ],
        "ecosystem_dependency": [
            # ERP Revenue Dependency
            {"name": "PrimaryERPDependencyPct", "type": "percentage", "unit": "%", "description": "% revenue tied to primary ERP vendor"},
            {"name": "SingleERPVersionDependencyPct", "type": "percentage", "unit": "%", "description": "% tied to specific ERP version"},
            {"name": "ERPCloudVsOnPremMix", "type": "json", "unit": "", "description": "Customer mix cloud vs on-prem ERP"},
            {"name": "LegacyERPVersionCustomerPct", "type": "percentage", "unit": "%", "description": "% customers on legacy ERP versions"},
            {"name": "CustomersMigrationRequired", "type": "numeric", "unit": "", "description": "Customers needing ERP migration"},
            # Roadmap & Strategic Alignment
            {"name": "ERPRoadmapAligned", "type": "boolean", "unit": "", "description": "ISV roadmap aligned with ERP direction"},
            {"name": "StrategicAdjacencyStatus", "type": "enum", "unit": "Strong/Moderate/Weak/Hostile", "description": "Strategic fit with ERP ecosystem"},
            {"name": "ERPInternalizationRisk", "type": "ordinal", "unit": "Low/Med/High", "description": "Risk of ERP building competing feature"},
            {"name": "ERPAcquisitionActivity", "type": "text", "unit": "", "description": "ERP's acquisition activity in ISV space"},
            # Integration Stability
            {"name": "IntegrationDepthScore", "type": "ordinal", "unit": "1-5", "description": "API depth and integration quality"},
            {"name": "IntegrationFragilityScore", "type": "ordinal", "unit": "1-5", "description": "How often integrations break (1=fragile)"},
            {"name": "ERPUpgradeImpactHistory", "type": "text", "unit": "", "description": "Historical impact of ERP upgrades"},
            {"name": "IntegrationTestingAutomated", "type": "boolean", "unit": "", "description": "Automated testing across ERP versions"},
            {"name": "DeprecatedAPIRisk", "type": "boolean", "unit": "", "description": "Using deprecated ERP APIs"},
            # Partner Relationship
            {"name": "PartnerTierLevel", "type": "enum", "unit": "Gold/Silver/Bronze/None", "description": "ERP partner tier status"},
            {"name": "JointCallsFrequency", "type": "ordinal", "unit": "1-5", "description": "Frequency of joint ERP calls"},
            {"name": "CoSellMotionExists", "type": "boolean", "unit": "", "description": "Active co-selling with ERP"},
            {"name": "ERPCertificationStatus", "type": "boolean", "unit": "", "description": "ISV certified by ERP vendor"},
            {"name": "RoadmapFeedbackPanelMember", "type": "boolean", "unit": "", "description": "ISV on ERP roadmap feedback panel"},
            {"name": "ERPChampionRelationships", "type": "boolean", "unit": "", "description": "Strong relationships with ERP champions"},
            # Marketplace Position
            {"name": "MarketplacePresence", "type": "boolean", "unit": "", "description": "Listed on ERP marketplace"},
            {"name": "MarketplaceRanking", "type": "numeric", "unit": "", "description": "Ranking within marketplace category"},
            {"name": "MarketplaceLeadsPct", "type": "percentage", "unit": "%", "description": "% of leads from marketplace"},
            {"name": "PartnerConcentrationPct", "type": "percentage", "unit": "%", "description": "Revenue from partner channel"},
            {"name": "ERPRepRelationshipStrength", "type": "ordinal", "unit": "1-5", "description": "Relationship with ERP account managers"},
            # Diversification
            {"name": "MultiERPCapable", "type": "boolean", "unit": "", "description": "Product works with multiple ERPs"},
            {"name": "IntegrationLayerIsolated", "type": "boolean", "unit": "", "description": "Integration code isolated for portability"},
            {"name": "ExpansionERPTargets", "type": "json", "unit": "", "description": "Target ERPs for expansion (NetSuite, Acumatica, etc)"},
            {"name": "DiversificationFeasibility", "type": "ordinal", "unit": "1-5", "description": "Technical/financial feasibility of multi-ERP"},
            # Ecosystem Trajectory
            {"name": "EcosystemGrowthStatus", "type": "enum", "unit": "Growing/Stable/Shrinking", "description": "ERP ecosystem trajectory"},
            {"name": "PlatformRoadmapRiskNotes", "type": "text", "unit": "", "description": "ERP vendor strategic risk notes"},
        ],
        "service_software_ratio": [
            # Revenue Mix
            {"name": "SoftwareRevenuePct", "type": "percentage", "unit": "%", "description": "Software/SaaS revenue % (GREEN 70-90%+, YELLOW 40-60%, RED <40%)"},
            {"name": "ServicesRevenuePct", "type": "percentage", "unit": "%", "description": "Professional services revenue %"},
            {"name": "MaintenanceRevenuePct", "type": "percentage", "unit": "%", "description": "Maintenance revenue %"},
            {"name": "ImplementationRevenuePct", "type": "percentage", "unit": "%", "description": "Implementation services revenue %"},
            {"name": "CustomizationRevenuePct", "type": "percentage", "unit": "%", "description": "Customization services revenue %"},
            {"name": "TrainingRevenuePct", "type": "percentage", "unit": "%", "description": "Training revenue %"},
            # Margins
            {"name": "SoftwareGrossMarginPct", "type": "percentage", "unit": "%", "description": "Software gross margin (target 70-90%)"},
            {"name": "ServicesGrossMarginPct", "type": "percentage", "unit": "%", "description": "Services gross margin (target 30-50%)"},
            {"name": "BlendedMarginTrajectory", "type": "enum", "unit": "Improving/Stable/Declining", "description": "Margin trend direction"},
            # Implementation Model
            {"name": "StandardizedOnboardingPlan", "type": "boolean", "unit": "", "description": "Standard onboarding process exists"},
            {"name": "TemplatedIntegrations", "type": "boolean", "unit": "", "description": "Pre-built integration templates"},
            {"name": "DataMigrationToolsExist", "type": "boolean", "unit": "", "description": "Reusable data migration tools"},
            {"name": "ConfigureNotCustomize", "type": "boolean", "unit": "", "description": "Configuration-first philosophy"},
            {"name": "ImplementationEffortPerCustomer", "type": "numeric", "unit": "hours", "description": "Average implementation hours"},
            # Customization Burden
            {"name": "CustomizationFrequency", "type": "percentage", "unit": "%", "description": "% of customers requiring custom work"},
            {"name": "EngineeringPctInServices", "type": "percentage", "unit": "%", "description": "% of engineering time on services work"},
            {"name": "CustomCodeLeakingToCore", "type": "boolean", "unit": "", "description": "Custom work bleeding into core product"},
            {"name": "CustomWorkBreakageWithUpdates", "type": "boolean", "unit": "", "description": "Custom work breaks on ERP updates"},
            # Delivery Efficiency
            {"name": "ProjectDeliveryTimeDays", "type": "numeric", "unit": "days", "description": "Average project delivery time"},
            {"name": "UtilizationRatePct", "type": "percentage", "unit": "%", "description": "Services team utilization"},
            {"name": "ServicesBacklogSize", "type": "numeric", "unit": "projects", "description": "Services project backlog"},
            {"name": "ContractorReliancePct", "type": "percentage", "unit": "%", "description": "% of delivery using contractors"},
            # Productization Potential
            {"name": "ProductizationPotentialScore", "type": "ordinal", "unit": "1-5", "description": "Potential to convert services to products"},
            {"name": "PackagedOfferingsExist", "type": "boolean", "unit": "", "description": "Packaged solution offerings available"},
            {"name": "TemplatedWorkflowsExist", "type": "boolean", "unit": "", "description": "Reusable workflow templates"},
            {"name": "VerticalBundlesExist", "type": "boolean", "unit": "", "description": "Industry-specific bundles available"},
            {"name": "TieredImplementationsExist", "type": "boolean", "unit": "", "description": "Tiered implementation packages"},
            # Technical Model
            {"name": "ConfigurationVsDevelopmentPct", "type": "percentage", "unit": "%", "description": "% of work that is config vs new code"},
            {"name": "NewCodePerImplementationPct", "type": "percentage", "unit": "%", "description": "% of implementation requiring new code"},
            {"name": "MultiTenantModel", "type": "boolean", "unit": "", "description": "True multi-tenant vs multi-instance"},
            {"name": "VersionDriftLevel", "type": "ordinal", "unit": "Low/Med/High", "description": "Customer version fragmentation"},
            {"name": "UpgradeOverheadLevel", "type": "ordinal", "unit": "Low/Med/High", "description": "Effort to upgrade customer base"},
            # Support Impact
            {"name": "SupportBacklogFromServices", "type": "percentage", "unit": "%", "description": "% of support tickets from custom work"},
            {"name": "CustomWorkBreakageFrequency", "type": "ordinal", "unit": "1-5", "description": "How often custom work causes issues"},
            {"name": "NonStandardConfigTicketPct", "type": "percentage", "unit": "%", "description": "% tickets from non-standard configs"},
            # Roadmap Impact
            {"name": "RoadmapCapacityConsumedByPS", "type": "percentage", "unit": "%", "description": "% of roadmap consumed by PS requests"},
            {"name": "EngineeringDivertedToPSPct", "type": "percentage", "unit": "%", "description": "% of engineering diverted to services"},
            {"name": "LargeClientRoadmapInfluence", "type": "boolean", "unit": "", "description": "Large clients distorting roadmap"},
            {"name": "ProductRoadmapClarity", "type": "ordinal", "unit": "1-5", "description": "Product roadmap discipline"},
            {"name": "AutomationCoveragePct", "type": "percentage", "unit": "%", "description": "Process automation coverage"},
        ],
    }

    def __init__(self):
        self.llm_client = get_llm_client()
        logger.info("[MetricExtractionService] Initialized")

    async def extract_metrics_for_company(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        scoring_run_id: str = None
    ) -> Dict[str, List[CompanyMetric]]:
        """
        Extract all metrics for a company across all pillars.

        Returns dict of {pillar: [metrics]}
        """
        logger.info(f"[Stage 1] Starting metric extraction for company {company_id} (run: {scoring_run_id})")

        all_metrics = {}

        for pillar in BDEPillar:
            if pillar == BDEPillar.GENERAL:
                continue  # Skip general pillar

            pillar_value = pillar.value
            logger.info(f"[Stage 1] Extracting metrics for pillar: {pillar_value}")

            # Get chunks for this pillar that likely contain metrics
            chunks = await self._get_metric_chunks(db, company_id, pillar_value)

            if not chunks:
                logger.info(f"[Stage 1] No chunks found for {pillar_value}, skipping")
                continue

            # Extract metrics using LLM
            extracted = await self._llm_extract_metrics(
                chunks=chunks,
                metric_definitions=self.PILLAR_METRIC_DEFINITIONS.get(pillar_value, []),
                pillar=pillar_value
            )

            # Resolve chunk references to actual chunk IDs
            extracted = self._resolve_chunk_references(extracted, chunks)

            # Boost confidence for metrics corroborated by multiple source types
            extracted = self._boost_corroborated_confidence(extracted, chunks)

            # Log detailed metric extraction sources
            chunk_lookup = {c["id"]: c for c in chunks}
            connector_count_extracted = 0
            document_count_extracted = 0
            corroborated_count = 0

            logger.info(f"[Stage 1] [{pillar_value}] ===== METRIC EXTRACTION SOURCES =====")
            for metric in extracted:
                metric_name = metric.get("name", "unknown")
                confidence = metric.get("confidence", 0)
                value = metric.get("numeric_value") or metric.get("text_value") or metric.get("boolean_value")
                primary_source = metric.get("primary_source_type", "document")
                source_chunks = metric.get("source_chunks", [])
                is_corroborated = metric.get("corroborated", False)

                # Build source details
                source_details = []
                for chunk_id in source_chunks[:3]:
                    chunk = chunk_lookup.get(chunk_id, {})
                    if chunk.get("source_type") == "connector":
                        connector_type = chunk.get("connector_type", "unknown")
                        entity_type = chunk.get("entity_type", "data")
                        source_details.append(f"{connector_type}/{entity_type}")
                    else:
                        page = chunk.get("page_number", "?")
                        source_details.append(f"doc/page-{page}")

                sources_str = ", ".join(source_details) if source_details else "no source"

                if is_corroborated:
                    corroborated_count += 1
                    logger.info(f"[Stage 1] [{pillar_value}] ★ {metric_name}: {value} (confidence: {confidence}, CORROBORATED) [sources: {sources_str}]")
                elif primary_source == "connector":
                    connector_count_extracted += 1
                    logger.info(f"[Stage 1] [{pillar_value}] [CONNECTOR] {metric_name}: {value} (confidence: {confidence}) [source: {sources_str}]")
                else:
                    document_count_extracted += 1
                    logger.info(f"[Stage 1] [{pillar_value}] [DOCUMENT] {metric_name}: {value} (confidence: {confidence}) [source: {sources_str}]")

            logger.info(f"[Stage 1] [{pillar_value}] SUMMARY: {len(extracted)} metrics | {connector_count_extracted} from connector | {document_count_extracted} from document | {corroborated_count} corroborated")
            logger.info(f"[Stage 1] [{pillar_value}] =====================================")

            # Store metrics in database
            stored_metrics = []
            for metric in extracted:
                stored_metric = await self._store_metric(
                    db=db,
                    company_id=company_id,
                    tenant_id=tenant_id,
                    pillar=pillar_value,
                    metric_data=metric,
                    scoring_run_id=scoring_run_id
                )
                if stored_metric:
                    stored_metrics.append(stored_metric)

            all_metrics[pillar_value] = stored_metrics
            logger.info(f"[Stage 1] Extracted {len(stored_metrics)} metrics for {pillar_value}")

        logger.info(f"[Stage 1] Metric extraction complete for company {company_id}")
        return all_metrics

    async def _get_metric_chunks(
        self,
        db: Session,
        company_id: str,
        pillar: str
    ) -> List[Dict[str, Any]]:
        """
        Get ALL chunks for this pillar from both documents and connectors.
        Returns unified chunk dicts with source_type indicator.
        """
        all_chunks = []

        # Query document chunks for this pillar
        doc_statement = select(DocumentChunk).where(
            DocumentChunk.company_id == company_id,
            DocumentChunk.pillar == pillar
        ).order_by(
            DocumentChunk.page_number.asc(),
            DocumentChunk.chunk_index.asc()
        ).limit(150)  # Leave room for connector chunks

        doc_chunks = db.exec(doc_statement).all()

        for chunk in doc_chunks:
            all_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
                "summary": chunk.summary,
                "pillar": chunk.pillar,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "source_type": MetricSourceType.DOCUMENT.value,
                "source_priority": METRIC_SOURCE_PRIORITY[MetricSourceType.DOCUMENT],
            })

        # Query connector chunks for this pillar
        conn_statement = select(ConnectorChunk).where(
            ConnectorChunk.company_id == company_id,
            ConnectorChunk.pillar == pillar
        ).order_by(
            ConnectorChunk.created_at.desc()
        ).limit(50)  # Connector chunks

        conn_chunks = db.exec(conn_statement).all()

        for chunk in conn_chunks:
            all_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
                "summary": chunk.summary,
                "pillar": chunk.pillar,
                "page_number": 0,  # Connector chunks don't have page numbers
                "chunk_index": 0,
                "source_type": MetricSourceType.CONNECTOR.value,
                "source_priority": METRIC_SOURCE_PRIORITY[MetricSourceType.CONNECTOR],
                "connector_type": chunk.connector_type.value if chunk.connector_type else None,
                "entity_type": chunk.entity_type,
                "entity_name": chunk.entity_name,
            })

        logger.info(f"[Stage 1] Retrieved {len(doc_chunks)} document chunks and {len(conn_chunks)} connector chunks for {pillar}")

        return all_chunks

    async def _llm_extract_metrics(
        self,
        chunks: List[DocumentChunk],
        metric_definitions: List[Dict],
        pillar: str
    ) -> List[Dict]:
        """Use LLM to extract structured metrics from chunks"""

        if not metric_definitions:
            logger.info(f"[Stage 1] No metric definitions for pillar {pillar}")
            return []

        # Format chunks for prompt
        chunks_text = self._format_chunks(chunks)

        # Count source types for context
        connector_count = sum(1 for c in chunks if c.get("source_type") == "connector")
        document_count = len(chunks) - connector_count

        # Build clean, focused prompt
        prompt = f"""You are extracting BDE metrics from the provided document chunks according to the metric definitions for the **{pillar}** pillar.
For each metric definition provided, search the document text for supporting evidence and output only metrics that meet the confidence threshold of 0.5 or above.
Prioritize CONNECTOR data for quantitative metrics and DOCUMENT data for qualitative metrics.
When both sources exist for the same metric, use CONNECTOR as primary and cite DOCUMENT chunks as supporting evidence.

## DATA SOURCES:
You have access to {len(chunks)} chunks from TWO types of sources:
- **CONNECTOR chunks** ({connector_count}): Authoritative pre-computed data from integrated systems.
- **DOCUMENT chunks** ({document_count}): Narrative context from uploaded business documents.

## SOURCE PRIORITY & COMBINATION
1. Quantitative metrics (numbers, percentages, currency): Prefer CONNECTOR data.
2. Qualitative metrics (boolean, ordinal, text): Use DOCUMENT data.
3. If both sources mention the same metric:
   - Use CONNECTOR value as primary.
   - Cite supporting DOCUMENT chunks in `"source_chunks"`.
4. If values conflict, take the most recent/explicit, and note all sources.

## METRIC DEFINITIONS:
{json.dumps(metric_definitions, indent=2)}

## DOCUMENT TEXT:
{chunks_text}

## EXTRACTION RULES:
- For each metric in the metric definitions, identify the specific criteria, data type, and expected format defined for that pillar.
- Systematically scan the document text for language, values, or statements that directly correspond to each metric's definition.
- Only extract metrics that achieve a confidence score of 0.5 or above based on the evidence found.
- For each extracted metric, provide surrounding sentence context (1-2 sentences) and list all relevant chunk IDs.
- Do not extract metrics that lack supporting evidence in the document.
- Always store the original text including signs, symbols, and units in "text_value" for database storage.
- Numeric conversions (if any) go into "numeric_value" only; otherwise leave null.
- For boolean metrics: use true/false for numeric_value (1/0) and "Yes"/"No" for text_value.


## TABLE/LIST DATA EXTRACTION:
When table first column has ENTITY NAMES (accounts, customers, deals) with multiple attribute columns:
- Match tables to list-type metric definitions: TopAccountsList, AtRiskAccountsList, RecentDealsList
- Extract ALL rows from the table into "json_value" as an array of objects
- **SCHEMA-FLEXIBLE**: Convert each table column header to a snake_case key. Use the ACTUAL column names from the table - do NOT force predefined keys.
- Parse numeric values: remove currency symbols and commas, convert to numbers
- Include ALL columns present in the table - do not skip any data
- Set "numeric_value" to the count of rows extracted
- Set "text_value" to a brief description like "X rows extracted from table"
- The "json_value" array should contain one object per table row, with keys matching the table's column headers in snake_case


## CONFIDENCE GUIDELINES (0.0 to 1.0 scale):
- 0.9-1.0: Explicit exact value from CONNECTOR or clearly stated in document
- 0.7-0.89: Clear implication with supporting context
- 0.5-0.69: Reasonable inference
- Below 0.5: Do not extract

## CONTEXT Requirements:
- Include the sentence containing the metric plus 1-2 surrounding sentences for clarity.
- Always reference chunk IDs where metrics appear (e.g., "chunk_0", "chunk_1").

## OUTPUT FORMAT (Strict JSON):
{{
  "metrics": [
    {{
      "name": "metric name",
      "type": "numeric|percentage|boolean|ordinal|text|json",
      "numeric_value": null,
      "text_value": "",
      "json_value": null,
      "unit": "",
      "period": "",
      "as_of_date": "",
      "source_chunks": ["chunk_0"],
      "confidence": [0.0-1.0],
      "context": "surrounding sentence context"
    }}
  ]
}}

NOTE: For metrics with type "json" (lists/tables/time-series), put the structured data in "json_value" field. Follow the format specified in the metric definition's description. For time-series data, use the format: {{"type": "time_series", "frequency": "monthly|quarterly|yearly", "data": {{"Period": value, ...}}, "total": total_value}}.

IMPORTANT: Return ONLY valid JSON. No markdown, no code blocks, no explanations. Start with {{ and end with }}."""

        try:
            response_text, usage_stats = self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business due diligence expert. Extract metrics from the provided data following the instructions. You MUST respond with valid JSON only - no markdown, no code blocks, no explanations. Start your response with { and end with }."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=5000
            )

            # Parse response - handle markdown code blocks
            cleaned_response = response_text.strip()

            # Remove markdown code blocks if present
            if cleaned_response.startswith("```"):
                # Remove ```json or ``` from start
                lines = cleaned_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_response = "\n".join(lines)

            # Try to find JSON object/array in the response
            json_start = cleaned_response.find("{")
            json_array_start = cleaned_response.find("[")

            if json_start == -1 and json_array_start == -1:
                logger.warning(f"[Stage 1] No JSON found in response for {pillar}")
                return []

            # Use whichever comes first
            if json_start >= 0 and (json_array_start == -1 or json_start < json_array_start):
                cleaned_response = cleaned_response[json_start:]
            elif json_array_start >= 0:
                cleaned_response = cleaned_response[json_array_start:]

            result = json.loads(cleaned_response)

            # Handle different response formats
            if isinstance(result, dict) and "metrics" in result:
                metrics = result["metrics"]
            elif isinstance(result, list):
                metrics = result
            else:
                metrics = []

            # Debug: Log first metric to see what LLM is returning
            if metrics:
                logger.debug(f"[Stage 1] Sample metric from LLM: {json.dumps(metrics[0], indent=2)}")

            logger.info(f"[Stage 1] LLM extracted {len(metrics)} metrics for {pillar}")
            return metrics

        except json.JSONDecodeError as e:
            logger.error(f"[Stage 1] JSON parse error for {pillar}: {e}")
            logger.debug(f"[Stage 1] Raw response: {response_text[:500]}...")
            return []
        except Exception as e:
            logger.error(f"[Stage 1] Error extracting metrics: {e}")
            return []

    def _format_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks for LLM prompt with numeric indices - FULL CONTENT, no truncation"""
        formatted = []

        # Group chunks by source type for clearer presentation
        connector_chunks = [(i, c) for i, c in enumerate(chunks) if c.get("source_type") == "connector"]
        document_chunks = [(i, c) for i, c in enumerate(chunks) if c.get("source_type") != "connector"]

        # Add connector chunks first (higher priority for financial metrics)
        if connector_chunks:
            formatted.append("=" * 60)
            formatted.append("## CONNECTOR DATA (Authoritative financial data - PREFER for quantitative metrics)")
            formatted.append("=" * 60)

            for i, chunk in connector_chunks:
                formatted.append(f"\n[Chunk ID: chunk_{i}]")
                connector_type = chunk.get("connector_type", "connector")
                entity_type = chunk.get("entity_type", "data")
                entity_name = chunk.get("entity_name", "")
                source_label = f"Source: {connector_type.upper()} | Entity: {entity_type}"
                if entity_name:
                    source_label += f" | {entity_name}"
                formatted.append(source_label)
                formatted.append(f"Data Quality: COMPUTED (from actual transactions)")
                formatted.append(f"Content: {chunk.get('content', '')}")
                if chunk.get("summary"):
                    formatted.append(f"Summary: {chunk.get('summary')}")
                formatted.append("---")

        # Add document chunks
        if document_chunks:
            formatted.append("\n" + "=" * 60)
            formatted.append("## DOCUMENT DATA (Narrative context - USE for qualitative metrics)")
            formatted.append("=" * 60)

            for i, chunk in document_chunks:
                formatted.append(f"\n[Chunk ID: chunk_{i}]")
                formatted.append(f"Source: DOCUMENT | Page {chunk.get('page_number', 0)}")
                formatted.append(f"Data Quality: EXTRACTED (from uploaded documents)")
                formatted.append(f"Content: {chunk.get('content', '')}")
                if chunk.get("summary"):
                    formatted.append(f"Summary: {chunk.get('summary')}")
                formatted.append("---")

        return "\n".join(formatted)

    def _resolve_chunk_references(
        self,
        metrics: List[Dict],
        chunks: List[Dict[str, Any]]
    ) -> List[Dict]:
        """
        Resolve LLM chunk references to actual chunk IDs.
        LLM might return "chunk_1", "chunk_2" or partial UUIDs - map them to real IDs.
        Also tracks source_type for each resolved chunk.
        """
        # Build mapping of index -> chunk info and partial ID -> chunk info
        chunk_index_map = {i: chunk for i, chunk in enumerate(chunks)}
        chunk_uuid_map = {chunk["id"]: chunk for chunk in chunks}

        # Track how many metrics are missing source_chunks
        missing_sources_count = 0

        for metric in metrics:
            source_chunks = metric.get("source_chunks", [])
            if not source_chunks:
                missing_sources_count += 1
                # Log the metric name for debugging
                metric_name = metric.get("name", "unknown")
                logger.debug(f"[Stage 1] Metric '{metric_name}' has no source_chunks field in LLM response")
                continue

            resolved_chunks = []
            resolved_source_types = []  # Track source types for priority
            resolved_source_priorities = []

            for ref in source_chunks:
                if not ref:
                    continue

                resolved_chunk = None

                # Handle "chunk_id_UUID" format (e.g., "chunk_id_20c75d60-25ce-4782-984e-62672d36019a")
                if isinstance(ref, str) and ref.startswith("chunk_id_"):
                    # Extract UUID after "chunk_id_" prefix
                    uuid_part = ref[9:]  # Remove "chunk_id_" (9 characters)
                    if uuid_part in chunk_uuid_map:
                        resolved_chunk = chunk_uuid_map[uuid_part]
                    else:
                        # Try to find matching chunk by prefix
                        for chunk in chunks:
                            if chunk["id"].startswith(uuid_part) or chunk["id"] == uuid_part:
                                resolved_chunk = chunk
                                break

                # Handle "chunk_N" format (e.g., "chunk_1", "chunk_0") - numeric index
                elif isinstance(ref, str) and ref.startswith("chunk_") and ref.split("_")[1].isdigit():
                    try:
                        idx = int(ref.split("_")[1])
                        if idx in chunk_index_map:
                            resolved_chunk = chunk_index_map[idx]
                    except (ValueError, IndexError):
                        pass

                # Handle actual UUID (already correct)
                elif ref in chunk_uuid_map:
                    resolved_chunk = chunk_uuid_map[ref]

                # Handle partial UUID - find matching chunk
                elif isinstance(ref, str) and len(ref) > 8:
                    for chunk in chunks:
                        if chunk["id"].startswith(ref):
                            resolved_chunk = chunk
                            break

                # Add resolved chunk info
                if resolved_chunk:
                    resolved_chunks.append(resolved_chunk["id"])
                    resolved_source_types.append(resolved_chunk.get("source_type", "document"))
                    resolved_source_priorities.append(resolved_chunk.get("source_priority", 50))
                else:
                    logger.warning(f"[Stage 1] Could not resolve chunk reference: {ref}")

            # Update metric with resolved chunk IDs and source info
            metric["source_chunks"] = resolved_chunks if resolved_chunks else []

            # Track highest priority source type for this metric
            if resolved_source_priorities:
                max_priority = max(resolved_source_priorities)
                max_idx = resolved_source_priorities.index(max_priority)
                metric["primary_source_type"] = resolved_source_types[max_idx]
                metric["source_priority"] = max_priority

        # Log summary
        if missing_sources_count > 0:
            logger.warning(f"[Stage 1] {missing_sources_count}/{len(metrics)} metrics missing source_chunks in LLM response")

        return metrics

    def _boost_corroborated_confidence(
        self,
        metrics: List[Dict],
        chunks: List[Dict[str, Any]]
    ) -> List[Dict]:
        """
        Boost confidence for metrics that are corroborated by multiple source types.

        If the same metric is found in both connector AND document sources,
        boost the confidence since we have independent verification.
        """
        # Build chunk source type lookup
        chunk_source_map = {c["id"]: c.get("source_type", "document") for c in chunks}

        for metric in metrics:
            source_chunks = metric.get("source_chunks", [])
            if len(source_chunks) < 2:
                continue

            # Check source types of all cited chunks
            source_types = set()
            for chunk_id in source_chunks:
                source_type = chunk_source_map.get(chunk_id, "document")
                source_types.add(source_type)

            # If metric has BOTH connector AND document sources, it's corroborated
            if "connector" in source_types and "document" in source_types:
                original_confidence = metric.get("confidence", 0.8)
                # Boost by 0.05-0.10, cap at 1.0
                boost = 0.08
                new_confidence = min(1.0, original_confidence + boost)
                metric["confidence"] = new_confidence
                metric["corroborated"] = True
                metric["corroboration_note"] = "Metric found in both connector data and uploaded documents"

                logger.debug(
                    f"[Stage 1] Boosted confidence for {metric.get('name')}: "
                    f"{original_confidence} → {new_confidence} (corroborated)"
                )

        # Log corroboration summary
        corroborated_count = sum(1 for m in metrics if m.get("corroborated"))
        if corroborated_count > 0:
            logger.info(f"[Stage 1] {corroborated_count} metrics corroborated by multiple sources")

        return metrics

    async def _store_metric(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        pillar: str,
        metric_data: Dict[str, Any],
        scoring_run_id: str = None
    ) -> Optional[CompanyMetric]:
        """Store metric with conflict resolution"""

        metric_name = metric_data.get("name")
        if not metric_name:
            return None

        # Check for existing metrics with same name in THIS scoring run only
        # (not previous runs - those are historical data)
        statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.metric_name == metric_name,
            CompanyMetric.scoring_run_id == scoring_run_id
        )
        existing = db.exec(statement).first()

        # Parse date
        as_of_date = None
        if metric_data.get("as_of_date"):
            try:
                as_of_date = datetime.strptime(metric_data["as_of_date"], "%Y-%m-%d").date()
            except:
                pass

        # Determine pillar associations
        pillars_used_by = self._determine_pillar_associations(metric_name)

        # Handle different value types
        numeric_value = metric_data.get("numeric_value")
        text_value = metric_data.get("text_value")
        json_value = None

        # Parse json_value if provided (for any type — time-series, lists, complex data)
        raw_json = metric_data.get("json_value")
        if raw_json is not None:
            if isinstance(raw_json, str):
                try:
                    parsed = json.loads(raw_json)
                    # Handle double-serialized (string containing string)
                    while isinstance(parsed, str):
                        parsed = json.loads(parsed)
                    json_value = parsed
                    logger.debug(f"[Stage 1] Parsed JSON string for {metric_data.get('name')}")
                except json.JSONDecodeError as e:
                    logger.warning(f"[Stage 1] Failed to parse JSON for {metric_data.get('name')}: {e}")
                    json_value = None
            elif isinstance(raw_json, (list, dict)):
                # Already a proper Python object
                json_value = raw_json
            else:
                logger.warning(f"[Stage 1] Unexpected json_value type for {metric_data.get('name')}: {type(raw_json)}")
                json_value = None

        # For booleans
        if metric_data.get("type") == "boolean":
            numeric_value = 1 if metric_data.get("boolean_value") else 0
            text_value = "Yes" if metric_data.get("boolean_value") else "No"

        # Get source chunks - CRITICAL for data lineage
        source_chunks = metric_data.get("source_chunks", [])

        # VALIDATION: Ensure source_chunks is not empty
        # If LLM didn't provide source chunks, log a warning
        if not source_chunks:
            logger.warning(f"[Stage 1] Metric {metric_name} missing source_chunks - data lineage will be incomplete")

        # Get source type and priority info
        source_type = metric_data.get("primary_source_type", "document")
        source_priority = metric_data.get("source_priority", 50)

        # Build extraction context with source info
        extraction_context = {
            "context": metric_data.get("context"),
            "source_type": source_type,
            "source_priority": source_priority,
        }

        # Create new metric
        new_metric = CompanyMetric(
            company_id=company_id,
            tenant_id=tenant_id,
            scoring_run_id=scoring_run_id,
            metric_name=metric_name,
            metric_value_numeric=numeric_value,
            metric_value_text=text_value,
            metric_value_json=json_value,
            metric_unit=metric_data.get("unit"),
            metric_period=metric_data.get("period"),
            metric_as_of_date=as_of_date,
            pillars_used_by=pillars_used_by,
            primary_pillar=pillar,
            source_chunk_ids=source_chunks,
            confidence=metric_data.get("confidence"),
            extraction_context=json.dumps(extraction_context),
            is_current=True
        )

        # Conflict resolution - pass source priority
        if existing:
            should_supersede = self._should_supersede_metric(existing, new_metric, source_priority)

            if should_supersede:
                # Mark old as superseded
                existing.is_current = False
                existing.superseded_by = new_metric.id
                db.add(existing)
                logger.info(f"[Stage 1] Superseding metric {metric_name}: {existing.metric_value_text} → {new_metric.metric_value_text}")
            else:
                # Keep both, flag for review
                new_metric.needs_analyst_review = True
                existing.needs_analyst_review = True
                db.add(existing)
                logger.info(f"[Stage 1] Conflict detected for {metric_name}, flagging for review")

        db.add(new_metric)
        db.commit()
        db.refresh(new_metric)

        return new_metric

    def _should_supersede_metric(
        self,
        existing: CompanyMetric,
        new_metric: CompanyMetric,
        new_source_priority: int = 50
    ) -> bool:
        """
        Determine if new metric should supersede existing one.
        Connector data (priority 100) beats document data (priority 50).
        """
        # Get existing metric's source priority from extraction context
        existing_priority = 50  # Default for documents
        if existing.extraction_context:
            try:
                ctx = json.loads(existing.extraction_context) if isinstance(existing.extraction_context, str) else existing.extraction_context
                existing_priority = ctx.get("source_priority", 50) if isinstance(ctx, dict) else 50
            except:
                pass

        # Rule 1: Higher priority source always wins (connector > document)
        if new_source_priority > existing_priority:
            logger.info(f"[Stage 1] Connector metric supersedes document metric (priority {new_source_priority} > {existing_priority})")
            return True
        elif new_source_priority < existing_priority:
            return False

        # Rule 2: Same priority - prefer most recent date
        if new_metric.metric_as_of_date and existing.metric_as_of_date:
            if new_metric.metric_as_of_date > existing.metric_as_of_date:
                return True
            elif new_metric.metric_as_of_date < existing.metric_as_of_date:
                return False

        # Rule 3: Prefer higher confidence (0.1 threshold on 0-1 scale)
        if new_metric.confidence and existing.confidence:
            if new_metric.confidence > existing.confidence + 0.1:
                return True

        # Rule 4: Conservative default - keep existing
        return False

    def _determine_pillar_associations(self, metric_name: str) -> List[str]:
        """Map metrics to all relevant pillars - COMPLETE MAPPING"""

        # Metrics that are used by multiple pillars
        multi_pillar_metrics = {
            # Financial Health cross-pillar
            "ARR": ["financial_health", "gtm_engine"],
            "MRR": ["financial_health", "gtm_engine"],
            "GRR": ["customer_health", "financial_health"],
            "NRR": ["customer_health", "financial_health"],
            "ChurnRatePct": ["customer_health", "financial_health"],
            "LogoChurnRatePct": ["customer_health", "financial_health"],
            "RevenueChurnRatePct": ["customer_health", "financial_health"],
            "GrossMarginPct": ["financial_health", "service_software_ratio"],
            "EBITDA_MarginPct": ["financial_health", "operational_maturity"],
            "TopCustomerConcentrationPct": ["financial_health", "customer_health"],
            "Top3CustomerConcentrationPct": ["financial_health", "customer_health"],
            "CustomerConcentrationPct": ["financial_health", "customer_health"],
            "RecurringRevenuePct": ["financial_health", "service_software_ratio"],
            # Service/Software cross-pillar
            "ServicesGrossMarginPct": ["operational_maturity", "service_software_ratio", "financial_health"],
            "SoftwareGrossMarginPct": ["service_software_ratio", "financial_health"],
            "SoftwareRevenuePct": ["financial_health", "service_software_ratio"],
            "ServicesRevenuePct": ["financial_health", "service_software_ratio"],
            "ImplementationRevenuePct": ["service_software_ratio", "operational_maturity"],
            "CustomizationRevenuePct": ["service_software_ratio", "product_technical"],
            # GTM cross-pillar
            "ForecastAccuracyPct": ["gtm_engine", "operational_maturity"],
            "PartnerSourcedRevenuePct": ["gtm_engine", "ecosystem_dependency"],
            "CRMDisciplineScore": ["gtm_engine", "operational_maturity"],
            # Customer Health cross-pillar
            "NPS": ["customer_health", "product_technical"],
            "CSAT": ["customer_health", "product_technical"],
            "SupportTicketVolume": ["customer_health", "operational_maturity"],
            "TicketBacklogCount": ["customer_health", "operational_maturity"],
            "TicketResolutionTimeDays": ["customer_health", "operational_maturity"],
            # Product/Technical cross-pillar
            "TechDebtLevel": ["product_technical", "service_software_ratio"],
            "IntegrationFragilityScore": ["product_technical", "ecosystem_dependency"],
            "ERPVersionCompatibility": ["product_technical", "ecosystem_dependency"],
            "BusFactorRisk": ["product_technical", "leadership_transition"],
            # Operational cross-pillar
            "OnboardingTimeDays": ["operational_maturity", "customer_health"],
            "StandardImplementationPct": ["operational_maturity", "service_software_ratio"],
            "DeliveryDependencyOnIndividuals": ["operational_maturity", "leadership_transition"],
            # Leadership cross-pillar
            "FounderSalesDependencyPct": ["leadership_transition", "gtm_engine"],
            "FounderProductDependency": ["leadership_transition", "product_technical"],
            "LeadershipBenchCoverage": ["leadership_transition", "operational_maturity"],
            "DecisionCentralizationScore": ["leadership_transition", "operational_maturity"],
            # Ecosystem cross-pillar
            "PrimaryERPDependencyPct": ["ecosystem_dependency", "financial_health"],
            "MarketplacePresence": ["ecosystem_dependency", "gtm_engine"],
            "CoSellMotionExists": ["ecosystem_dependency", "gtm_engine"],
            "PartnerConcentrationPct": ["ecosystem_dependency", "financial_health"],
        }

        return multi_pillar_metrics.get(metric_name, [])
