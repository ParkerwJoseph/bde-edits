/**
 * useScoring Hooks
 *
 * Custom hooks for fetching BDE scoring data from the API.
 * Provides loading states, error handling, and automatic refetching.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  scoringApi,
  type BDEScoreResponse,
  type FlagsResponse,
  type RecommendationResponse,
  type AnalysisStatusResponse,
  type MetricsResponse,
  type BDEPillar,
  type PillarDetailResponse,
} from '../api/scoringApi';

// Generic fetch state
interface FetchState<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook for fetching BDE score data for a company
 */
export function useBDEScore(companyId: string | null): FetchState<BDEScoreResponse> {
  const [data, setData] = useState<BDEScoreResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!companyId) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await scoringApi.getBDEScore(companyId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch BDE score'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * Hook for fetching flags (red, yellow, green) for a company
 */
export function useFlags(companyId: string | null): FetchState<FlagsResponse> {
  const [data, setData] = useState<FlagsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!companyId) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await scoringApi.getFlags(companyId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch flags'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * Hook for fetching recommendation for a company
 */
export function useRecommendation(companyId: string | null): FetchState<RecommendationResponse> {
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!companyId) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await scoringApi.getRecommendation(companyId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch recommendation'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * Hook for fetching analysis status for a company
 */
export function useAnalysisStatus(companyId: string | null): FetchState<AnalysisStatusResponse> {
  const [data, setData] = useState<AnalysisStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!companyId) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await scoringApi.getAnalysisStatus(companyId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch analysis status'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * Hook for fetching all metrics for a company
 */
export function useMetrics(companyId: string | null): FetchState<MetricsResponse> {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!companyId) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await scoringApi.getMetrics(companyId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch metrics'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * Hook for fetching detailed pillar information
 */
export function usePillarDetail(
  companyId: string | null,
  pillar: BDEPillar | null
): FetchState<PillarDetailResponse> {
  const [data, setData] = useState<PillarDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!companyId || !pillar) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await scoringApi.getPillarDetail(companyId, pillar);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch pillar detail'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, pillar]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * Combined hook for fetching all home page data
 */
export interface HomePageData {
  score: BDEScoreResponse | null;
  flags: FlagsResponse | null;
  recommendation: RecommendationResponse | null;
  analysisStatus: AnalysisStatusResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetchAll: () => Promise<void>;
}

export function useHomePageData(companyId: string | null): HomePageData {
  const [score, setScore] = useState<BDEScoreResponse | null>(null);
  const [flags, setFlags] = useState<FlagsResponse | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchAll = useCallback(async () => {
    if (!companyId) {
      setScore(null);
      setFlags(null);
      setRecommendation(null);
      setAnalysisStatus(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Fetch all data in parallel
      const [scoreRes, flagsRes, recommendationRes, statusRes] = await Promise.all([
        scoringApi.getBDEScore(companyId).catch(() => null),
        scoringApi.getFlags(companyId).catch(() => null),
        scoringApi.getRecommendation(companyId).catch(() => null),
        scoringApi.getAnalysisStatus(companyId).catch(() => null),
      ]);

      setScore(scoreRes);
      setFlags(flagsRes);
      setRecommendation(recommendationRes);
      setAnalysisStatus(statusRes);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch home page data'));
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return {
    score,
    flags,
    recommendation,
    analysisStatus,
    isLoading,
    error,
    refetchAll: fetchAll,
  };
}
