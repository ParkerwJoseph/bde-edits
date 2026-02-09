/**
 * AnalyticsPillarDetail Page
 *
 * Deep-dive analytics view for a specific pillar.
 * Shows detailed metrics, documents, risks, and accelerants.
 * Fetches real data from the API.
 */

import { useMemo, useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle2,
  Clock,
  AlertCircle,
  Zap,
  Upload,
  FileText,
  FileSpreadsheet,
  Mail,
  FileAudio,
  Database,
  File,
  Star,
  CircleDot,
  Info,
  DollarSign,
  Users,
  Cpu,
  Target,
  Settings,
  Crown,
  Network,
  ArrowRightLeft,
  type LucideIcon,
} from 'lucide-react';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/common/PageLoader';
import { useCompany } from '../contexts/CompanyContext';
import { usePillarDetail, useBDEScore, useFlags, useMetrics } from '../hooks/useScoring';
import { scoringApi, type BDEPillar, PILLAR_CONFIG, type Metric, type SourceDocumentInfo } from '../api/scoringApi';
import { cn } from '../lib/scorecard-utils';
import styles from '../styles/pages/AnalyticsPillarDetail.module.css';

// Pillar icons mapping
const PILLAR_ICONS: Record<BDEPillar, LucideIcon> = {
  financial_health: DollarSign,
  gtm_engine: Target,
  customer_health: Users,
  product_technical: Cpu,
  operational_maturity: Settings,
  leadership_transition: Crown,
  ecosystem_dependency: Network,
  service_software_ratio: ArrowRightLeft,
};

// Pillar short names
const PILLAR_SHORT_NAMES: Record<BDEPillar, string> = {
  financial_health: 'Financial',
  gtm_engine: 'GTM',
  customer_health: 'Customer',
  product_technical: 'Product',
  operational_maturity: 'Operations',
  leadership_transition: 'Leadership',
  ecosystem_dependency: 'Ecosystem',
  service_software_ratio: 'S2S',
};

// Pillar descriptions
const PILLAR_DESCRIPTIONS: Record<BDEPillar, string> = {
  financial_health: 'Revenue quality, growth trajectory, and financial health metrics',
  gtm_engine: 'Go-to-market efficiency, sales performance, and pipeline health',
  customer_health: 'Customer retention, satisfaction, and concentration metrics',
  product_technical: 'Product-market fit, technical health, and development velocity',
  operational_maturity: 'Process maturity, compliance, and operational efficiency',
  leadership_transition: 'Team depth, key person dependencies, and governance',
  ecosystem_dependency: 'Platform dependencies, integrations, and partner ecosystem',
  service_software_ratio: 'Balance between professional services and software revenue',
};

// Document type icons
const DOC_TYPE_ICONS: Record<string, LucideIcon> = {
  pdf: FileText,
  spreadsheet: FileSpreadsheet,
  email: Mail,
  transcript: FileAudio,
  crm_export: Database,
  other: File,
  xlsx: FileSpreadsheet,
  csv: FileSpreadsheet,
  docx: FileText,
};

// Recommended documents by pillar
interface RecommendedDocument {
  name: string;
  type: string;
  priority: 'required' | 'recommended' | 'optional';
  description: string;
  impact: string;
}

