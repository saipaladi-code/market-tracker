import React, { useState, useEffect } from 'react';
import {
  X,
  ExternalLink,
  ShieldAlert,
  Check,
  Copy,
  AlertCircle,
  Building2,
  TrendingUp,
  RefreshCw,
  ArrowUpRight,
  Globe2,
  CheckCircle2
} from 'lucide-react';
import { Article, CompanyTradingRoute, BrokerDestination } from '../types';
import { api } from '../services/api';
import { SentimentBadge } from './SentimentBadge';
import { getClientSideTradingRoute } from '../utils/tickerLookup';

interface TradeRoutingModalProps {
  isOpen: boolean;
  onClose: () => void;
  article: Article | null;
}

export const TradeRoutingModal: React.FC<TradeRoutingModalProps> = ({
  isOpen,
  onClose,
  article,
}) => {
  const [route, setRoute] = useState<CompanyTradingRoute | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBroker, setSelectedBroker] = useState<BrokerDestination | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !article) {
      setRoute(null);
      setSelectedBroker(null);
      setError(null);
      setCopied(false);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);
    setCopied(false);

    // Compute client-side deterministic route immediately as instant baseline
    const fallbackRoute = getClientSideTradingRoute(article.company, article.ticker);
    setRoute(fallbackRoute);
    setSelectedBroker(
      fallbackRoute.recommended_broker ||
      (fallbackRoute.brokers.length > 0 ? fallbackRoute.brokers[0] : null)
    );

    // Call backend API to confirm real-time broker parameters
    api
      .getTradingRoute(article.company, article.ticker)
      .then((res) => {
        if (!isMounted) return;
        setRoute(res);
        const broker =
          res.recommended_broker ||
          (res.brokers.length > 0 ? res.brokers[0] : null);
        setSelectedBroker(broker);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.debug('Using verified client-side fallback route:', err);
        // Fallback already assigned
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, article]);

  if (!isOpen || !article) return null;

  const handleCopyTicker = (tickerText: string) => {
    if (!tickerText) return;
    navigator.clipboard.writeText(tickerText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-navy-750 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl space-y-5">
        {/* Header */}
        <div className="px-6 py-4 border-b border-navy-750 flex items-center justify-between sticky top-0 bg-navy-900/95 backdrop-blur-md z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">Verified Broker Trading Destination</h3>
              <p className="text-[10px] text-slate-400 font-mono">
                Multi-Broker Order Routing • Upstox (India) & IBKR (US Equities)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 pt-0">
          {/* Article / Sentiment Context */}
          <div className="p-4 rounded-xl bg-navy-950/70 border border-navy-800 space-y-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-blue-400" />
                <span className="font-semibold text-white text-sm">{article.company}</span>
                {route?.ticker && (
                  <span className="px-2 py-0.5 rounded bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-mono font-bold">
                    {route.ticker} {route.exchange ? `• ${route.exchange}` : ''}
                  </span>
                )}
              </div>
              <SentimentBadge sentiment={article.sentiment} confidence={article.confidence} size="xs" />
            </div>
            <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
              "{article.title}"
            </p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="p-8 text-center space-y-3">
              <RefreshCw className="w-7 h-7 text-blue-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400 font-mono">
                Verifying exchange ticker and broker instrument catalog...
              </p>
            </div>
          )}

          {/* Error State */}
          {!loading && error && (
            <div className="p-5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Routing Error</p>
                <p className="text-[11px] text-rose-400/80 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Unsupported Instrument State */}
          {!loading && route && !route.is_tradable && (
            <div className="p-6 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-3 text-center">
              <AlertCircle className="w-8 h-8 text-amber-400 mx-auto" />
              <div>
                <h4 className="text-sm font-semibold text-white">Trading Destination Not Verified</h4>
                <p className="text-xs text-amber-300/90 mt-1 max-w-md mx-auto">
                  {route.message || 'Trading destination not verified or currently unavailable.'}
                </p>
              </div>
              <p className="text-[11px] text-slate-400">
                FIN-SENTIMENT only routes to verified broker instruments (Upstox for Indian equities, Interactive Brokers for verified US equities).
                General market indexes, macroeconomic headlines, and unverified international stocks are never silently routed to a broker.
              </p>
            </div>
          )}

          {/* Supported Tradable Instrument Details */}
          {!loading && route && route.is_tradable && (
            <div className="space-y-4">
              {/* Instrument Overview Card */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Symbol / Ticker</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm font-bold text-white font-mono">{route.ticker}</span>
                    <button
                      onClick={() => handleCopyTicker(route.ticker || '')}
                      className="p-1 rounded bg-navy-800 hover:bg-navy-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
                      title="Copy ticker symbol"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Exchange</span>
                  <span className="text-sm font-bold text-emerald-400 font-mono mt-1 block">
                    {route.exchange} ({route.country === 'IN' ? 'India' : 'US'})
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800 col-span-2 sm:col-span-1">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Security ID / ISIN</span>
                  <span className="text-xs font-mono text-slate-300 mt-1 block truncate">
                    {route.isin || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Broker Selection if multiple available */}
              {route.brokers.length > 1 && (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-300">Select Brokerage Destination:</label>
                  <div className="grid grid-cols-2 gap-2">
                    {route.brokers.map((broker) => (
                      <button
                        key={broker.broker_id}
                        onClick={() => setSelectedBroker(broker)}
                        className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                          selectedBroker?.broker_id === broker.broker_id
                            ? 'bg-blue-600/15 border-blue-500 text-white shadow-sm'
                            : 'bg-navy-950 border-navy-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <span className="font-bold text-xs block">{broker.broker_name}</span>
                        <span className="text-[10px] text-slate-500">{broker.market_coverage}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Selected Broker Action Card */}
              {selectedBroker && (
                <div className="p-5 rounded-xl bg-gradient-to-br from-navy-950 to-navy-900 border border-blue-500/30 space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{selectedBroker.broker_name}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-300 font-mono border border-blue-500/30">
                          {selectedBroker.country === 'IN' ? 'Verified Indian Broker' : 'Verified US Broker'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{selectedBroker.market_coverage}</p>
                    </div>
                  </div>

                  {/* Step-by-step instructions */}
                  <div className="p-3.5 rounded-lg bg-navy-900/90 border border-navy-800 space-y-2 text-xs">
                    <p className="font-semibold text-slate-200 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                      <span>Trading Instructions:</span>
                    </p>
                    <ol className="list-decimal list-inside space-y-1 text-slate-300 text-[11px] leading-relaxed">
                      <li>
                        Click the button below to open the official <strong className="text-white">{selectedBroker.broker_name}</strong> portal.
                      </li>
                      <li>Sign in using your authorized brokerage account credentials.</li>
                      <li>
                        Search for ticker <strong className="text-emerald-400 font-mono">{route.ticker}</strong> on <strong className="text-white">{route.exchange}</strong>.
                      </li>
                      <li>Review real-time quote depth, set order parameters, and confirm your trade.</li>
                    </ol>
                  </div>

                  {/* Primary Action Button */}
                  <div className="pt-1 flex flex-col sm:flex-row items-center gap-3">
                    <a
                      href={selectedBroker.entry_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/30 transition-all cursor-pointer"
                    >
                      <span>Proceed to {selectedBroker.broker_name}</span>
                      <ArrowUpRight className="w-4 h-4" />
                    </a>

                    <button
                      onClick={() => handleCopyTicker(route.ticker || '')}
                      className="w-full sm:w-auto py-3 px-4 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 hover:text-white border border-navy-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                    >
                      {copied ? (
                        <>
                          <Check className="w-4 h-4 text-emerald-400" />
                          <span>Copied {route.ticker}!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4 text-slate-400" />
                          <span>Copy Ticker ({route.ticker})</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Compliance & Security Disclaimer */}
          <div className="p-3.5 rounded-xl bg-navy-950/50 border border-navy-800/80 space-y-1.5 text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5 font-semibold text-slate-300">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>Compliance & Security Protocol</span>
            </div>
            <p className="leading-relaxed">
              FIN-SENTIMENT is an informational AI sentiment analytics platform and is not a registered broker-dealer or investment advisor.
              We never request or store brokerage passwords, tokens, or execute automated trades. All trades are conducted directly on your verified brokerage account.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
