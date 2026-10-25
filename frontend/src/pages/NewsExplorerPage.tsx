import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  ExternalLink,
  Copy,
  Sparkles,
  RefreshCw,
  AlertCircle,
  HelpCircle
} from 'lucide-react';
import { api } from '../services/api';
import { Article, SentimentAnalysisResult } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { ExplainModal } from '../components/ExplainModal';

const COMPANIES = ['All', 'Apple', 'Microsoft', 'Nvidia', 'Tesla', 'Alphabet', 'Amazon', 'JPMorgan Chase', 'Pfizer', 'ExxonMobil'];
const SENTIMENTS = ['All', 'Positive', 'Negative', 'Neutral'];

export const NewsExplorerPage: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('All');
  const [selectedSentiment, setSelectedSentiment] = useState('All');
  const [page, setPage] = useState(1);
  const [isDemoDataset, setIsDemoDataset] = useState(false);

  // Explain modal state
  const [selectedExplainResult, setSelectedExplainResult] = useState<SentimentAnalysisResult | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  const fetchNews = async () => {
    try {
      setLoading(true);
      const data = await api.getNews({
        page,
        page_size: 15,
        company: selectedCompany === 'All' ? undefined : selectedCompany,
        sentiment: selectedSentiment === 'All' ? undefined : selectedSentiment.toLowerCase(),
        query: searchQuery.trim() || undefined,
      });
      setArticles(data.articles || []);
      setTotalCount(data.total_count || 0);
      setIsDemoDataset(data.is_demo_dataset || false);
    } catch (err) {
      console.error('Failed to load news:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, [page, selectedCompany, selectedSentiment]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchNews();
  };

  const handleInspectAttribution = async (article: Article) => {
    try {
      setExplainLoading(true);
      const result = await api.analyzeHeadline(article.title);
      setSelectedExplainResult(result);
    } catch (err) {
      console.error('Explain lookup failed:', err);
    } finally {
      setExplainLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Filters */}
      <div className="bg-navy-900 border border-navy-750 p-5 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white">Financial News Intelligence Feed</h2>
            <p className="text-xs text-slate-400">
              Aggregated financial news classified by FinBERT with deduplication tracking.
            </p>
          </div>
          {isDemoDataset && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs self-start md:self-auto">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>DEMO DATASET ACTIVE</span>
            </div>
          )}
        </div>

        {/* Search bar and Filters */}
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search keyword (e.g., earnings, cloud, antitrust, margins)..."
              className="w-full bg-navy-950 border border-navy-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <select
              value={selectedCompany}
              onChange={(e) => {
                setSelectedCompany(e.target.value);
                setPage(1);
              }}
              className="w-full bg-navy-950 border border-navy-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {COMPANIES.map((c) => (
                <option key={c} value={c}>
                  Company: {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedSentiment}
              onChange={(e) => {
                setSelectedSentiment(e.target.value);
                setPage(1);
              }}
              className="w-full bg-navy-950 border border-navy-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {SENTIMENTS.map((s) => (
                <option key={s} value={s}>
                  Sentiment: {s}
                </option>
              ))}
            </select>
          </div>
        </form>
      </div>

      {/* Articles Feed */}
      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 space-y-3">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
          <p className="text-xs text-slate-400">Filtering articles...</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-xl space-y-2">
          <p className="text-sm font-semibold text-slate-300">No matching financial articles found</p>
          <p className="text-xs text-slate-500">Try adjusting your keyword, company, or sentiment filters.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>Showing {articles.length} of {totalCount} records</span>
            <span className="font-mono text-[11px]">Page {page}</span>
          </div>

          {articles.map((art) => (
            <div
              key={art.id}
              className={`bg-navy-900 border rounded-xl p-4 transition-colors space-y-3 ${
                art.is_duplicate ? 'border-navy-800 opacity-70 bg-navy-950/60' : 'border-navy-750 hover:border-navy-700'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-blue-900/30 text-blue-300 font-mono text-[11px] font-semibold border border-blue-800/40">
                    {art.company}
                  </span>
                  <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} />
                  {art.is_duplicate && (
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px] border border-slate-700">
                      DUPLICATE HEADLINE
                    </span>
                  )}
                  {art.is_demo && (
                    <span className="text-[10px] text-amber-400/80 font-mono">DEMO DATA</span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>{art.source}</span>
                  <span>•</span>
                  <span>{new Date(art.published_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white leading-snug">
                  {art.title}
                </h3>
                {art.description && (
                  <p className="text-xs text-slate-300/80 mt-1 line-clamp-2 leading-relaxed">
                    {art.description}
                  </p>
                )}
              </div>

              <div className="pt-2 border-t border-navy-800/80 flex items-center justify-between text-xs">
                <button
                  onClick={() => handleInspectAttribution(art)}
                  className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors font-medium text-[11px]"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Explain AI Salience</span>
                </button>

                <a
                  href={art.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition-colors text-[11px]"
                >
                  <span>Original Article</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}

          {/* Pagination Controls */}
          {totalCount > 15 && (
            <div className="flex items-center justify-center gap-3 pt-4">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded bg-navy-900 border border-navy-750 text-xs text-slate-300 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-xs text-slate-400 font-mono">Page {page}</span>
              <button
                disabled={page * 15 >= totalCount}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded bg-navy-900 border border-navy-750 text-xs text-slate-300 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Explainable AI Modal */}
      <ExplainModal
        isOpen={selectedExplainResult !== null}
        onClose={() => setSelectedExplainResult(null)}
        result={selectedExplainResult}
      />
    </div>
  );
};
