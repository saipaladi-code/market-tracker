import React, { useState, useEffect } from 'react';
import {
  BellRing,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  RefreshCw,
  TrendingDown,
  GitCompareArrows
} from 'lucide-react';
import { api } from '../services/api';
import { AlertRecord } from '../types';

export const AlertsHistoryPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await api.getAlerts(unreadOnly);
      setAlerts(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [unreadOnly]);

  const handleMarkRead = async (alertId: string) => {
    try {
      await api.markAlertRead(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a))
      );
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BellRing className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-bold text-white">Sentiment Alerts & Risk Watchlist</h2>
          </div>
          <p className="text-xs text-slate-400">
            Automated alerts triggered when negative media tone exceeds thresholds or when opposing narratives collide.
          </p>
        </div>

        {/* Filter Toggle */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400 flex items-center gap-2 cursor-pointer bg-navy-900 border border-navy-750 px-3 py-1.5 rounded-lg">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
              className="accent-blue-500 rounded"
            />
            <span>Unread Only</span>
          </label>
        </div>
      </div>

      {/* Alerts List */}
      {loading ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
      ) : alerts.length === 0 ? (
        <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-xl space-y-2">
          <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-300">All Clear — No Active Sentiment Alerts</h3>
          <p className="text-xs text-slate-500">
            No monitored companies exceed negative surge thresholds (40%+) or significant sentiment divergence.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((al) => {
            const isBearishSurge = al.alert_type === 'BEARISH_SURGE';
            return (
              <div
                key={al.id}
                className={`bg-navy-900 border rounded-xl p-4 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                  al.is_read
                    ? 'border-navy-800 opacity-60'
                    : isBearishSurge
                    ? 'border-rose-900/60 bg-rose-950/10'
                    : 'border-amber-900/60 bg-amber-950/10'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg mt-0.5 ${
                    isBearishSurge ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'
                  }`}>
                    {isBearishSurge ? <TrendingDown className="w-4 h-4" /> : <GitCompareArrows className="w-4 h-4" />}
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-white">{al.company}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                        al.severity === 'high'
                          ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}>
                        {al.alert_type}
                      </span>
                      {al.is_read && (
                        <span className="text-[10px] text-slate-500 font-mono">READ</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-300">{al.message}</p>
                    <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(al.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {!al.is_read && (
                  <button
                    onClick={() => handleMarkRead(al.id)}
                    className="self-end sm:self-center shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-navy-800 hover:bg-navy-700 text-slate-300 text-xs font-medium border border-navy-700 transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                    <span>Acknowledge</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
