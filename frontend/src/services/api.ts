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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const api = {
  // Health
  getHealth: async () => {
    const res = await client.get('/api/health');
    return res.data;
  },

  // Dashboard Stats
  getDashboardStats: async (): Promise<DashboardStats> => {
    const res = await client.get('/api/dashboard/stats');
    return res.data;
  },

  // News Explorer
  getNews: async (params?: { page?: number; page_size?: number; company?: string; sentiment?: string; query?: string }) => {
    const res = await client.get('/api/news', { params });
    return res.data;
  },

  refreshNews: async () => {
    const res = await client.post('/api/news/refresh');
    return res.data;
  },

  // FinBERT Sentiment Analysis
  analyzeHeadline: async (text: string): Promise<SentimentAnalysisResult> => {
    const res = await client.post('/api/analyze', { text });
    return res.data;
  },

  analyzeBatch: async (texts: string[]): Promise<SentimentAnalysisResult[]> => {
    const res = await client.post('/api/analyze/batch', { texts });
    return res.data;
  },

  // Companies
  getCompanies: async (): Promise<CompanySummary[]> => {
    const res = await client.get('/api/companies');
    return res.data;
  },

  getCompanyDetail: async (company: string) => {
    const res = await client.get(`/api/companies/${encodeURIComponent(company)}/sentiment`);
    return res.data;
  },

  // Conflict Detector
  getConflicts: async (): Promise<ConflictSignal[]> => {
    const res = await client.get('/api/conflicts');
    return res.data;
  },

  // Sectors Heatmap
  getSectors: async (): Promise<SectorSentiment[]> => {
    const res = await client.get('/api/sentiment/sectors');
    return res.data;
  },

  // History & Alerts
  getHistory: async (company?: string) => {
    const res = await client.get('/api/sentiment/history', { params: { company } });
    return res.data;
  },

  getAlerts: async (unreadOnly = false): Promise<AlertRecord[]> => {
    const res = await client.get('/api/alerts', { params: { unread_only: unreadOnly } });
    return res.data;
  },

  markAlertRead: async (alertId: string) => {
    const res = await client.patch(`/api/alerts/${encodeURIComponent(alertId)}`);
    return res.data;
  },

  // Data Quality
  getDataQuality: async (): Promise<DataQualityReport> => {
    const res = await client.get('/api/data-quality');
    return res.data;
  },

  // AI Financial Assistant
  chatAssistant: async (message: string, companyFocus?: string): Promise<AssistantChatResponse> => {
    const res = await client.post('/api/assistant/chat', { message, company_focus: companyFocus });
    return res.data;
  },
};
