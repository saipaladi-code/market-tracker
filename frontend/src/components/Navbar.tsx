import React, { useState } from 'react';
import { RefreshCw, Activity, AlertCircle, Database } from 'lucide-react';

interface NavbarProps {
  lastUpdated?: string;
  isDemo?: boolean;
  onRefresh?: () => Promise<void>;
}

export const Navbar: React.FC<NavbarProps> = ({ lastUpdated, isDemo = false, onRefresh }) => {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (!onRefresh) return;
    try {
      setRefreshing(true);
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <header className="h-16 bg-navy-900 border-b border-navy-700/60 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-white">Financial Market Sentiment Tracker</h2>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
              v1.0 College Field Edition
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Real-time textual tone classification via local Hugging Face <code className="text-slate-300">ProsusAI/finbert</code>
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {isDemo && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-medium">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>DEMO DATA MODE</span>
          </div>
        )}

        <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 border border-navy-700 bg-navy-950 px-3 py-1 rounded-md">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>Freshness: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : 'Current'}</span>
        </div>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-md text-xs font-medium transition-colors shadow-sm"
          title="Trigger news fetch and sentiment aggregation"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{refreshing ? 'Refreshing...' : 'Ingest & Refresh'}</span>
        </button>
      </div>
    </header>
  );
};