const RECOMMENDED_DOCUMENTS: Record<BDEPillar, RecommendedDocument[]> = {
  financial_health: [
    { name: 'Audited Financial Statements', type: 'pdf', priority: 'required', description: 'Last 2-3 years of audited financials', impact: 'Provides verified revenue, expenses, and balance sheet data' },
    { name: 'Monthly P&L Statements', type: 'spreadsheet', priority: 'required', description: 'Trailing 12-24 months of P&L', impact: 'Enables trend analysis and margin calculations' },
    { name: 'Cap Table', type: 'spreadsheet', priority: 'required', description: 'Current capitalization table with all shareholders', impact: 'Critical for ownership structure and dilution analysis' },
    { name: 'Cash Flow Forecast', type: 'spreadsheet', priority: 'recommended', description: '18-month forward cash projections', impact: 'Helps assess runway and capital needs' },
    { name: 'Revenue by Customer', type: 'spreadsheet', priority: 'recommended', description: 'Detailed revenue breakdown by customer', impact: 'Reveals concentration risk and expansion patterns' },
  ],
  gtm_engine: [
    { name: 'CRM Pipeline Export', type: 'spreadsheet', priority: 'required', description: 'Full pipeline with stages, values, and close dates', impact: 'Enables pipeline coverage and velocity analysis' },
    { name: 'Won/Lost Deal Analysis', type: 'spreadsheet', priority: 'required', description: 'Last 12 months of closed deals with outcomes', impact: 'Calculates win rates and identifies patterns' },
    { name: 'Sales Rep Performance', type: 'spreadsheet', priority: 'required', description: 'Quota attainment by rep over time', impact: 'Reveals team capacity and performance distribution' },
    { name: 'Marketing Spend Report', type: 'spreadsheet', priority: 'recommended', description: 'Channel-by-channel marketing spend', impact: 'CAC calculation and channel efficiency' },
  ],
  customer_health: [
    { name: 'Cohort Retention Analysis', type: 'spreadsheet', priority: 'required', description: 'Monthly cohort retention over 24+ months', impact: 'Accurate NRR/GRR and retention trend calculation' },
    { name: 'Customer Health Scores', type: 'spreadsheet', priority: 'required', description: 'Current health scores with methodology', impact: 'Identifies at-risk accounts and expansion opportunities' },
    { name: 'NPS/CSAT Survey Results', type: 'spreadsheet', priority: 'required', description: 'Survey responses with scores and verbatims', impact: 'Quantifies customer satisfaction and loyalty' },
    { name: 'Churn Log', type: 'spreadsheet', priority: 'recommended', description: 'Historical churned customers with reasons', impact: 'Pattern identification for churn prevention' },
  ],
  product_technical: [
    { name: 'Technical Architecture Document', type: 'pdf', priority: 'required', description: 'System architecture and tech stack overview', impact: 'Understanding of scalability and maintainability' },
    { name: 'Security Audit Report', type: 'pdf', priority: 'required', description: 'Recent third-party security assessment', impact: 'Validates security posture and compliance' },
    { name: 'Product Roadmap', type: 'pdf', priority: 'required', description: '12-18 month product development plan', impact: 'Vision clarity and execution capability' },
    { name: 'Engineering Metrics Dashboard', type: 'spreadsheet', priority: 'recommended', description: 'Velocity, uptime, incident data', impact: 'Quantifies engineering team performance' },
  ],
  operational_maturity: [
    { name: 'Operations Playbook', type: 'pdf', priority: 'required', description: 'Documented SOPs and workflows', impact: 'Process maturity and scalability assessment' },
    { name: 'SLA Performance Report', type: 'spreadsheet', priority: 'required', description: 'Historical SLA attainment metrics', impact: 'Operational reliability measurement' },
    { name: 'SOC 2 Report', type: 'pdf', priority: 'required', description: 'Latest SOC 2 Type II audit', impact: 'Compliance verification and control assessment' },
    { name: 'Data Quality Report', type: 'spreadsheet', priority: 'recommended', description: 'CRM and system data hygiene metrics', impact: 'Operational foundation assessment' },
  ],
  leadership_transition: [
    { name: 'Organizational Chart', type: 'pdf', priority: 'required', description: 'Current org structure with reporting lines', impact: 'Clarity on structure and key person dependencies' },
    { name: 'Executive Bios & Resumes', type: 'pdf', priority: 'required', description: 'Background on leadership team', impact: 'Experience and capability assessment' },
    { name: 'Board Meeting Minutes', type: 'pdf', priority: 'required', description: 'Last 3-4 board meeting notes', impact: 'Governance quality and strategic alignment' },
    { name: 'Succession Plan', type: 'pdf', priority: 'recommended', description: 'Key role succession documentation', impact: 'Continuity planning assessment' },
  ],
  ecosystem_dependency: [
    { name: 'Partner List & Revenue', type: 'spreadsheet', priority: 'required', description: 'All partners with attributed revenue', impact: 'Partner channel contribution analysis' },
    { name: 'Integration Documentation', type: 'pdf', priority: 'required', description: 'API docs and integration guides', impact: 'Technical partnership capability assessment' },
    { name: 'ERP Certification Status', type: 'pdf', priority: 'required', description: 'Certifications for major ERP platforms', impact: 'Enterprise readiness validation' },
    { name: 'API Usage Analytics', type: 'spreadsheet', priority: 'recommended', description: 'API call volumes and adoption trends', impact: 'Platform stickiness measurement' },
  ],
  service_software_ratio: [
    { name: 'Revenue Mix Analysis', type: 'spreadsheet', priority: 'required', description: 'Software vs services revenue over time', impact: 'Transition progress measurement' },
    { name: 'Services P&L', type: 'spreadsheet', priority: 'required', description: 'Professional services margin analysis', impact: 'Services profitability assessment' },
    { name: 'Implementation Playbook', type: 'pdf', priority: 'required', description: 'Standard implementation methodology', impact: 'Scalability and repeatability evaluation' },
    { name: 'Self-Serve Adoption Metrics', type: 'spreadsheet', priority: 'recommended', description: 'Self-service vs assisted onboarding rates', impact: 'Productization progress indicator' },
  ],
};

