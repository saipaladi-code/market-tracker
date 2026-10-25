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
  Copy
} from 'lucide-react';
import { api } from '../services/api';
import { DataQualityReport } from '../types';

export const DataQualityPage: React.FC = () => {
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState(true);

  const loadReport = async () => {
    try {
      setLoading(true);
      const data = await api.getDataQuality();
      setReport(data);
    } catch (err) {
      console.error('Failed to load data quality:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-bold text-white">System Integrity & Data Quality Telemetry</h2>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono text-[10px] border border-blue-500/20">
            QA Telemetry
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Rigorous operational health monitoring covering FinBERT model readiness, provider status, deduplication, and data hygiene.
        </p>
      </div>

      {loading || !report ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Service Connectivity Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* FinBERT AI Model Status */}
            <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">FinBERT AI Engine</span>
                <Cpu className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-bold text-white uppercase font-mono">
                  {report.model_status}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Local PyTorch CPU model loaded in memory (ProsusAI/finbert).
              </p>
            </div>

            {/* Database Persistence Status */}
            <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Persistence Layer</span>
                <Database className="w-4 h-4 text-blue-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                <span className="text-sm font-bold text-white font-mono uppercase">
                  {report.database_status.persistence_mode} Mode
                </span>
              </div>
              <p className="text-[11px] text-slate-500 truncate" title={report.database_status.message}>
                {report.database_status.message}
              </p>
            </div>

            {/* News API Provider Status */}
            <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">News Provider</span>
                <Globe className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-sm font-bold text-white font-mono truncate">
                {report.news_api_status}
              </div>
              <p className="text-[11px] text-slate-500">
                Transparent fallback activated if no key or quota exceeded.
              </p>
            </div>
          </div>

          {/* Data Hygiene Metrics */}
          <div className="bg-navy-900 border border-navy-750 rounded-xl p-5 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Corpus Data Hygiene & Ambiguity Audits
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800 text-center">
                <span className="text-[10px] text-slate-400 block mb-1">Total Indexed</span>
                <strong className="text-base font-bold font-mono text-white">{report.total_articles}</strong>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800 text-center">
                <span className="text-[10px] text-slate-400 block mb-1">Duplicate Rate</span>
                <strong className="text-base font-bold font-mono text-amber-400">{report.duplicate_rate}%</strong>
                <span className="text-[10px] text-slate-500 block">({report.duplicate_count} items)</span>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800 text-center">
                <span className="text-[10px] text-slate-400 block mb-1">Low Confidence</span>
                <strong className="text-base font-bold font-mono text-blue-400">{report.low_confidence_rate}%</strong>
                <span className="text-[10px] text-slate-500 block">(&lt; 60% conf)</span>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800 text-center">
                <span className="text-[10px] text-slate-400 block mb-1">Missing Headings</span>
                <strong className={`text-base font-bold font-mono ${report.missing_headlines === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {report.missing_headlines}
                </strong>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800 text-center">
                <span className="text-[10px] text-slate-400 block mb-1">Missing Sources</span>
                <strong className={`text-base font-bold font-mono ${report.missing_sources === 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {report.missing_sources}
                </strong>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800 text-center">
                <span className="text-[10px] text-slate-400 block mb-1">Invalid URLs</span>
                <strong className={`text-base font-bold font-mono ${report.invalid_urls === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {report.invalid_urls}
                </strong>
              </div>
            </div>
          </div>

          {/* Methodological Guidance */}
          <div className="p-4 bg-navy-900 border border-navy-800 rounded-xl space-y-2 text-xs text-slate-400">
            <div className="flex items-center gap-2 text-slate-200 font-semibold">
              <HelpCircle className="w-4 h-4 text-blue-400" />
              <span>Scientific Note on Model Confidence</span>
            </div>
            <p className="leading-relaxed">
              Model confidence scores reflect the softmax probability distribution across FinBERT's three training classes. 
              A low-confidence classification indicates syntactic or semantic ambiguity in headline phrasing. 
              Confidence scores should be used as quality and triage filters rather than irrefutable verification.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
