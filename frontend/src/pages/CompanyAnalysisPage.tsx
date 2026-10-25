import React, { useState, useEffect } from 'react';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
  GitCompareArrows,
  ExternalLink,
  Layers,
  Calendar,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { api } from '../services/api';
import { CompanySummary, Article } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';

export const CompanyAnalysisPage: React.FC = () => {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>('Nvidia');
  const [companyDetail, setCompanyDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    const loadCompanyList = async () => {
      try {
        setLoading(true);
        const list = await api.getCompanies();
        setCompanies(list);
        if (list.length > 0 && !selectedCompany) {
          setSelectedCompany(list[0].company);
        }
      } catch (err) {
        console.error('Failed to load companies:', err);
      } finally {
        setLoading(false);
      }
    };
    loadCompanyList();
  }, []);

  useEffect(() => {
    if (!selectedCompany) return;
    const loadDetail = async () => {
      try {
        setDetailLoading(true);
        const data = await api.getCompanyDetail(selectedCompany);
        setCompanyDetail(data);
      } catch (err) {
        console.error('Failed to load company detail:', err);
      } finally {
        setDetailLoading(false);
      }
    };
    loadDetail();
  }, [selectedCompany]);

  const activeSummary = companies.find((c) => c.company === selectedCompany);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-base font-bold text-white">Company Sentiment Deep Dive</h2>
        <p className="text-xs text-slate-400">
          In-depth coverage breakdown, historical sentiment progression, and conflict detection.
        </p>
      </div>

      {/* Company Selector Buttons */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        {companies.map((c) => (
          <button
            key={c.company}
            onClick={() => setSelectedCompany(c.company)}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all border flex items-center gap-2 ${
              selectedCompany === c.company
                ? 'bg-blue-600 border-blue-500 text-white shadow-md shadow-blue-600/20'
                : 'bg-navy-900 border-navy-750 text-slate-300 hover:bg-navy-800'
            }`}
          >
            <span className="font-bold">{c.ticker}</span>
            <span className="text-slate-300 font-normal">{c.company}</span>
            {c.has_conflict && (
              <span className="w-2 h-2 rounded-full bg-amber-400" title="Mixed sentiment conflict detected" />
            )}
          </button>
        ))}
      </div>

      {/* Selected Company Overview Cards */}
      {activeSummary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
            <span className="text-xs text-slate-400">Monitored Sector</span>
            <div className="text-base font-bold text-white font-mono">{activeSummary.sector}</div>
            <p className="text-[11px] text-slate-500">{activeSummary.total_articles} distinct articles</p>
          </div>

          <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
            <span className="text-xs text-slate-400">Bullish Ratio</span>
            <div className="text-xl font-bold text-emerald-400 font-mono">
              {activeSummary.positive_pct}%
            </div>
            <p className="text-[11px] text-slate-500">
              {activeSummary.positive_count} of {activeSummary.total_articles} articles
            </p>
          </div>

          <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
            <span className="text-xs text-slate-400">Bearish Ratio</span>
            <div className="text-xl font-bold text-rose-400 font-mono">
              {activeSummary.negative_pct}%
            </div>
            <p className="text-[11px] text-slate-500">
              {activeSummary.negative_count} of {activeSummary.total_articles} articles
            </p>
          </div>

          <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
            <span className="text-xs text-slate-400">FinBERT Avg Confidence</span>
            <div className="text-xl font-bold text-blue-400 font-mono">
              {(activeSummary.average_confidence * 100).toFixed(1)}%
            </div>
            <p className="text-[11px] text-slate-500">Model certainty on winning class</p>
          </div>
        </div>
      )}

      {/* Conflict Warning If Active */}
      {companyDetail?.conflict && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2 text-xs">
          <div className="flex items-center gap-2 text-amber-400 font-bold">
            <GitCompareArrows className="w-4 h-4" />
            <span>Active Sentiment Divergence Signal Flagged</span>
            <span className="ml-auto px-2 py-0.5 rounded bg-amber-500/20 font-mono">
              Conflict Index: {(companyDetail.conflict.conflict_score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-slate-300 leading-relaxed">
            {companyDetail.conflict.explanation}
          </p>
        </div>
      )}

      {/* Company Articles Feed */}
      <div className="bg-navy-900 border border-navy-750 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            {selectedCompany} News Archive ({companyDetail?.articles?.length || 0})
          </h3>
          <span className="text-[11px] text-slate-500 font-mono">Sorted by publication date</span>
        </div>

        {detailLoading ? (
          <div className="flex items-center justify-center p-8">
            <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
          </div>
        ) : !companyDetail?.articles || companyDetail.articles.length === 0 ? (
          <p className="text-xs text-slate-500 p-6 text-center italic">
            No specific articles logged for {selectedCompany} yet.
          </p>
        ) : (
          <div className="space-y-3">
            {companyDetail.articles.map((art: Article) => (
              <div
                key={art.id}
                className="bg-navy-950 border border-navy-800 rounded-lg p-3.5 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} />
                    <span className="text-[11px] text-slate-400 font-mono">{art.source}</span>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    {new Date(art.published_at).toLocaleDateString()}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-white leading-snug">
                  {art.title}
                </h4>
                {art.description && (
                  <p className="text-[11px] text-slate-400 line-clamp-2">
                    {art.description}
                  </p>
                )}
                <div className="pt-2 flex justify-end">
                  <a
                    href={art.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300"
                  >
                    <span>View original</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
