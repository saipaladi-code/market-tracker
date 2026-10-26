import axios from 'axios';
import {
  DashboardStats,
  Article,
  SentimentAnalysisResult,
  CompanySummary,
  ConflictSignal,
  SectorSentiment,
  AlertRecord,
  DataQualityReport,
  AssistantChatResponse
} from '../types';
import {
  MOCK_ARTICLES,
  MOCK_DASHBOARD_STATS,
  MOCK_COMPANIES,
  MOCK_SECTORS,
  MOCK_CONFLICTS,
  MOCK_ALERTS,
  MOCK_HISTORY,
  MOCK_DATA_QUALITY,
  MOCK_HEALTH,
  simulateFinbertAnalysis,
  simulateAssistantChat,
} from './mockData';

const STORAGE_KEY = 'FIN_SENTIMENT_API_URL';

export function getStoredApiUrl(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && saved.trim()) return saved.trim();
  } catch {
    // localStorage not accessible
  }
  if (import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.trim()) {
    return import.meta.env.VITE_API_URL.trim();
  }
  // If running in production mode or on a deployed domain (such as Vercel), default to the deployed backend
  if (
    import.meta.env.PROD ||
    (typeof window !== 'undefined' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1')
  ) {
    return 'https://market-tracker-c6ou.onrender.com';
  }
  return 'http://localhost:8000';
}

let currentBaseUrl = getStoredApiUrl();
let client = axios.create({
  baseURL: currentBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 25000, // 25s timeout to accommodate cloud container spin-up and network latency
});

let isOfflineMode = false;
const listeners: Array<(offline: boolean) => void> = [];

function setOfflineStatus(offline: boolean) {
  if (isOfflineMode !== offline) {
    isOfflineMode = offline;
    listeners.forEach((cb) => cb(isOfflineMode));
  }
}

