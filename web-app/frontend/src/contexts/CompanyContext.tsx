/**
 * CompanyContext
 *
 * Provides selected company state and company list to the entire application.
 * Manages localStorage persistence for the selected company.
 * Only fetches companies when user is authenticated.
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { companyApi, type Company } from '../api/companyApi';
import { STORAGE_KEYS } from '../lib/constants';
import { useAuth } from '../context/AuthContext';

interface CompanyContextValue {
  /** Currently selected company ID */
  selectedCompanyId: string | null;
  /** Currently selected company object */
  selectedCompany: Company | null;
  /** List of all companies */
  companies: Company[];
  /** Whether companies are loading */
  isLoading: boolean;
  /** Error if company fetch failed */
  error: Error | null;
  /** Select a company */
  selectCompany: (companyId: string) => void;
  /** Refresh the companies list */
  refreshCompanies: () => Promise<void>;
  /** Add a new company to the list */
  addCompany: (company: Company) => void;
}

const CompanyContext = createContext<CompanyContextValue | undefined>(undefined);

export interface CompanyProviderProps {
  children: ReactNode;
}

export function CompanyProvider({ children }: CompanyProviderProps) {
  const { user, loading: authLoading } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEYS.selectedCompany);
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Fetch companies only when user is authenticated
  const fetchCompanies = useCallback(async () => {
    // Don't fetch if not authenticated
    if (!user) {
      setCompanies([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await companyApi.list();
      setCompanies(response.companies);

      // If no company selected, select the first one
      if (!selectedCompanyId && response.companies.length > 0) {
        const firstCompanyId = response.companies[0].id;
        setSelectedCompanyId(firstCompanyId);
        localStorage.setItem(STORAGE_KEYS.selectedCompany, firstCompanyId);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch companies'));
    } finally {
      setIsLoading(false);
    }
  }, [user, selectedCompanyId]);

  // Fetch companies when user changes (login/logout)
  useEffect(() => {
    if (!authLoading) {
      fetchCompanies();
    }
  }, [authLoading, fetchCompanies]);

  // Get selected company object
  const selectedCompany = companies.find((c) => c.id === selectedCompanyId) || null;

  // Select a company
  const selectCompany = useCallback((companyId: string) => {
    setSelectedCompanyId(companyId);
    localStorage.setItem(STORAGE_KEYS.selectedCompany, companyId);
  }, []);

  // Add a new company
  const addCompany = useCallback((company: Company) => {
    setCompanies((prev) => [...prev, company]);
  }, []);

  const value: CompanyContextValue = {
    selectedCompanyId,
    selectedCompany,
    companies,
    isLoading,
    error,
    selectCompany,
    refreshCompanies: fetchCompanies,
    addCompany,
  };

  return (
    <CompanyContext.Provider value={value}>
      {children}
    </CompanyContext.Provider>
  );
}

export function useCompany(): CompanyContextValue {
  const context = useContext(CompanyContext);
  if (!context) {
    throw new Error('useCompany must be used within a CompanyProvider');
  }
  return context;
}
