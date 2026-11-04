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
  CheckCircle2,
  ExternalLink,
  Info,
  Compass
} from 'lucide-react';
import { Article, CompanyTradingRoute, BrokerDestination } from '../types';
import { SentimentBadge } from './SentimentBadge';
import { brokerNavigationService, NavigationResult } from '../services/brokerNavigationService';

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
  const [navNotice, setNavNotice] = useState<string | null>(null);
  const [blockedUrl, setBlockedUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !article) {
      setRoute(null);
      setSelectedBroker(null);
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

    brokerNavigationService
      .resolveRoute({
        company: article.company,
        ticker: article.ticker,
      })
      .then((resolvedRoute) => {
        if (!isMounted) return;
        setRoute(resolvedRoute);
        const broker =
          resolvedRoute.recommended_broker ||
          (resolvedRoute.brokers.length > 0 ? resolvedRoute.brokers[0] : null);
        setSelectedBroker(broker);
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
  }, [isOpen, article]);

  if (!isOpen || !article) return null;

  const handleCopyTicker = (tickerText: string) => {
    if (!tickerText) return;
    navigator.clipboard.writeText(tickerText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNavigate = (destinationPreference: 'direct' | 'portal' = 'direct') => {
    if (!route || !selectedBroker) return;
    setNavNotice(null);
    setBlockedUrl(null);

    const result: NavigationResult = brokerNavigationService.openDestination(
      route,
      selectedBroker,
      destinationPreference
    );

    if (result.isBlockedByPopup && result.openedUrl) {
      setBlockedUrl(result.openedUrl);
      setNavNotice('Pop-up window was blocked by your browser. Click the direct link below.');
    } else if (!result.success) {
      setError(result.message || 'Failed to navigate to broker destination.');
    }
  };

  const isDirectInstrument = route?.destination_type === 'direct_instrument';
  const isIndianSupported = Boolean(route && route.is_tradable && route.country === 'IN');
  const isUSStock = Boolean(route && (route.country === 'US' || route.exchange === 'NASDAQ' || route.exchange === 'NYSE'));

  const primaryTargetUrl = selectedBroker && route
    ? brokerNavigationService.getDestinationUrl(route, selectedBroker, 'direct')
    : (route?.direct_url || '');

  // Dynamic Dialog Title
  let modalTitle = 'Broker Trade Routing';
  let modalSubtitle = 'Instrument Routing & Verification';
  if (route) {
    if (isIndianSupported) {
      modalTitle = `Open ${route.company} on Groww?`;
      modalSubtitle = 'Verified Indian Equity (NSE / BSE) • Direct Stock Navigation';
    } else if (isUSStock) {
      modalTitle = 'US Stocks Not Supported on Groww';
      modalSubtitle = `${route.company} (${route.ticker || 'US Equity'}) • Market Coverage Notice`;
    } else {
      modalTitle = 'Trading Destination Unavailable';
      modalSubtitle = 'Macroeconomic / Unmapped Instrument';
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-navy-750 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl space-y-5">
        {/* Header */}
        <div className="px-6 py-4 border-b border-navy-750 flex items-center justify-between sticky top-0 bg-navy-900/95 backdrop-blur-md z-10">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isIndianSupported 
                ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400' 
                : isUSStock 
                ? 'bg-amber-500/15 border border-amber-500/30 text-amber-400'
                : 'bg-blue-500/15 border border-blue-500/30 text-blue-400'
            }`}>
              <TrendingUp className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">{modalTitle}</h3>
              <p className="text-[10px] text-slate-400 font-mono">
                {modalSubtitle}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors cursor-pointer"
            title="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 pt-0">
          {/* Article Context Header */}
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
                Verifying exchange ticker and Groww instrument catalog...
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
                  Click here to open Groww directly
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          )}

          {/* CASE 1: Supported Indian Stock (Reliance, TCS, Infosys, etc.) */}
          {!loading && route && isIndianSupported && (
            <div className="space-y-4">
              {/* Instrument Overview Card */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Symbol / Ticker</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm font-bold text-white font-mono notranslate" translate="no">{route.ticker}</span>
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
                    {route.exchange} (India)
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800 col-span-2 sm:col-span-1">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Broker Destination</span>
                  <span className="text-xs font-semibold text-emerald-300 mt-1 block truncate">
                    Groww (Direct Page)
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

              {/* Groww Confirmation Card */}
              <div className="p-5 rounded-xl bg-gradient-to-br from-navy-950 to-navy-900 border border-emerald-500/30 space-y-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">Groww Verified Stock Page</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-mono border border-emerald-500/30">
                      Direct Instrument Link
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    You will be directed to the official {route.company} page on Groww to review real-time NSE quotes, interactive charts, and execute your trade.
                  </p>
                </div>

                {/* Direct URL Preview */}
                {primaryTargetUrl && (
                  <div className="p-2.5 rounded-lg bg-navy-900/90 border border-navy-800 text-[11px] font-mono text-slate-400 flex items-center justify-between gap-2 overflow-hidden">
                    <span className="truncate text-emerald-400">{primaryTargetUrl}</span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  </div>
                )}

                {/* Primary Action Buttons: Continue to Groww & Cancel */}
                <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                  <a
                    href={primaryTargetUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => {
                      if (!primaryTargetUrl) {
                        e.preventDefault();
                        handleNavigate('direct');
                      }
                    }}
                    className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/30 transition-all cursor-pointer text-center"
                  >
                    <span>Continue to Groww</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </a>

                  <button
                    onClick={() => handleCopyTicker(route.ticker || '')}
                    className="w-full sm:w-auto py-3 px-4 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 hover:text-white border border-navy-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
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
                        <span>Copy Ticker</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={onClose}
                    className="w-full sm:w-auto py-3 px-4 rounded-xl bg-navy-950 hover:bg-navy-800 text-slate-400 hover:text-white border border-navy-800 text-xs font-semibold transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* CASE 2: US Stock (Apple, Amazon, Nvidia, Tesla, etc.) */}
          {!loading && route && isUSStock && (
            <div className="space-y-4">
              {/* Instrument Overview Card */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Company</span>
                  <span className="text-sm font-bold text-white font-mono mt-1 block truncate">
                    {route.company}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Symbol / Exchange</span>
                  <span className="text-sm font-bold text-amber-400 font-mono mt-1 block">
                    {route.ticker} • {route.exchange}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800 col-span-2 sm:col-span-1">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Trading Status</span>
                  <span className="text-xs font-semibold text-rose-400 mt-1 block">
                    Unsupported on Groww
                  </span>
                </div>
              </div>

              {/* Explicit Limitation Explanation */}
              <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/25 space-y-3">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>US Equities Order Execution Notice</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Groww does not currently support active trading or direct order execution for US-listed equities (<strong className="text-white font-mono">{route.ticker}</strong> on <strong className="text-white">{route.exchange}</strong>). Retail US stock onboarding and active trading execution have been discontinued under RBI Liberalised Remittance Scheme (LRS) regulations.
                </p>
                <p className="text-[11px] text-slate-400">
                  FIN-SENTIMENT never silently routes unsupported securities to an unrelated order book. You may view Groww's general US stock directory for informational research, but live order execution is unavailable.
                </p>
              </div>

              {/* Action Buttons: Cancel and Optional Directory link */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                <button
                  onClick={onClose}
                  className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors cursor-pointer text-center"
                >
                  Close / Cancel
                </button>

                <a
                  href="https://groww.in/us-stocks/popular-us-stocks-and-etfs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full sm:w-auto py-3 px-4 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white border border-navy-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <span>Groww US Directory</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>

                {route.ticker && (
                  <button
                    onClick={() => handleCopyTicker(route.ticker || '')}
                    className="w-full sm:w-auto py-3 px-4 rounded-xl bg-navy-950 hover:bg-navy-800 text-slate-400 hover:text-white border border-navy-800 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                    title="Copy ticker symbol"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Symbol</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* CASE 3: General Market / Unsupported Company */}
          {!loading && route && !isIndianSupported && !isUSStock && (
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
