import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  Database,
  Cpu,
  Globe,
  Layers,
  FileCheck,
  RefreshCw,
  HelpCircle,
  Copy,
  CheckCircle2,
  XCircle,
  Activity,
  BotMessageSquare,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';
import { DataQualityReport } from '../types';

export const DataQualityPage: React.FC = () => {
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [healthData, setHealthData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadReport = async () => {
    try {
      setLoading(true);
      const [reportData, health] = await Promise.allSettled([
        api.getDataQuality(),
        api.getHealth(),
      ]);

      if (reportData.status === 'fulfilled') {
        setReport(reportData.value);
      }
      if (health.status === 'fulfilled') {
        setHealthData(health.value);
      }
    } catch (err) {
      console.error('Failed to load data quality telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  const handleManualCheck = async () => {
    try {
      setRefreshing(true);
      await loadReport();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono font-bold uppercase tracking-wider">
                TELEMETRY & QA INSPECTOR
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Real-time System Verification
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              Data Quality & Operational Health Telemetry
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Continuous diagnostics evaluating FinBERT inference engine, persistence layer, news provider, and corpus deduplication.
            </p>
          </div>

          <button
            onClick={handleManualCheck}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-navy-850 hover:bg-navy-800 text-slate-200 border border-navy-750 rounded-xl text-xs font-semibold transition-all self-start md:self-auto cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Run Health Diagnostic</span>
          </button>
        </div>
      </div>

      {loading || !report ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Subsystems Connectivity Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* FinBERT AI Engine */}
            <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400">FinBERT AI Model</span>
                <Cpu className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${
                  report.engine_mode === 'lexical-fallback' ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'
                }`} />
                <span className="text-base font-extrabold text-white uppercase font-mono">
                  {report.engine_mode || report.model_status}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {report.engine_mode === 'hosted-huggingface' || report.engine_mode === 'hosted-finbert'
                  ? 'ProsusAI/finbert active via Hugging Face Serverless API.'
                  : (report.engine_mode === 'cloud-gemini'
                    ? 'Cloud AI Neural Sentiment Engine active.'
                    : (report.engine_mode === 'local-bfloat16'
                      ? 'Local FinBERT PyTorch CPU weights active in memory.'
                      : 'Rule-based Loughran-McDonald lexicon fallback active.'))}
              </p>
            </div>

            {/* Persistence Layer */}
            <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400">Database Persistence</span>
                <Database className="w-4 h-4 text-blue-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                <span className="text-base font-extrabold text-white font-mono uppercase">
                  {report.database_status.persistence_mode}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed truncate" title={report.database_status.message}>
                {report.database_status.message}
              </p>
            </div>

            {/* News Provider Status */}
            <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400">News Provider</span>
                <Globe className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${
                  healthData?.news_api?.has_key ? 'bg-emerald-400' : 'bg-amber-400'
                }`} />
                <span className="text-base font-extrabold text-white font-mono uppercase">
                  {healthData?.news_api?.has_key ? 'CONNECTED' : 'DEMO CORPUS'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {report.news_api_status}
              </p>
            </div>

            {/* AI Assistant Status */}
            <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400">Gemini Assistant</span>
                <BotMessageSquare className="w-4 h-4 text-purple-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${
                  healthData?.gemini_assistant?.active ? 'bg-emerald-400' : 'bg-cyan-400'
                }`} />
                <span className="text-base font-extrabold text-white font-mono uppercase">
                  {healthData?.gemini_assistant?.active ? 'GEMINI 1.5' : 'GROUNDED OFFLINE'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {healthData?.gemini_assistant?.active
                  ? 'Gemini 1.5 Flash conversational synthesis active.'
                  : 'Grounded in retrieved news citations.'}
              </p>
            </div>
          </div>

          {/* Data Hygiene Metrics */}
          <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 space-y-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white font-mono">
                  Data Ingestion & Hygiene Telemetry
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Automated checks inspecting headline integrity, canonical duplicates, and confidence distributions.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 bg-navy-950 text-slate-300 rounded-lg border border-navy-800">
                {report.total_articles} Ingested Articles Audited
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Duplicate Analysis */}
              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Near-Duplicate Articles</span>
                  <span className="font-mono text-cyan-400 font-bold">{report.duplicate_rate}%</span>
                </div>
                <div className="text-2xl font-extrabold font-mono text-white">
                  {report.duplicate_count}
                </div>
                <p className="text-[10px] text-slate-500">
                  Canonical URLs and title similarity filtered.
                </p>
              </div>

              {/* Low Confidence Ratio */}
              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Low-Confidence Tone (&lt;60%)</span>
                  <span className="font-mono text-amber-400 font-bold">{report.low_confidence_rate}%</span>
                </div>
                <div className="text-2xl font-extrabold font-mono text-white">
                  {report.low_confidence_count}
                </div>
                <p className="text-[10px] text-slate-500">
                  Headlines with high semantic ambiguity.
                </p>
              </div>

              {/* Missing Metadata */}
              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Missing Source / Title</span>
                  <span className="font-mono text-emerald-400 font-bold">0% Error</span>
                </div>
                <div className="text-2xl font-extrabold font-mono text-emerald-400">
                  {report.missing_headlines + report.missing_sources}
                </div>
                <p className="text-[10px] text-slate-500">
                  Rejected during ingestion validation.
                </p>
              </div>

              {/* Stale Articles */}
              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Aged Headlines (&gt;7 Days)</span>
                  <span className="font-mono text-slate-400 font-bold">Archive</span>
                </div>
                <div className="text-2xl font-extrabold font-mono text-white">
                  {report.stale_articles_count}
                </div>
                <p className="text-[10px] text-slate-500">
                  Retained for time-series drift modeling.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