// Metrics mapping by pillar (which metrics to show for each pillar)
// Names must match the actual metric names extracted by the backend (metric_extraction_service.py)
// Show up to 6 metrics per pillar to match the 6-column grid layout
const PILLAR_METRICS: Record<BDEPillar, string[]> = {
  financial_health: ['ARR', 'GrossMarginPct', 'BurnRateMonthly', 'RunwayMonths', 'MRR', 'EBITDA_MarginPct'],
  gtm_engine: ['PipelineCoverageRatio', 'WinRatePct', 'CAC', 'AvgSalesCycleDays', 'AvgDealSize', 'ForecastAccuracyPct'],
  customer_health: ['NRR', 'GRR', 'ChurnRatePct', 'NPS', 'CSAT', 'TotalCustomers'],
  product_technical: ['UptimePct', 'TechDebtLevel', 'DeployFrequency', 'TestCoveragePct', 'ErrorRatePct', 'AvgResponseTimeMs'],
  operational_maturity: ['SOPCoveragePct', 'CRMDataAccuracyScore', 'OnboardingTimeDays', 'UtilizationRatePct', 'TimeToValueDays', 'ServicesGrossMarginPct'],
  leadership_transition: ['FounderDailyInvolvementHours', 'FounderSalesDependencyPct', 'LeadershipTeamSize', 'TransitionReadinessScore', 'DecisionCentralizationScore', 'TurnoverRatePct'],
  ecosystem_dependency: ['PrimaryERPDependencyPct', 'PartnerSourcedRevenuePct', 'IntegrationDepthScore', 'MarketplaceRanking', 'ERPRoadmapAligned', 'MultiERPCapable'],
  service_software_ratio: ['SoftwareRevenuePct', 'ServicesGrossMarginPct', 'ImplementationEffortPerCustomer', 'CustomizationFrequency', 'ProductizationPotentialScore', 'ServicesRevenuePct'],
};

// Display names for metrics (technical name -> user-friendly name)
const METRIC_DISPLAY_NAMES: Record<string, string> = {
  // Financial
  ARR: 'ARR',
  MRR: 'MRR',
  GrossMarginPct: 'Gross Margin',
  BurnRateMonthly: 'Burn Rate',
  RunwayMonths: 'Runway',
  RevenueGrowthRateYoY: 'Revenue Growth',
  RecurringRevenuePct: 'Recurring Revenue %',
  EBITDA_MarginPct: 'EBITDA Margin',
  // GTM
  CAC: 'CAC',
  WinRatePct: 'Win Rate',
  PipelineCoverageRatio: 'Pipeline Coverage',
  AvgSalesCycleDays: 'Sales Cycle',
  AvgDealSize: 'Avg Deal Size',
  ForecastAccuracyPct: 'Forecast Accuracy',
  LeadToMQLPct: 'Lead to MQL',
  SQLToClosePct: 'SQL to Close',
  // Customer Health
  NRR: 'NRR',
  GRR: 'GRR',
  ChurnRatePct: 'Churn Rate',
  NPS: 'NPS',
  CSAT: 'CSAT',
  TotalCustomers: 'Total Customers',
  ActiveCustomers: 'Active Customers',
  AtRiskCustomerCount: 'At-Risk Customers',
  RenewalRate: 'Renewal Rate',
  // Product/Technical
  UptimePct: 'Uptime',
  TechDebtLevel: 'Tech Debt',
  DeployFrequency: 'Deploy Frequency',
  TestCoveragePct: 'Test Coverage',
  ErrorRatePct: 'Error Rate',
  AvgResponseTimeMs: 'Avg Response Time',
  IntegrationFragilityScore: 'Integration Stability',
  // Operational
  SOPCoveragePct: 'SOP Coverage',
  CRMDataAccuracyScore: 'CRM Data Quality',
  OnboardingTimeDays: 'Onboarding Time',
  UtilizationRatePct: 'Utilization Rate',
  TimeToValueDays: 'Time to Value',
  ServicesGrossMarginPct: 'Services Margin',
  // Leadership
  FounderDailyInvolvementHours: 'Founder Involvement',
  FounderSalesDependencyPct: 'Founder Sales Dependency',
  LeadershipTeamSize: 'Leadership Team Size',
  TransitionReadinessScore: 'Transition Readiness',
  DecisionCentralizationScore: 'Decision Distribution',
  TurnoverRatePct: 'Turnover Rate',
  // Ecosystem
  PrimaryERPDependencyPct: 'ERP Dependency',
  PartnerSourcedRevenuePct: 'Partner Revenue',
  IntegrationDepthScore: 'Integration Depth',
  MarketplaceRanking: 'Marketplace Rank',
  ERPRoadmapAligned: 'ERP Alignment',
  MultiERPCapable: 'Multi-ERP Support',
  // Service/Software
  SoftwareRevenuePct: 'Software Revenue %',
  ImplementationEffortPerCustomer: 'Impl. Effort',
  CustomizationFrequency: 'Customization Rate',
  ProductizationPotentialScore: 'Productization Score',
  ServicesRevenuePct: 'Services Revenue %',
};