export const api = {
  getBaseUrl: (): string => currentBaseUrl,

  setBaseUrl: (newUrl: string) => {
    currentBaseUrl = newUrl.trim();
    try {
      localStorage.setItem(STORAGE_KEY, currentBaseUrl);
    } catch {}
    client = axios.create({
      baseURL: currentBaseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 25000,
    });
  },

  resetBaseUrl: () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
    currentBaseUrl = getStoredApiUrl();
    client = axios.create({
      baseURL: currentBaseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 25000,
    });
  },

  isOffline: (): boolean => isOfflineMode,

  subscribeStatus: (cb: (offline: boolean) => void) => {
    listeners.push(cb);
    return () => {
      const idx = listeners.indexOf(cb);
      if (idx !== -1) listeners.splice(idx, 1);
    };
  },

  testConnection: async (targetUrl?: string): Promise<{ success: boolean; latency?: number; message?: string }> => {
    const url = (targetUrl || currentBaseUrl).replace(/\/+$/, '');
    const start = performance.now();
    try {
      const res = await axios.get(`${url}/api/health`, { timeout: 15000 });
      const latency = Math.round(performance.now() - start);
      if (res.status === 200) {
        setOfflineStatus(false);
        return { success: true, latency, message: 'Connected successfully to backend service.' };
      }
      return { success: false, message: `Unexpected status code: ${res.status}` };
    } catch (err: any) {
      return {
        success: false,
        message: err?.response?.data?.detail || err?.message || 'Failed to connect. Check CORS or URL.',
      };
    }
  },

  // Health
  getHealth: async () => {
    try {
      const res = await client.get('/api/health');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return MOCK_HEALTH;
    }
  },

  // Dashboard Stats
  getDashboardStats: async (): Promise<DashboardStats> => {
    try {
      const res = await client.get('/api/dashboard/stats');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      console.warn('Backend unavailable for dashboard stats. Falling back to demo intelligence:', err);
      setOfflineStatus(true);
      return {
        ...MOCK_DASHBOARD_STATS,
        is_demo_dataset: true,
      };
    }
  },

  // News Explorer
  getNews: async (params?: {
    page?: number;
    page_size?: number;
    company?: string;
    sentiment?: string;
    query?: string;
  }) => {
    try {
      const res = await client.get('/api/news', { params });
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      console.warn('Backend unavailable for news. Falling back to demo data:', err);
      setOfflineStatus(true);

      let items = [...MOCK_ARTICLES];
      if (params?.company && params.company !== 'All Companies') {
        items = items.filter((a) => a.company.toLowerCase() === params.company!.toLowerCase());
      }
      if (params?.sentiment && params.sentiment !== 'all') {
        items = items.filter((a) => a.sentiment?.toLowerCase() === params.sentiment!.toLowerCase());
      }
      if (params?.query) {
        const q = params.query.toLowerCase();
        items = items.filter((a) => a.title.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q));
      }

      const page = params?.page || 1;
      const pageSize = params?.page_size || 12;
      const paginated = items.slice((page - 1) * pageSize, page * pageSize);

      return {
        articles: paginated,
        total_count: items.length,
        page,
        page_size: pageSize,
        is_demo_dataset: true,
      };
    }
  },

  refreshNews: async () => {
    try {
      const res = await client.post('/api/news/refresh');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return {
        message: 'Refreshed 15 demo articles in standalone mode.',
        articles_count: MOCK_ARTICLES.length,
        new_alerts_count: 0,
        is_demo_dataset: true,
      };
    }
  },

  // FinBERT Sentiment Analysis
  analyzeHeadline: async (text: string): Promise<SentimentAnalysisResult> => {
    try {
      const res = await client.post('/api/analyze', { text });
      setOfflineStatus(false);
      return res.data;
    } catch (err: any) {
      if (err?.response?.status === 422 || err?.response?.data?.error_code) {
        // Backend HTTP 422 validation failure: rethrow directly to caller
        throw err;
      }
      console.warn('Backend unavailable for FinBERT inference. Using simulated inference:', err);
      setOfflineStatus(true);
      return simulateFinbertAnalysis(text);
    }
  },

  analyzeBatch: async (texts: string[]): Promise<SentimentAnalysisResult[]> => {
    try {
      const res = await client.post('/api/analyze/batch', { texts });
      setOfflineStatus(false);
      return res.data;
    } catch (err: any) {
      if (err?.response?.status === 422 || err?.response?.data?.error_code) {
        throw err;
      }
      setOfflineStatus(true);
      return texts.map(simulateFinbertAnalysis);
    }
  },

  // Companies
  getCompanies: async (): Promise<CompanySummary[]> => {
    try {
      const res = await client.get('/api/companies');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return MOCK_COMPANIES;
    }
  },

  getCompanyDetail: async (company: string) => {
    try {
      const res = await client.get(`/api/companies/${encodeURIComponent(company)}/sentiment`);
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      const compSummary = MOCK_COMPANIES.find(
        (c) => c.company.toLowerCase() === company.toLowerCase()
      ) || MOCK_COMPANIES[0];

      const compArts = MOCK_ARTICLES.filter(
        (a) => a.company.toLowerCase() === compSummary.company.toLowerCase() && !a.is_duplicate
      );

      const conflict = MOCK_CONFLICTS.find(
        (c) => c.company.toLowerCase() === compSummary.company.toLowerCase()
      ) || null;

      return {
        company: compSummary.company,
        total_articles: compArts.length,
        articles: compArts,
        positive_count: compSummary.positive_count,
        negative_count: compSummary.negative_count,
        neutral_count: compSummary.neutral_count,
        positive_pct: compSummary.positive_pct,
        negative_pct: compSummary.negative_pct,
        neutral_pct: compSummary.neutral_pct,
        conflict,
        history: MOCK_HISTORY,
      };
    }
  },

  // Conflict Detector
  getConflicts: async (): Promise<ConflictSignal[]> => {
    try {
      const res = await client.get('/api/conflicts');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return MOCK_CONFLICTS;
    }
  },

  // Sectors Heatmap
  getSectors: async (): Promise<SectorSentiment[]> => {
    try {
      const res = await client.get('/api/sentiment/sectors');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return MOCK_SECTORS;
    }
  },

  // History & Alerts
  getHistory: async (company?: string) => {
    try {
      const res = await client.get('/api/sentiment/history', { params: { company } });
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return MOCK_HISTORY;
    }
  },

  getAlerts: async (unreadOnly = false): Promise<AlertRecord[]> => {
    try {
      const res = await client.get('/api/alerts', { params: { unread_only: unreadOnly } });
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return unreadOnly ? MOCK_ALERTS.filter((a) => !a.is_read) : MOCK_ALERTS;
    }
  },

  markAlertRead: async (alertId: string) => {
    try {
      const res = await client.patch(`/api/alerts/${encodeURIComponent(alertId)}`);
      return res.data;
    } catch (err) {
      return { success: true };
    }
  },

  // Data Quality
  getDataQuality: async (): Promise<DataQualityReport> => {
    try {
      const res = await client.get('/api/data-quality');
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return MOCK_DATA_QUALITY;
    }
  },

  // AI Financial Assistant
  chatAssistant: async (message: string, companyFocus?: string): Promise<AssistantChatResponse> => {
    try {
      const res = await client.post('/api/assistant/chat', { message, company_focus: companyFocus });
      setOfflineStatus(false);
      return res.data;
    } catch (err) {
      setOfflineStatus(true);
      return simulateAssistantChat(message, companyFocus);
    }
  },
};
