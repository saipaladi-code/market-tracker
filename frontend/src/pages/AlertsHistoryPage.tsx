import React, { useState, useEffect } from 'react';
import {
  BellRing,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  RefreshCw,
  TrendingDown,
  GitCompareArrows,
  Check,
  ExternalLink,
  Layers
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { api } from '../services/api';
import { AlertRecord } from '../types';

export const AlertsHistoryPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [historyRecords, setHistoryRecords] = useState<any[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [alertsData, historyData] = await Promise.allSettled([
        api.getAlerts(unreadOnly),
        api.getHistory(),
      ]);

      if (alertsData.status === 'fulfilled') {
        setAlerts(alertsData.value);
      }
      if (historyData.status === 'fulfilled' && Array.isArray(historyData.value)) {
        setHistoryRecords(historyData.value);
      }
    } catch (err) {
      console.error('Failed to load alerts & history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
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
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-mono font-bold uppercase tracking-wider">
                RISK SURVEILLANCE & AUDIT LOG
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {alerts.length} Surveillance Events
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              Sentiment Alerts & Historical Timeline
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Automated notifications triggered by bearish sentiment surges (40%+) or narrative divergence spikes.
            </p>
          </div>

          {/* Controls: Filter unread only & reload */}
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-300 flex items-center gap-2 cursor-pointer bg-navy-950 border border-navy-750 px-3.5 py-2 rounded-xl">
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => setUnreadOnly(e.target.checked)}
                className="accent-blue-500 rounded"
              />
              <span className="font-medium">Unread Only</span>
            </label>

            <button
              onClick={loadData}
              className="p-2 bg-navy-850 hover:bg-navy-800 border border-navy-750 rounded-xl text-slate-300 transition-colors cursor-pointer"
              title="Refresh alerts"
            >
              <RefreshCw className="w-4 h-4 text-blue-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Historical Sentiment Progression Card */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Aggregated Historical Sentiment Trend
            </h3>
            <p className="text-xs text-slate-400">
              Time-series recordings captured during scheduled news ingestion cycles.
            </p>
          </div>
          <span className="text-[11px] font-mono text-slate-400 bg-navy-950 px-2 py-1 rounded-md border border-navy-800">
            {historyRecords.length} Stored Snapshots
          </span>
        </div>

        {historyRecords && historyRecords.length > 1 ? (
          <div className="h-60 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyRecords} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2b4a" />
                <XAxis dataKey="timestamp" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#070b14', borderColor: '#1c2b4a', borderRadius: '8px', fontSize: '11px' }}
                />
                <Line type="monotone" dataKey="positive_pct" stroke="#10b981" strokeWidth={2} name="Bullish %" dot={false} />
                <Line type="monotone" dataKey="negative_pct" stroke="#f43f5e" strokeWidth={2} name="Bearish %" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="p-8 text-center bg-navy-950/70 rounded-xl border border-navy-800/80 space-y-2">
            <Clock className="w-8 h-8 text-blue-400/50 mx-auto" />
            <h4 className="text-xs font-semibold text-slate-200">Historical Records Accumulation</h4>
            <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
              Historical progression graphs populate automatically as sequential news refreshes occur.
              No fabricated records are shown in accordance with institutional data integrity standards.
            </p>
          </div>
        )}
      </div>

      {/* Risk Alerts Feed */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
          Surveillance Watchlist ({alerts.length} Events)
        </h3>

        {loading ? (
          <div className="flex items-center justify-center p-12">
            <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-2xl space-y-3 shadow-sm">
            <ShieldCheck className="w-10 h-10 text-emerald-400 mx-auto" />
            <h3 className="text-base font-semibold text-slate-200">All Clear — No Active Sentiment Alerts</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              No monitored equities exceed bearish surge thresholds (40%+) or significant narrative polarization.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((al) => {
              const isBearishSurge = al.alert_type === 'BEARISH_SURGE';
              const isHighSeverity = al.severity === 'high';

              return (
                <div
                  key={al.id}
                  className={`bg-navy-900/90 border rounded-2xl p-5 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm ${
                    al.is_read
                      ? 'border-navy-800/80 opacity-60'
                      : isBearishSurge
                      ? 'border-rose-900/60 bg-rose-950/15'
                      : 'border-amber-900/60 bg-amber-950/15'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                        isBearishSurge
                          ? 'bg-rose-500/15 border-rose-500/30 text-rose-400'
                          : 'bg-amber-500/15 border-amber-500/30 text-amber-400'
                      }`}
                    >
                      {isBearishSurge ? (
                        <TrendingDown className="w-5 h-5" />
                      ) : (
                        <GitCompareArrows className="w-5 h-5" />
                      )}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-extrabold text-white text-sm">{al.company}</span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase border ${
                          isHighSeverity ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        }`}>
                          {al.severity} Severity
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 bg-navy-950 px-2 py-0.5 rounded border border-navy-800">
                          {al.alert_type}
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 leading-relaxed max-w-2xl">
                        {al.message}
                      </p>

                      <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono pt-1">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(al.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    {!al.is_read ? (
                      <button
                        onClick={() => handleMarkRead(al.id)}
                        className="px-3.5 py-1.5 bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white border border-navy-700 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                        title="Mark alert as acknowledged"
                      >
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Acknowledge</span>
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
                        <span>Acknowledged</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