// Human-readable descriptions for metrics (shown below the value)
const METRIC_DESCRIPTIONS: Record<string, string> = {
  // Financial
  ARR: 'Annual recurring revenue',
  MRR: 'Monthly recurring revenue',
  GrossMarginPct: 'Revenue minus COGS',
  BurnRateMonthly: 'Monthly cash consumption',
  RunwayMonths: 'Months of cash remaining',
  RevenueGrowthRateYoY: 'Year-over-year growth',
  RecurringRevenuePct: 'Recurring share of revenue',
  EBITDA_MarginPct: 'Earnings before interest, taxes, depreciation',
  // GTM
  CAC: 'Cost to acquire customer',
  WinRatePct: 'Deals won vs total',
  PipelineCoverageRatio: 'Pipeline vs quota',
  AvgSalesCycleDays: 'Average deal duration',
  AvgDealSize: 'Average contract value',
  ForecastAccuracyPct: 'Forecast vs actual',
  LeadToMQLPct: 'Lead to MQL conversion',
  SQLToClosePct: 'SQL to close conversion',
  // Customer Health
  NRR: 'Net revenue retention',
  GRR: 'Gross revenue retention',
  ChurnRatePct: 'Monthly logo churn',
  NPS: 'Net promoter score',
  CSAT: 'Customer satisfaction',
  TotalCustomers: 'Total customer count',
  ActiveCustomers: 'Active customer count',
  AtRiskCustomerCount: 'Accounts flagged at-risk',
  RenewalRate: 'Contract renewal rate',
  // Product/Technical
  UptimePct: 'Service availability',
  TechDebtLevel: 'Code quality rating',
  DeployFrequency: 'Deployments per month',
  TestCoveragePct: 'Code test coverage',
  ErrorRatePct: 'Application error rate',
  AvgResponseTimeMs: 'Mean time to respond',
  IntegrationFragilityScore: 'Integration stability score',
  // Operational
  SOPCoveragePct: 'Standard operating procedures',
  CRMDataAccuracyScore: 'Data quality score',
  OnboardingTimeDays: 'Onboarding duration',
  UtilizationRatePct: 'Resource utilization',
  TimeToValueDays: 'Time to first value',
  ServicesGrossMarginPct: 'Services margin',
  // Leadership
  FounderDailyInvolvementHours: 'Key person risk',
  FounderSalesDependencyPct: 'Founder in sales deals',
  LeadershipTeamSize: 'Leadership depth',
  TransitionReadinessScore: 'Transition readiness',
  DecisionCentralizationScore: 'Decision distribution',
  TurnoverRatePct: 'Leadership retention',
  // Ecosystem
  PrimaryERPDependencyPct: 'ERP platform dependency',
  PartnerSourcedRevenuePct: 'Partner-sourced revenue',
  IntegrationDepthScore: 'Integration depth',
  MarketplaceRanking: 'Marketplace position',
  ERPRoadmapAligned: 'ERP alignment status',
  MultiERPCapable: 'Multi-platform support',
  // Service/Software
  SoftwareRevenuePct: 'Software share of revenue',
  ImplementationEffortPerCustomer: 'Implementation effort',
  CustomizationFrequency: 'Customization frequency',
  ProductizationPotentialScore: 'Productization potential',
  ServicesRevenuePct: 'Services share of revenue',
};

// Helper functions
function getScoreColor(score: number): string {
  if (score >= 4.0) return 'hsl(var(--kpi-strong))';
  if (score >= 2.5) return 'hsl(var(--kpi-at-risk))';
  return 'hsl(var(--kpi-high-risk))';
}

