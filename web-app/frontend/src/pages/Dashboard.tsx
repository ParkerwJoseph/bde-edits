import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AppLayout } from '../components/layout/AppLayout';
import styles from '../styles/Dashboard.module.css';
import { companyApi } from '../api/companyApi';
import type { Company } from '../api/companyApi';
import { scoringApi } from '../api/scoringApi';
import type { BDEScoreResponse, MetricsResponse, FlagsResponse } from '../api/scoringApi';
import {
  ScoreGauge,
  PillarScoreBar,
  RiskRadar,
  QuickStats,
  DataCoverage,
  CustomerHealthPanel,
  ProductHealthPanel,
  AnalysisProgress,
} from '../components/dashboard';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const userName = user?.display_name || user?.email || 'User';

  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Scoring data
  const [scoreData, setScoreData] = useState<BDEScoreResponse | null>(null);
  const [metricsData, setMetricsData] = useState<MetricsResponse | null>(null);
  const [flagsData, setFlagsData] = useState<FlagsResponse | null>(null);
  const [scoringLoading, setScoringLoading] = useState(false);

  // Fetch companies on mount
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const response = await companyApi.list();
        setCompanies(response.companies);
        if (response.companies.length > 0) {
          setSelectedCompanyId(response.companies[0].id);
        }
      } catch (err) {
        setError('Failed to load companies');
      } finally {
        setLoading(false);
      }
    };

    fetchCompanies();
  }, []);

  // Fetch scoring data
  const fetchScoringData = async () => {
    if (!selectedCompanyId) return;

    setScoringLoading(true);
    try {
      const [scores, metrics, flags] = await Promise.all([
        scoringApi.getBDEScore(selectedCompanyId).catch(() => null),
        scoringApi.getMetrics(selectedCompanyId).catch(() => null),
        scoringApi.getFlags(selectedCompanyId).catch(() => null),
      ]);
      setScoreData(scores);
      setMetricsData(metrics);
      setFlagsData(flags);
    } catch (err) {
      console.error('Failed to fetch scoring data:', err);
    } finally {
      setScoringLoading(false);
    }
  };

  // Fetch scoring data when company changes
  useEffect(() => {
    fetchScoringData();
  }, [selectedCompanyId]);

  // Callback when analysis completes - refresh scoring data
  const handleAnalysisComplete = () => {
    fetchScoringData();
  };

  const handleCompanyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedCompanyId(e.target.value);
  };

  const handleRiskClick = () => {
    if (selectedCompanyId) {
      navigate(`/scoring/${selectedCompanyId}/risk-radar`);
    }
  };

  const handleQuickStatsClick = () => {
    if (selectedCompanyId) {
      navigate(`/scoring/${selectedCompanyId}/quick-stats`);
    }
  };

  const handleCustomerHealthClick = () => {
    if (selectedCompanyId) {
      navigate(`/scoring/${selectedCompanyId}/customer-health`);
    }
  };

  const handleProductHealthClick = () => {
    if (selectedCompanyId) {
      navigate(`/scoring/${selectedCompanyId}/product-health`);
    }
  };

  if (loading) {
    return (
      <AppLayout title="Dashboard">
        <div className={styles.loadingState}>Loading...</div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout title="Dashboard">
        <div className={styles.error}>{error}</div>
      </AppLayout>
    );
  }

  if (companies.length === 0) {
    return (
      <AppLayout title="Dashboard">
        <div className={styles.welcomeCard}>
          <h2 className={styles.welcomeTitle}>Welcome back, {userName}!</h2>
          <p className={styles.welcomeText}>Here's an overview of your business dashboard.</p>
        </div>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📊</div>
          <h3 className={styles.emptyTitle}>No Companies Found</h3>
          <p className={styles.emptyText}>Create a company to get started with scoring.</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Dashboard">
      {/* Company Selector */}
      <div className={styles.companySelectorWrapper}>
        <label className={styles.companySelectorLabel}>Company:</label>
        <select
          className={styles.companySelector}
          value={selectedCompanyId || ''}
          onChange={handleCompanyChange}
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
      </div>

      {/* Analysis Progress / Run Analysis Button */}
      {selectedCompanyId && (
        <AnalysisProgress
          companyId={selectedCompanyId}
          onComplete={handleAnalysisComplete}
        />
      )}

      {scoringLoading ? (
        <div className={styles.loadingState}>Loading scoring data...</div>
      ) : !scoreData ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📊</div>
          <h3 className={styles.emptyTitle}>No Scoring Data</h3>
          <p className={styles.emptyText}>Upload documents and run analysis to see results.</p>
        </div>
      ) : (
        <div className={styles.dashboardGrid}>
          {/* Score Gauge */}
          <div className={styles.gaugeSection}>
            <ScoreGauge
              score={scoreData.overall_score}
              subtitle={`Confidence: ${scoreData.confidence}%`}
            />
            <div className={styles.valuationRange}>
              <span className={styles.valuationLabel}>Valuation Range:</span>
              <span className={styles.valuationValue}>{scoreData.valuation_range}</span>
            </div>
          </div>

          {/* Pillar Scores */}
          <div className={styles.pillarSection}>
            <PillarScoreBar
              pillarScores={scoreData.pillar_scores}
              companyId={selectedCompanyId}
            />
          </div>

          {/* Risk Radar */}
          <div className={styles.riskSection} onClick={handleRiskClick}>
            <h3 className={styles.sectionTitle}>Risk Radar</h3>
            {flagsData ? (
              <RiskRadar flags={flagsData} companyId={selectedCompanyId} />
            ) : (
              <div className={styles.placeholderState}>No risk data available</div>
            )}
          </div>

          {/* Quick Stats */}
          <div className={styles.statsSection} onClick={handleQuickStatsClick}>
            <h3 className={styles.sectionTitle}>Quick Stats</h3>
            {metricsData ? (
              <QuickStats metrics={metricsData} companyId={selectedCompanyId} />
            ) : (
              <div className={styles.placeholderState}>No metrics available</div>
            )}
          </div>

          {/* Data Coverage */}
          <div className={styles.coverageSection}>
            <h3 className={styles.sectionTitle}>Data Coverage</h3>
            <DataCoverage pillarScores={scoreData.pillar_scores} />
          </div>

          {/* Customer Health */}
          <div className={styles.customerSection} onClick={handleCustomerHealthClick}>
            <h3 className={styles.sectionTitle}>Customer Health</h3>
            {metricsData ? (
              <CustomerHealthPanel metrics={metricsData} companyId={selectedCompanyId} />
            ) : (
              <div className={styles.placeholderState}>No customer data available</div>
            )}
          </div>

          {/* Product Health */}
          <div className={styles.productSection} onClick={handleProductHealthClick}>
            <h3 className={styles.sectionTitle}>Product Health</h3>
            {metricsData ? (
              <ProductHealthPanel metrics={metricsData} companyId={selectedCompanyId} />
            ) : (
              <div className={styles.placeholderState}>No product data available</div>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
