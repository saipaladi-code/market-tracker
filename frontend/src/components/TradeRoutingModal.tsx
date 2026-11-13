import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldAlert,
  Check,
  Copy,
  AlertCircle,
  Building2,
  TrendingUp,
  RefreshCw,
  ArrowUpRight,
  ExternalLink,
  Info,
  Compass
} from 'lucide-react';
import { Article, CompanyTradingRoute, BrokerDestination } from '../types';
import { SentimentBadge } from './SentimentBadge';
import { brokerNavigationService, NavigationResult } from '../services/brokerNavigationService';
import { BrokerId, getSelectedBroker, setSelectedBrokerPreference } from '../utils/brokerConfig';

interface TradeRoutingModalProps {
  isOpen: boolean;
  onClose: () => void;
  article: Article | null;
  initialBroker?: BrokerId;
}

export const TradeRoutingModal: React.FC<TradeRoutingModalProps> = ({
  isOpen,
  onClose,
  article,
  initialBroker,
}) => {
  const [route, setRoute] = useState<CompanyTradingRoute | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [navNotice, setNavNotice] = useState<string | null>(null);
  const [blockedUrl, setBlockedUrl] = useState<string | null>(null);

  // Resolve trading route whenever article or isOpen changes
  useEffect(() => {
    if (!isOpen || !article) {
      setRoute(null);
      setError(null);
      setCopied(false);
      setNavNotice(null);
      setBlockedUrl(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);
    setCopied(false);
    setNavNotice(null);
    setBlockedUrl(null);

    const preferredBroker = initialBroker || getSelectedBroker();

    brokerNavigationService
      .resolveRoute({
        company: article.company,
        ticker: article.ticker,
        preferredBrokerId: preferredBroker,
      })
      .then((resolvedRoute) => {
        if (!isMounted) return;
        setRoute(resolvedRoute);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to resolve trading route:', err);
        setError('Unable to resolve broker routing destination at this moment.');
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, article, initialBroker]);

  if (!isOpen || !article) return null;

  const handleCopyTicker = (tickerText: string) => {
    if (!tickerText) return;
    navigator.clipboard.writeText(tickerText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNavigateBroker = (brokerToUse: BrokerDestination) => {
    if (!route) return;
    setSelectedBrokerPreference(brokerToUse.broker_id as BrokerId);
    setNavNotice(null);
    setBlockedUrl(null);

    const result: NavigationResult = brokerNavigationService.openDestination(
      route,
      brokerToUse,
      'direct'
    );

    if (result.isBlockedByPopup && result.openedUrl) {
      setBlockedUrl(result.openedUrl);
      setNavNotice('Pop-up window was blocked by your browser. Click the direct link below.');
    } else if (!result.success) {
      setError(result.message || 'Failed to navigate to broker destination.');
    }
  };

  const isTradable = Boolean(route && route.is_tradable);
  const isIndianSupported = Boolean(route && route.is_tradable && route.country === 'IN');
  const isUSStock = Boolean(route && route.is_tradable && (route.country === 'US' || route.exchange === 'NASDAQ' || route.exchange === 'NYSE'));

  // Extract both brokers
  const upstoxBroker = route?.brokers.find((b) => b.broker_id.toLowerCase() === 'upstox') || null;
  const growwBroker = route?.brokers.find((b) => b.broker_id.toLowerCase() === 'groww') || null;

  const upstoxUrl = upstoxBroker && route
    ? brokerNavigationService.getDestinationUrl(route, upstoxBroker, 'direct')
    : (route?.country === 'US' ? 'https://upstox.com/us-stocks/' : 'https://pro.upstox.com');

  const growwUrl = growwBroker && route
    ? brokerNavigationService.getDestinationUrl(route, growwBroker, 'direct')
    : (route?.country === 'US' ? 'https://groww.in/us-stocks/popular-us-stocks-and-etfs' : 'https://groww.in/stocks');

  // Dynamic Dialog Title
  let modalTitle = 'Choose Your Trading Platform';
  let modalSubtitle = 'Instrument Routing & Verification';
  if (route) {
    if (isTradable) {
      modalTitle = 'Choose Your Trading Platform';
      modalSubtitle = isIndianSupported
        ? `${route.company} (${route.ticker || 'NSE'}) • Verified Indian Equity`
        : `${route.company} (${route.ticker || 'US'}) • Verified US Equity`;
    } else {
      modalTitle = 'Trading Destination Unavailable';
      modalSubtitle = 'Macroeconomic / Unmapped Instrument';
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-navy-750 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl space-y-5">
        {/* Header */}
        <div className="px-5 sm:px-6 py-4 border-b border-navy-750 flex items-center justify-between sticky top-0 bg-navy-900/95 backdrop-blur-md z-10 gap-3">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isTradable
                ? 'bg-blue-500/15 border border-blue-500/30 text-blue-400'
                : 'bg-slate-500/15 border border-slate-500/30 text-slate-400'
            }`}>
              <TrendingUp className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="font-bold text-white text-sm break-words leading-snug">{modalTitle}</h3>
              <p className="text-[10px] text-slate-400 font-mono break-words leading-tight">
                {modalSubtitle}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors cursor-pointer shrink-0"
            title="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 pt-0">
          {/* Article Context Header */}
          <div className="p-4 rounded-xl bg-navy-950/70 border border-navy-800 space-y-2.5">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-blue-400 shrink-0" />
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
                Verifying broker destinations and instrument catalog...
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

          {/* Popup Blocked Notice */}
          {blockedUrl && (
            <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-3">
              <Compass className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold">Browser Blocked New Tab</p>
                <p className="text-[11px] text-amber-300/90">{navNotice}</p>
                <a
                  href={blockedUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 underline font-semibold mt-1"
                >
                  Click here to open broker directly
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          )}

          {/* CASE 1: Supported Stock (Indian or US) - BOTH BROKER OPTIONS VISIBLE TOGETHER */}
          {!loading && route && isTradable && (
            <div className="space-y-5">
              {/* Instrument Overview Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Company</span>
                  <span className="text-sm font-bold text-white font-mono mt-1 block truncate">
                    {route.company}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Symbol</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm font-bold text-white font-mono notranslate" translate="no">
                      {route.ticker}
                    </span>
                    <button
                      onClick={() => handleCopyTicker(route.ticker || '')}
                      className="p-1 rounded bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white transition-colors cursor-pointer"
                      title="Copy ticker symbol"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Exchange</span>
                  <span className="text-sm font-bold text-emerald-400 font-mono mt-1 block">
                    {route.exchange} {route.country ? `(${route.country})` : ''}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Trading Coverage</span>
                  <span className="text-xs font-semibold text-blue-300 mt-1 block">
                    {isUSStock ? 'US Global Access' : 'Indian NSE / BSE'}
                  </span>
                </div>
              </div>

              {/* Share class note if applicable */}
              {route.share_class_note && (
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/25 flex items-start gap-2.5 text-xs text-blue-200">
                  <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                  <p className="leading-relaxed text-[11px]">{route.share_class_note}</p>
                </div>
              )}

              {/* Broker Selection Header */}
              <div className="flex items-center justify-between text-xs px-1 text-slate-300">
                <span className="font-semibold flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
                  <span>Choose Your Trading Destination:</span>
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  Both platforms supported • Select any
                </span>
              </div>

              {/* BOTH BROKER OPTIONS VISIBLE TOGETHER IN SIDE-BY-SIDE CARDS */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* OPTION 1: UPSTOX */}
                <div className="p-5 rounded-xl bg-gradient-to-br from-navy-950 to-navy-900 border border-blue-500/30 flex flex-col justify-between space-y-4 hover:border-blue-500/50 transition-all shadow-lg shadow-blue-950/20">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-xs">
                          U
                        </div>
                        <span className="font-bold text-white text-sm tracking-wide">
                          {isUSStock ? 'UPSTOX GLOBAL ACCESS' : 'UPSTOX PRO'}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono border bg-blue-500/20 text-blue-300 border-blue-500/30">
                        {isUSStock ? 'Global Access' : 'Direct Stock Link'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {isUSStock
                        ? "Continue to Upstox's US Stocks platform to review the selected security."
                        : `Continue to Upstox Pro to review real-time NSE charts, market depth, and execute your order for ${route.company}.`}
                    </p>

                    {upstoxUrl && (
                      <div className="p-2 rounded bg-navy-900/90 border border-navy-800 text-[10px] font-mono text-blue-400 flex items-center justify-between gap-2 overflow-hidden">
                        <span className="truncate">{upstoxUrl}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                      </div>
                    )}
                  </div>

                  <a
                    href={upstoxUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => {
                      if (upstoxBroker) {
                        e.preventDefault();
                        handleNavigateBroker(upstoxBroker);
                      }
                    }}
                    className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-900/30 transition-all cursor-pointer text-center"
                  >
                    <span>Open {route.company} on Upstox</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </a>
                </div>

                {/* OPTION 2: GROWW */}
                <div className="p-5 rounded-xl bg-gradient-to-br from-navy-950 to-navy-900 border border-emerald-500/30 flex flex-col justify-between space-y-4 hover:border-emerald-500/50 transition-all shadow-lg shadow-emerald-950/20">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
                          G
                        </div>
                        <span className="font-bold text-white text-sm tracking-wide">
                          {isUSStock ? 'GROWW US STOCKS' : 'GROWW'}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono border bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                        {isUSStock ? 'US Stocks' : 'Direct Stock Link'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {isUSStock
                        ? "Continue to Groww's US Stocks platform to review the selected security."
                        : `Continue to Groww to review real-time NSE quotes, interactive charts, and execute your trade for ${route.company}.`}
                    </p>

                    {growwUrl && (
                      <div className="p-2 rounded bg-navy-900/90 border border-navy-800 text-[10px] font-mono text-emerald-400 flex items-center justify-between gap-2 overflow-hidden">
                        <span className="truncate">{growwUrl}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                      </div>
                    )}
                  </div>

                  <a
                    href={growwUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => {
                      if (growwBroker) {
                        e.preventDefault();
                        handleNavigateBroker(growwBroker);
                      }
                    }}
                    className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/30 transition-all cursor-pointer text-center"
                  >
                    <span>Open {route.company} on Groww</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </a>
                </div>
              </div>

              {/* Utility Actions: Copy Ticker & Cancel */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
                {route.ticker && (
                  <button
                    type="button"
                    onClick={() => handleCopyTicker(route.ticker || '')}
                    className="w-full sm:w-auto py-2.5 px-4 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 hover:text-white border border-navy-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                    title="Copy ticker symbol to clipboard"
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
                )}

                <button
                  type="button"
                  onClick={onClose}
                  className="w-full sm:w-auto py-2.5 px-6 rounded-xl bg-navy-950 hover:bg-navy-800 text-slate-400 hover:text-white border border-navy-800 text-xs font-semibold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* CASE 2: General Market / Unmapped Headline */}
          {!loading && route && !isTradable && (
            <div className="p-6 rounded-xl bg-navy-950 border border-navy-800 space-y-4 text-center">
              <AlertCircle className="w-8 h-8 text-slate-500 mx-auto" />
              <div>
                <h4 className="text-sm font-semibold text-white">No Trading Destination Associated</h4>
                <p className="text-xs text-slate-400 mt-1.5 max-w-md mx-auto leading-relaxed">
                  This news headline covers macroeconomic developments, sector-wide indices, or an unverified instrument without an individual exchange equity association.
                </p>
              </div>
              <div className="pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-6 py-2.5 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 hover:text-white border border-navy-700 text-xs font-semibold transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Compliance & Security Disclaimer */}
          <div className="p-3.5 rounded-xl bg-navy-950/50 border border-navy-800/80 space-y-1.5 text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5 font-semibold text-slate-300">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>Compliance & Security Protocol</span>
            </div>
            <p className="leading-relaxed">
              FIN-SENTIMENT is an informational AI sentiment analytics platform and is not a registered broker-dealer. We never request or store brokerage credentials, API tokens, or execute automated trades. All trades must be confirmed directly by you on your authorized broker.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
