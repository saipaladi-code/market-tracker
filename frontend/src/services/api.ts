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
  AssistantChatResponse,
  NewsResponse,
  FeedStatus,
  User,
  AuthResponse,
  ForgotPasswordResponse,
  MessageResponse
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
import { getCanonicalSentimentResult, mergeExplanationTokens } from '../utils/canonicalSentiment';

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

const AUTH_TOKEN_KEY = 'FIN_SENTIMENT_AUTH_TOKEN';
const USER_PROFILE_KEY = 'FIN_SENTIMENT_USER_PROFILE';
const CACHE_NEWS_KEY = 'FIN_SENTIMENT_CACHED_NEWS';

export function getStoredAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_PROFILE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

export function setStoredUser(user: User | null): void {
  try {
    if (user) {
      localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_PROFILE_KEY);
    }
  } catch {}
}

function getStoredCachedNews(): NewsResponse | null {
  try {
    const raw = sessionStorage.getItem(CACHE_NEWS_KEY) || localStorage.getItem(CACHE_NEWS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

function setStoredCachedNews(data: NewsResponse | null) {
  try {
    if (data && data.articles && data.articles.length > 0 && !data.is_demo_dataset) {
      const serialized = JSON.stringify(data);
      sessionStorage.setItem(CACHE_NEWS_KEY, serialized);
      localStorage.setItem(CACHE_NEWS_KEY, serialized);
    }
  } catch {}
}

let inMemoryToken: string | null = getStoredAuthToken();
let currentBaseUrl = getStoredApiUrl();

// Pre-warm backend container early if on Render
if (typeof window !== 'undefined' && currentBaseUrl.includes('onrender.com')) {
  try {
    fetch(`${currentBaseUrl}/health`, { mode: 'no-cors' }).catch(() => {});
  } catch {}
}

const unauthorizedListeners: Array<() => void> = [];

function notifyUnauthorized() {
  unauthorizedListeners.forEach((cb) => cb());
}

function createAxiosClient(baseURL: string) {
  const instance = axios.create({
    baseURL,
    headers: {
      'Content-Type': 'application/json',
      ...(inMemoryToken ? { Authorization: `Bearer ${inMemoryToken}` } : {}),
    },
    withCredentials: true, // Required for HttpOnly session cookie persistence across CORS
    timeout: 90000,
  });

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error?.response?.status === 401) {
        const url = error.config?.url || '';
        // Only trigger session expiration for non-auth requests (don't wipe session on login, register, demo, or initial me probe)
        if (!url.includes('/api/auth/login') && !url.includes('/api/auth/register') && !url.includes('/api/auth/me') && !url.includes('/api/auth/demo')) {
          notifyUnauthorized();
        }
      }
      return Promise.reject(error);
    }
  );

  return instance;
}

let client = createAxiosClient(currentBaseUrl);

let isOfflineMode = false;
const listeners: Array<(offline: boolean) => void> = [];

function setOfflineStatus(offline: boolean) {
  if (isOfflineMode !== offline) {
    isOfflineMode = offline;
    listeners.forEach((cb) => cb(isOfflineMode));
  }
}

let cachedLiveNewsResponse: NewsResponse | null = getStoredCachedNews();