function getStatusColor(status: 'green' | 'yellow' | 'red'): string {
  if (status === 'green') return 'hsl(var(--kpi-strong))';
  if (status === 'yellow') return 'hsl(var(--kpi-at-risk))';
  return 'hsl(var(--kpi-high-risk))';
}

function formatMetricValue(metric: Metric): string {
  const value = metric.current_value;
  if (value.numeric !== null) {
    if (value.unit === '%') return `${value.numeric.toFixed(1)}%`;
    if (value.unit === '$' || value.unit === 'USD') {
      if (value.numeric >= 1000000) return `$${(value.numeric / 1000000).toFixed(1)}M`;
      if (value.numeric >= 1000) return `$${(value.numeric / 1000).toFixed(0)}K`;
      return `$${value.numeric.toFixed(0)}`;
    }
    if (value.unit === 'days') return `${value.numeric.toFixed(0)} days`;
    if (value.unit === 'months') return `${value.numeric.toFixed(0)} mo`;
    return `${value.numeric}${value.unit || ''}`;
  }
  return value.text || '—';
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);

  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffWeeks < 4) return `${diffWeeks} week${diffWeeks > 1 ? 's' : ''} ago`;
  return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;
}

function getDocIcon(fileType: string): LucideIcon {
  const type = fileType?.toLowerCase() || '';
  if (type.includes('pdf')) return FileText;
  if (type.includes('xls') || type.includes('csv') || type.includes('spreadsheet')) return FileSpreadsheet;
  if (type.includes('doc')) return FileText;
  return File;
}

