/**
 * BDE UI V2 - Core Constants
 *
 * This file contains the 8-pillar configuration, score thresholds,
 * and other constants used throughout the application.
 */

import type { LucideIcon } from 'lucide-react';
import {
  DollarSign,
  Target,
  Users,
  Wrench,
  BarChart3,
  Briefcase,
  Network,
  ArrowRightLeft,
} from 'lucide-react';

// ===== Pillar Types =====
export type PillarId =
  | 'financial_health'
  | 'gtm_engine'
  | 'customer_health'
  | 'product_technical'
  | 'operational_maturity'
  | 'leadership_transition'
  | 'ecosystem_dependency'
  | 'service_software_ratio';

export interface PillarConfig {
  id: PillarId;
  name: string;
  shortName: string;
  description: string;
  weight: number;
  order: number;
  color: string;
}

// ===== 8 Pillars Configuration =====
export const PILLARS: Record<PillarId, PillarConfig> = {
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
};

// ===== Pillar Icons Mapping =====
export const PILLAR_ICONS: Record<PillarId, LucideIcon> = {
  financial_health: DollarSign,
  gtm_engine: Target,
  customer_health: Users,
  product_technical: Wrench,
  operational_maturity: BarChart3,
  leadership_transition: Briefcase,
  ecosystem_dependency: Network,
  service_software_ratio: ArrowRightLeft,
};

// ===== Ordered Pillars Array =====
export const PILLARS_ORDERED = Object.values(PILLARS).sort((a, b) => a.order - b.order);

// ===== Score Thresholds (0-5 scale) =====
export const SCORE_THRESHOLDS = {
  green: { min: 3.5 },   // 3.5-5.0 = Healthy / Strong
  yellow: { min: 2.5 },  // 2.5-3.5 = Needs Attention / Moderate
  red: { max: 2.5 },     // 0-2.5 = At Risk / Critical
} as const;

// ===== Confidence Thresholds (0-100 scale) =====
export const CONFIDENCE_THRESHOLDS = {
  high: { min: 80 },    // 80-100 = High confidence
  medium: { min: 50 },  // 50-80 = Moderate confidence
  low: { max: 50 },     // 0-50 = Low confidence
} as const;

// ===== Exit Readiness Thresholds (0-100 scale) =====
export const EXIT_READINESS_THRESHOLDS = {
  ready: { min: 71 },       // 71-100 = Exit Ready
  conditional: { min: 31 }, // 31-70 = Conditional
  notReady: { max: 31 },    // 0-30 = Not Ready
} as const;

// ===== Valuation Bands =====
export interface ValuationBand {
  band: string;
  minScore: number;
  multiples: { low: number; high: number };
}

export const VALUATION_BANDS: ValuationBand[] = [
  { band: 'Premium', minScore: 4.5, multiples: { low: 8, high: 12 } },
  { band: 'Strong', minScore: 4.0, multiples: { low: 6, high: 8 } },
  { band: 'Average', minScore: 3.0, multiples: { low: 4, high: 6 } },
  { band: 'Below Average', minScore: 2.0, multiples: { low: 2, high: 4 } },
  { band: 'Distressed', minScore: 0, multiples: { low: 0.5, high: 2 } },
];

// ===== Score Colors =====
export const SCORE_COLORS = {
  green: {
    base: '#22c55e',
    bg: 'rgba(34, 197, 94, 0.1)',
    border: 'rgba(34, 197, 94, 0.3)',
    text: '#22c55e',
  },
  yellow: {
    base: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.1)',
    border: 'rgba(245, 158, 11, 0.3)',
    text: '#f59e0b',
  },
  red: {
    base: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.1)',
    border: 'rgba(239, 68, 68, 0.3)',
    text: '#ef4444',
  },
} as const;

export type ScoreColor = keyof typeof SCORE_COLORS;

// ===== Risk Severity =====
export const RISK_SEVERITY = {
  critical: { label: 'Critical', color: 'red', priority: 1 },
  high: { label: 'High', color: 'red', priority: 2 },
  medium: { label: 'Medium', color: 'yellow', priority: 3 },
  low: { label: 'Low', color: 'green', priority: 4 },
} as const;

export type RiskSeverity = keyof typeof RISK_SEVERITY;

// ===== Trend Directions =====
export type TrendDirection = 'up' | 'down' | 'flat';

// ===== Default KPIs by Pillar =====
export const DEFAULT_KPIS: Record<PillarId, string[]> = {
  financial_health: ['ARR', 'MRR', 'Gross Margin', 'EBITDA', 'DSO', 'Runway'],
  gtm_engine: ['Pipeline Coverage', 'Win Rate', 'Sales Cycle', 'CAC', 'CAC Payback'],
  customer_health: ['GRR', 'NRR', 'Churn Rate', 'NPS', 'CSAT', 'LTV'],
  product_technical: ['Uptime', 'P95 Latency', 'Error Rate', 'Release Cadence', 'Tech Debt Ratio'],
  operational_maturity: ['SLA Compliance', 'Automation Rate', 'Onboarding TTV', 'Process Maturity'],
  leadership_transition: ['Founder Dependency', 'Bench Strength', 'Key Person Risk', 'Governance Score'],
  ecosystem_dependency: ['Integration Health', 'Platform Risk', 'API Coverage', 'Vendor Concentration'],
  service_software_ratio: ['Software Revenue %', 'Services GM', 'Productization Score', 'Recurring %'],
};

// ===== Metric Units =====
export const METRIC_UNITS = {
  currency: ['$', 'USD', 'K', 'M'],
  percentage: ['%'],
  time: ['days', 'd', 'months', 'mo', 'hours', 'h'],
  ratio: ['x', '×'],
  count: ['count', '#'],
} as const;

// ===== LocalStorage Keys =====
export const STORAGE_KEYS = {
  analyticsLayout: 'bde-analytics-dashboard-layout',
  selectedCompany: 'bde-selected-company',
  sidebarCollapsed: 'bde-sidebar-collapsed',
  theme: 'bde-theme',
} as const;