export const api = {
  getBaseUrl: (): string => currentBaseUrl,

  setBaseUrl: (newUrl: string) => {
    currentBaseUrl = newUrl.trim();
    try {
      localStorage.setItem(STORAGE_KEY, currentBaseUrl);
    } catch {}
    client = createAxiosClient(currentBaseUrl);
  },

  resetBaseUrl: () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
    currentBaseUrl = getStoredApiUrl();
    client = createAxiosClient(currentBaseUrl);
  },

  setAuthToken: (token: string | null) => {
    inMemoryToken = token;
    try {
      if (token) {
        localStorage.setItem(AUTH_TOKEN_KEY, token);
      } else {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(USER_PROFILE_KEY);
      }
    } catch {}
    client = createAxiosClient(currentBaseUrl);
  },

  subscribeUnauthorized: (cb: () => void) => {
    unauthorizedListeners.push(cb);
    return () => {
      const idx = unauthorizedListeners.indexOf(cb);
      if (idx !== -1) unauthorizedListeners.splice(idx, 1);
    };
  },

  // Authentication API endpoints
  register: async (data: { full_name: string; email: string; password: string }): Promise<AuthResponse> => {
    try {
      const res = await client.post<AuthResponse>('/api/auth/register', data);
      setOfflineStatus(false);
      if (res.data?.token) {
        api.setAuthToken(res.data.token);
      }
      if (res.data?.user) {
        setStoredUser(res.data.user);
      }
      return res.data;
    } catch (err: any) {
      if (err?.code === 'ECONNABORTED' || (err?.message && err.message.toLowerCase().includes('timeout'))) {
        throw new Error('Cloud server is waking up. Please try submitting again in a moment.');
      }
      throw err;
    }
  },

  login: async (data: { email: string; password: string; remember_me?: boolean }): Promise<AuthResponse> => {
    try {
      const res = await client.post<AuthResponse>('/api/auth/login', data);
      setOfflineStatus(false);
      if (res.data?.token) {
        api.setAuthToken(res.data.token);
      }
      if (res.data?.user) {
        setStoredUser(res.data.user);
      }
      return res.data;
    } catch (err: any) {
      if (err?.code === 'ECONNABORTED' || (err?.message && err.message.toLowerCase().includes('timeout'))) {
        throw new Error('Cloud server is waking up from idle mode (cold start). Please click Sign In again in a few seconds.');
      }
      throw err;
    }
  },

  demoLogin: async (): Promise<AuthResponse> => {
    try {
      const res = await client.post<AuthResponse>('/api/auth/demo');
      setOfflineStatus(false);
      if (res.data?.token) {
        api.setAuthToken(res.data.token);
      }
      if (res.data?.user) {
        setStoredUser(res.data.user);
      }
      return res.data;
    } catch (err: any) {
      console.warn('Remote demo login unreachable or timed out, activating instant local demo session:', err);
      const fallbackUser: User = {
        id: 'usr_demo_analyst',
        email: 'demo.analyst@finsentiment.ai',
        full_name: 'Lead Market Analyst (Demo)',
        created_at: new Date().toISOString()
      };
      const fallbackToken = 'demo-session-' + Date.now();
      api.setAuthToken(fallbackToken);
      setStoredUser(fallbackUser);
      setOfflineStatus(true);
      return {
        user: fallbackUser,
        token: fallbackToken,
        expires_in: 86400 * 30,
        message: 'Instant Demo Analyst terminal activated.'
      };
    }
  },

  getMe: async (): Promise<User> => {
    const res = await client.get<User>('/api/auth/me');
    setOfflineStatus(false);
    if (res.data) {
      setStoredUser(res.data);
    }
    return res.data;
  },

  logout: async (): Promise<MessageResponse> => {
    try {
      const res = await client.post<MessageResponse>('/api/auth/logout');
      return res.data;
    } finally {
      api.setAuthToken(null);
    }
  },

  forgotPassword: async (email: string): Promise<ForgotPasswordResponse> => {
    const res = await client.post<ForgotPasswordResponse>('/api/auth/forgot-password', { email });
    setOfflineStatus(false);
    return res.data;
  },

  resetPassword: async (token: string, new_password: string): Promise<MessageResponse> => {
    const res = await client.post<MessageResponse>('/api/auth/reset-password', {
      token,
      new_password,
    });
    setOfflineStatus(false);
    return res.data;
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
      console.warn('Backend unavailable for dashboard stats:', err);
      setOfflineStatus(true);
      const effectiveCache = cachedLiveNewsResponse || getStoredCachedNews();
      const status: FeedStatus = (effectiveCache && effectiveCache.articles && effectiveCache.articles.length > 0)
        ? 'CACHED LIVE DATA'
        : 'API ERROR';
      return {
        ...MOCK_DASHBOARD_STATS,
        is_demo_dataset: false,
        feed_status: status,
      };
    }
  },

  // News Explorer with honest multi-state live / cached / error handling
  getNews: async (params?: {
    page?: number;
    page_size?: number;
    company?: string;
    sentiment?: string;
    query?: string;
    today_only?: boolean;
    date?: string;
  }): Promise<NewsResponse> => {
    try {
      const res = await client.get<NewsResponse>('/api/news', { params });
      setOfflineStatus(false);
      if (res.data && !res.data.is_demo_dataset && res.data.articles && res.data.articles.length > 0) {
        cachedLiveNewsResponse = res.data;
        setStoredCachedNews(res.data);
      }
      return res.data;
    } catch (err: any) {
      console.warn('Backend unavailable for news:', err);
      setOfflineStatus(true);

      const effectiveCache = cachedLiveNewsResponse || getStoredCachedNews();
      // If we previously fetched live data, return cached genuine results with clear stale-data indicator
      if (effectiveCache && effectiveCache.articles && effectiveCache.articles.length > 0) {
        let items = [...effectiveCache.articles];
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
          ...effectiveCache,
          articles: paginated,
          total_count: items.length,
          page,
          page_size: pageSize,
          is_demo_dataset: false,
          feed_status: 'CACHED LIVE DATA',
        };
      }

      // If no real news is available, return an honest API ERROR state with empty list.
      // Do not silently substitute demo articles and label them as live.
      return {
        articles: [],
        total_count: 0,
        page: params?.page || 1,
        page_size: params?.page_size || 12,
        is_demo_dataset: false,
        feed_status: 'API ERROR',
        error_message: err?.response?.data?.detail || err?.message || 'Financial news service is currently unreachable.',
      };
    }
  },

  refreshNews: async () => {
    try {
      const res = await client.post('/api/news/refresh');
      setOfflineStatus(false);
      return res.data;
    } catch (err: any) {
      setOfflineStatus(true);
      throw new Error(err?.response?.data?.detail || err?.message || 'Failed to refresh news feed from backend.');
    }
  },

  // Explain Article using canonical prediction and perturbation attribution
  explainArticle: async (article: Article): Promise<SentimentAnalysisResult> => {
    // 1. Immediately establish canonical prediction from article
    const canonical = getCanonicalSentimentResult(article);
    if (canonical.tokens && canonical.tokens.length > 0) {
      return canonical;
    }

    try {
      // 2. Fetch from backend /api/news/{article_id}/explain
      const res = await client.get(`/api/news/${encodeURIComponent(article.id)}/explain`);
      setOfflineStatus(false);
      // Strictly preserve canonical sentiment, confidence, scores, text, article_id
      return mergeExplanationTokens(
        canonical,
        res.data.tokens,
        res.data.explanation_note,
        res.data.is_fallback
      );
    } catch (err) {
      // 3. Fallback: query analyzeHeadline for tokens, but strictly preserve canonical prediction
      try {
        const headlineRes = await api.analyzeHeadline(article.title);
        return mergeExplanationTokens(
          canonical,
          headlineRes.tokens,
          headlineRes.explanation_note,
          headlineRes.is_fallback
        );
      } catch (headlineErr) {
        return canonical;
      }
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