export default function AnalyticsPillarDetail() {
  const { pillarId } = useParams<{ pillarId: string }>();
  const navigate = useNavigate();
  const { selectedCompanyId } = useCompany();

  // Validate pillar ID
  const validPillar = pillarId as BDEPillar | undefined;
  const isValidPillar = validPillar && Object.keys(PILLAR_CONFIG).includes(validPillar);

  // Fetch data from API
  const { data: pillarDetail, isLoading: pillarLoading } = usePillarDetail(
    selectedCompanyId,
    isValidPillar ? validPillar : null
  );
  const { data: bdeScore, isLoading: scoreLoading } = useBDEScore(selectedCompanyId);
  const { data: flags, isLoading: flagsLoading } = useFlags(selectedCompanyId);
  const { data: metricsData, isLoading: metricsLoading } = useMetrics(selectedCompanyId);

  // Extended document info with pillar-specific metrics count
  interface PillarDocumentInfo extends SourceDocumentInfo {
    pillarMetricsCount: number;
    pillarConfidence: number;
  }

  // Fetch data sources (documents) filtered by pillar
  const [pillarDocuments, setPillarDocuments] = useState<PillarDocumentInfo[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);

  const fetchPillarDocuments = useCallback(async () => {
    if (!selectedCompanyId || !isValidPillar) return;

    setIsLoadingDocuments(true);
    try {
      // Get metrics with their source documents
      const metricsWithSources = await scoringApi.getMetricsWithSources(selectedCompanyId);

      // Track document IDs and their pillar-specific metrics count & confidence
      const documentMetrics = new Map<string, { count: number; confidenceSum: number }>();

      Object.values(metricsWithSources.metrics).forEach((metric) => {
        // Check if this metric belongs to the current pillar
        const belongsToPillar =
          metric.primary_pillar === validPillar ||
          metric.pillars_used_by?.includes(validPillar);

        if (belongsToPillar && metric.source_documents) {
          metric.source_documents.forEach((doc) => {
            const existing = documentMetrics.get(doc.document_id) || { count: 0, confidenceSum: 0 };
            existing.count += 1;
            existing.confidenceSum += metric.current_value?.confidence || 0;
            documentMetrics.set(doc.document_id, existing);
          });
        }
      });

      // Filter source documents and add pillar-specific metrics info
      const filteredDocuments: PillarDocumentInfo[] = metricsWithSources.source_documents
        .filter((doc) => documentMetrics.has(doc.id))
        .map((doc) => {
          const metrics = documentMetrics.get(doc.id)!;
          return {
            ...doc,
            pillarMetricsCount: metrics.count,
            pillarConfidence: metrics.count > 0 ? Math.round(metrics.confidenceSum / metrics.count) : 0,
          };
        });

      setPillarDocuments(filteredDocuments);
    } catch (err) {
      console.error('Failed to fetch pillar documents:', err);
      setPillarDocuments([]);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, [selectedCompanyId, validPillar, isValidPillar]);

  useEffect(() => {
    fetchPillarDocuments();
  }, [fetchPillarDocuments]);

  // Get pillar score from BDE score
  const pillarScore = useMemo(() => {
    if (!bdeScore?.pillar_scores || !validPillar) return null;
    return bdeScore.pillar_scores[validPillar];
  }, [bdeScore, validPillar]);

  // Get flags for this pillar
  const pillarFlags = useMemo(() => {
    if (!flags || !validPillar) return { risks: [], accelerants: [] };

    const risks = [
      ...flags.red_flags.filter(f => f.pillar === validPillar),
      ...flags.yellow_flags.filter(f => f.pillar === validPillar),
    ];
    const accelerants = flags.green_accelerants.filter(f => f.pillar === validPillar);

    return { risks, accelerants };
  }, [flags, validPillar]);

  // Get metrics for this pillar
  const pillarMetrics = useMemo(() => {
    if (!metricsData?.metrics || !validPillar) return [];

    const metricNames = PILLAR_METRICS[validPillar] || [];
    const result: Array<{ name: string; value: string; status: 'green' | 'yellow' | 'red'; description?: string }> = [];

    // Try to find each metric
    for (const name of metricNames) {
      // Search for metric by exact name first, then by partial match
      const metric = Object.entries(metricsData.metrics).find(([key]) =>
        key === name ||
        key.toLowerCase() === name.toLowerCase() ||
        key.toLowerCase().includes(name.toLowerCase()) ||
        name.toLowerCase().includes(key.toLowerCase())
      );

      if (metric) {
        const [metricKey, metricData] = metric;
        const value = formatMetricValue(metricData);

        // Determine status based on confidence or typical thresholds
        let status: 'green' | 'yellow' | 'red' = 'yellow';
        if (metricData.current_value.confidence >= 80) status = 'green';
        else if (metricData.current_value.confidence < 50) status = 'red';

        // Use display name if available, otherwise use the metric key
        const displayName = METRIC_DISPLAY_NAMES[metricKey] || METRIC_DISPLAY_NAMES[name] || name;

        result.push({
          name: displayName,
          value,
          status,
          description: METRIC_DESCRIPTIONS[metricKey] || METRIC_DESCRIPTIONS[name] || undefined,
        });
      }
    }

    return result;
  }, [metricsData, validPillar]);

  // Combined loading state
  const isLoading = pillarLoading || scoreLoading || flagsLoading || metricsLoading;

  // Show loading state while fetching data
  if (isLoading && !bdeScore && !pillarDetail) {
    return (
      <AppLayout title="Loading...">
        <PageLoader message="Loading pillar details..." size="lg" />
      </AppLayout>
    );
  }

  // Handle invalid pillar
  if (!isValidPillar) {
    return (
      <AppLayout title="Pillar Not Found">
        <div className={styles.notFound}>
          <h2>Pillar not found</h2>
          <p>The requested pillar does not exist.</p>
          <Button onClick={() => navigate('/analytics')}>
            <ArrowLeft size={16} />
            Back to Analytics
          </Button>
        </div>
      </AppLayout>
    );
  }

  const pillarConfig = PILLAR_CONFIG[validPillar];
  const PillarIcon = PILLAR_ICONS[validPillar];
  const recommendedDocs = RECOMMENDED_DOCUMENTS[validPillar] || [];

  // Use API data or fallback values
  const score = pillarDetail?.score ?? pillarScore?.score ?? 0;
  const confidence = pillarDetail?.confidence ?? pillarScore?.confidence ?? 0;
  const healthStatus = pillarDetail?.health_status ?? pillarScore?.health_status ?? 'yellow';

  // Combine API risks with flags
  const risks = pillarDetail?.risks?.length ? pillarDetail.risks : pillarFlags.risks.map(f => f.text);
  const accelerants = pillarDetail?.key_findings?.length ? pillarDetail.key_findings : pillarFlags.accelerants.map(f => f.text);

  return (
    <AppLayout title={pillarConfig.label}>
      <div className={styles.container}>
        {/* Page Header with border-b */}
        <header className={styles.pageHeader}>
          <div className={styles.pageHeaderInner}>
            {/* Back button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/analytics')}
              className={styles.backButton}
            >
              <ArrowLeft size={16} className="mr-2" />
              Back to Analytics
            </Button>

            {/* Header Content */}
            <div className={styles.header}>
              <div className={styles.headerLeft}>
                <div
                  className={styles.pillarIcon}
                  style={{ backgroundColor: `${pillarConfig.color}20` }}
                >
                  <PillarIcon size={24} style={{ color: pillarConfig.color }} />
                </div>
                <div>
                  <p className={styles.pillarShortName}>{PILLAR_SHORT_NAMES[validPillar]}</p>
                  <h1 className={styles.pillarName}>{pillarConfig.label}</h1>
                  <p className={styles.pillarDescription}>{PILLAR_DESCRIPTIONS[validPillar]}</p>
                </div>
              </div>
              <div className={styles.headerRight}>
                <div className={styles.scoreBox}>
                  <p className={styles.scoreLabel}>Score</p>
                  <p
                    className={styles.scoreValue}
                    style={{ color: getScoreColor(score) }}
                  >
                    {score.toFixed(1)}
                  </p>
                </div>
                <div className={styles.scoreBox}>
                  <p className={styles.scoreLabel}>Confidence</p>
                  <p className={styles.scoreValueSmall}>{confidence.toFixed(0)}%</p>
                </div>
                <div className={styles.scoreBox}>
                  <p className={styles.scoreLabel}>Weight</p>
                  <p className={styles.scoreValueSmall}>{(pillarConfig.weight * 100).toFixed(0)}%</p>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Page Main Content */}
        <main className={styles.pageMain}>
          <div className={styles.pageMainInner}>
            {/* Trend Summary Bar */}
            <div className={styles.summaryBar}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Trend:</span>
            <div className={cn(
              styles.summaryValue,
              healthStatus === 'green' && styles.trendUp,
              healthStatus === 'red' && styles.trendDown
            )}>
              {healthStatus === 'green' && <><TrendingUp size={14} /> Improving</>}
              {healthStatus === 'yellow' && <><Minus size={14} /> Stable</>}
              {healthStatus === 'red' && <><TrendingDown size={14} /> Declining</>}
            </div>
          </div>
          <div className={styles.summaryDivider} />
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Documents:</span>
            <span className={styles.summaryValue}>
              {isLoadingDocuments ? '...' : `${pillarDocuments.length} files`}
            </span>
          </div>
          <div className={styles.summaryDivider} />
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Risks:</span>
            <span className={cn(styles.summaryValue, styles.riskCount)}>{risks.length}</span>
          </div>
          <div className={styles.summaryDivider} />
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Accelerants:</span>
            <span className={cn(styles.summaryValue, styles.accelerantCount)}>{accelerants.length}</span>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIndicator} />
            <h2 className={styles.sectionTitle}>Key Metrics</h2>
          </div>
          {pillarMetrics.length > 0 ? (
            <div className={styles.metricsGrid}>
              {pillarMetrics.map((metric) => (
                <div key={metric.name} className={styles.metricCard}>
                  <p className={styles.metricName}>{metric.name}</p>
                  <p
                    className={styles.metricValue}
                    style={{ color: getStatusColor(metric.status) }}
                  >
                    {metric.value}
                  </p>
                  {metric.description && (
                    <p className={styles.metricDescription}>{metric.description}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptyMetrics}>
              <Info size={20} />
              <p>No metrics data available. Upload relevant documents to extract metrics.</p>
            </div>
          )}
        </section>

        {/* Related Documents Section */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIndicator} />
            <h2 className={styles.sectionTitle}>Related Documents</h2>
          </div>
          {pillarDocuments.length > 0 ? (
            <div className={styles.relatedDocumentsList}>
              {pillarDocuments.map((doc) => {
                const DocIcon = getDocIcon(doc.file_type);
                const isProcessed = doc.status === 'processed' || doc.status === 'completed';
                const isPending = doc.status === 'pending' || doc.status === 'processing';
                const isError = doc.status === 'error' || doc.status === 'failed';

                return (
                  <div key={doc.id} className={styles.relatedDocItem}>
                    <div className={styles.relatedDocLeft}>
                      <div className={styles.relatedDocIcon}>
                        <DocIcon size={16} />
                      </div>
                      <div className={styles.relatedDocInfo}>
                        <p className={styles.relatedDocName}>{doc.original_filename || doc.filename}</p>
                        <div className={styles.relatedDocMeta}>
                          <Clock size={12} />
                          <span>{formatRelativeTime(doc.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                    <div className={styles.relatedDocRight}>
                      <div className={styles.relatedDocStat}>
                        <p className={styles.relatedDocStatLabel}>Pillar Metrics</p>
                        <p className={styles.relatedDocStatValue}>{doc.pillarMetricsCount} metrics</p>
                      </div>
                      <div className={styles.relatedDocStat}>
                        <p className={styles.relatedDocStatLabel}>Confidence</p>
                        <p className={cn(
                          styles.relatedDocStatValue,
                          doc.pillarConfidence >= 80 && styles.confidenceHigh,
                          doc.pillarConfidence >= 50 && doc.pillarConfidence < 80 && styles.confidenceMedium,
                          doc.pillarConfidence < 50 && styles.confidenceLow
                        )}>
                          {doc.pillarConfidence > 0 ? `${doc.pillarConfidence}%` : '—'}
                        </p>
                      </div>
                      <div className={styles.relatedDocStatus}>
                        {isProcessed && <CheckCircle2 size={16} className={styles.statusProcessed} />}
                        {isPending && <Clock size={16} className={styles.statusPending} />}
                        {isError && <AlertCircle size={16} className={styles.statusError} />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={styles.emptyState}>
              <FileText size={20} />
              <p>
                {isLoadingDocuments
                  ? 'Loading documents...'
                  : 'No documents contributing to this pillar yet'}
              </p>
            </div>
          )}
        </section>

        {/* Recommended Documents Section */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIndicator} />
            <h2 className={styles.sectionTitle}>Recommended Documents to Upload</h2>
            <span className={styles.sectionHint}>Upload these to improve accuracy</span>
          </div>
          <div className={styles.documentsList}>
            {recommendedDocs.map((doc, index) => {
              const DocIcon = DOC_TYPE_ICONS[doc.type] || File;
              return (
                <div key={index} className={styles.documentItem}>
                  <div className={styles.documentLeft}>
                    <div className={cn(
                      styles.documentIcon,
                      doc.priority === 'required' && styles.iconRequired,
                      doc.priority === 'recommended' && styles.iconRecommended
                    )}>
                      <DocIcon size={16} />
                    </div>
                    <div className={styles.documentInfo}>
                      <div className={styles.documentHeader}>
                        <span className={styles.documentName}>{doc.name}</span>
                        <span className={cn(
                          styles.priorityBadge,
                          doc.priority === 'required' && styles.badgeRequired,
                          doc.priority === 'recommended' && styles.badgeRecommended,
                          doc.priority === 'optional' && styles.badgeOptional
                        )}>
                          {doc.priority === 'required' && <Star size={10} />}
                          {doc.priority === 'recommended' && <CircleDot size={10} />}
                          {doc.priority === 'optional' && <Info size={10} />}
                          {doc.priority}
                        </span>
                      </div>
                      <p className={styles.documentDescription}>{doc.description}</p>
                      <p className={styles.documentImpact}>
                        <Zap size={12} />
                        {doc.impact}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/ingestion')}
                  >
                    <Upload size={14} />
                    Upload
                  </Button>
                </div>
              );
            })}
          </div>
        </section>

        {/* Risks & Accelerants */}
        <div className={styles.twoColumnGrid}>
          {/* Risks */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIndicator} style={{ backgroundColor: 'hsl(var(--kpi-high-risk))' }} />
              <h2 className={cn(styles.sectionTitle, styles.riskTitle)}>Risks</h2>
            </div>
            {risks.length > 0 ? (
              <div className={styles.risksList}>
                {risks.map((risk, index) => (
                  <div key={index} className={styles.riskItem}>
                    <AlertTriangle size={16} />
                    <span>{risk}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <CheckCircle2 size={20} />
                <p>No significant risks identified</p>
              </div>
            )}
          </section>

          {/* Accelerants */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIndicator} style={{ backgroundColor: 'hsl(var(--kpi-strong))' }} />
              <h2 className={cn(styles.sectionTitle, styles.accelerantTitle)}>Accelerants</h2>
            </div>
            {accelerants.length > 0 ? (
              <div className={styles.accelerantsList}>
                {accelerants.map((accelerant, index) => (
                  <div key={index} className={styles.accelerantItem}>
                    <Zap size={16} />
                    <span>{accelerant}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <Info size={20} />
                <p>No accelerants identified yet</p>
              </div>
            )}
          </section>
        </div>

        {/* Justification */}
        {pillarDetail?.justification && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIndicator} />
              <h2 className={styles.sectionTitle}>Score Justification</h2>
            </div>
            <div className={styles.justificationCard}>
              <p>{pillarDetail.justification}</p>
            </div>
          </section>
        )}
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
