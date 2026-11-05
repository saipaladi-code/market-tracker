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
  const [activeBrokerTab, setActiveBrokerTab] = useState<BrokerId>(() => initialBroker || getSelectedBroker());
  const [route, setRoute] = useState<CompanyTradingRoute | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBroker, setSelectedBroker] = useState<BrokerDestination | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [navNotice, setNavNotice] = useState<string | null>(null);
  const [blockedUrl, setBlockedUrl] = useState<string | null>(null);

  // Sync active broker if initialBroker changes when modal opens
  useEffect(() => {
    if (isOpen) {
      const preferred = initialBroker || getSelectedBroker();
      setActiveBrokerTab(preferred);
    }
  }, [isOpen, initialBroker]);

  // Resolve trading route whenever article, isOpen, or activeBrokerTab changes
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
        preferredBrokerId: activeBrokerTab,
      })
      .then((resolvedRoute) => {
        if (!isMounted) return;
        setRoute(resolvedRoute);

        // Pick matching broker destination
        const matchingBroker =
          resolvedRoute.brokers.find((b) => b.broker_id.toLowerCase() === activeBrokerTab.toLowerCase()) ||
          resolvedRoute.recommended_broker ||
          (resolvedRoute.brokers.length > 0 ? resolvedRoute.brokers[0] : null);

        setSelectedBroker(matchingBroker);
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
  }, [isOpen, article, activeBrokerTab]);

  if (!isOpen || !article) return null;

  const handleSwitchBroker = (newBroker: BrokerId) => {
    if (newBroker === activeBrokerTab) return;
    setActiveBrokerTab(newBroker);
    setSelectedBrokerPreference(newBroker);
  };

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

  const isIndianSupported = Boolean(route && route.is_tradable && route.country === 'IN');
  const isUSStock = Boolean(route && (route.country === 'US' || route.exchange === 'NASDAQ' || route.exchange === 'NYSE'));

  const primaryTargetUrl = selectedBroker && route
    ? brokerNavigationService.getDestinationUrl(route, selectedBroker, 'direct')
    : (route?.direct_url || '');

  const isUpstox = activeBrokerTab === 'upstox';
  const brokerDisplayName = isUpstox ? 'Upstox Pro' : 'Groww';

  // Dynamic Dialog Title
  let modalTitle = 'Broker Trade Routing';
  let modalSubtitle = 'Instrument Routing & Verification';
  if (route) {
    if (isIndianSupported) {
      modalTitle = isUpstox
        ? `Open ${route.company} in Upstox?`
        : `Open ${route.company} on Groww?`;
      modalSubtitle = isUpstox
        ? 'Verified Indian Equity (NSE / BSE) • Direct Upstox Pro Navigation'
        : 'Verified Indian Equity (NSE / BSE) • Direct Groww Navigation';
    } else if (isUSStock) {
      modalTitle = 'US Equities Unsupported on Indian Retail Brokers';
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
        <div className="px-5 sm:px-6 py-4 border-b border-navy-750 flex items-center justify-between sticky top-0 bg-navy-900/95 backdrop-blur-md z-10 gap-3">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isIndianSupported 
                ? isUpstox
                  ? 'bg-blue-500/15 border border-blue-500/30 text-blue-400'
                  : 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400' 
                : isUSStock 
                ? 'bg-amber-500/15 border border-amber-500/30 text-amber-400'
                : 'bg-blue-500/15 border border-blue-500/30 text-blue-400'
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
                Verifying exchange ticker and {brokerDisplayName} instrument catalog...
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
                  Click here to open {brokerDisplayName} directly
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          )}

          {/* CASE 1: Supported Indian Stock (Reliance, TCS, Infosys, Marico, etc.) */}
          {!loading && route && isIndianSupported && (
            <div className="space-y-4">
              {/* Broker Switcher Tabs */}
              <div className="p-1 rounded-xl bg-navy-950 border border-navy-800 flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => handleSwitchBroker('upstox')}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    isUpstox
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-900/40 border border-blue-400/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-navy-850'
                  }`}
                >
                  <span>Upstox Pro</span>
                  {isUpstox && <Check className="w-3.5 h-3.5 text-blue-200" />}
                </button>
                <button
                  type="button"
                  onClick={() => handleSwitchBroker('groww')}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    !isUpstox
                      ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/40 border border-emerald-400/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-navy-850'
                  }`}
                >
                  <span>Groww</span>
                  {!isUpstox && <Check className="w-3.5 h-3.5 text-emerald-200" />}
                </button>
              </div>

              {/* Instrument Overview Card */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-navy-950 border border-navy-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Symbol / Ticker</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm font-bold text-white font-mono notranslate" translate="no">{route.ticker}</span>
                    <button
                      onClick={() => handleCopyTicker(route.ticker || '')}
                      className="p-1 rounded bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white transition-colors cursor-pointer"
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
                  <span className="text-[10px] text-slate-400 font-mono uppercase block">Selected Broker</span>
                  <span className={`text-xs font-semibold mt-1 block truncate ${isUpstox ? 'text-blue-300' : 'text-emerald-300'}`}>
                    {brokerDisplayName} (Direct Page)
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

              {/* Broker Confirmation Card */}
              <div className={`p-5 rounded-xl bg-gradient-to-br from-navy-950 to-navy-900 border space-y-4 ${
                isUpstox ? 'border-blue-500/30' : 'border-emerald-500/30'
              }`}>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">
                      {isUpstox ? 'Upstox Pro Verified Stock Page' : 'Groww Verified Stock Page'}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                      isUpstox
                        ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                    }`}>
                      Direct Instrument Link
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {isUpstox
                      ? `You will be directed to the official ${route.company} page on Upstox Pro to review real-time NSE charts, market depth, and execute your order.`
                      : `You will be directed to the official ${route.company} page on Groww to review real-time NSE quotes, interactive charts, and execute your trade.`}
                  </p>
                </div>

                {/* Direct URL Preview */}
                {primaryTargetUrl && (
                  <div className="p-2.5 rounded-lg bg-navy-900/90 border border-navy-800 text-[11px] font-mono text-slate-400 flex items-center justify-between gap-2 overflow-hidden">
                    <span className={`truncate ${isUpstox ? 'text-blue-400' : 'text-emerald-400'}`}>
                      {primaryTargetUrl}
                    </span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  </div>
                )}

                {/* Primary Action Buttons: Continue to Selected Broker & Cancel */}
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
                    className={`w-full sm:flex-1 py-3 px-4 rounded-xl text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg transition-all cursor-pointer text-center ${
                      isUpstox
                        ? 'bg-blue-600 hover:bg-blue-500 shadow-blue-900/30'
                        : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30'
                    }`}
                  >
                    <span>{isUpstox ? 'Continue to Upstox' : 'Continue to Groww'}</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </a>

                  <button
                    type="button"
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
                    type="button"
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
                    Unsupported on Indian Brokers
                  </span>
                </div>
              </div>

              {/* Explicit Limitation Explanation */}
              <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/25 space-y-3">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>US Equities Trading Notice</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Indian retail brokers (Upstox and Groww) do not support active trading or direct order execution for US-listed equities (<strong className="text-white font-mono">{route.ticker}</strong> on <strong className="text-white">{route.exchange}</strong>). Retail US equity trading execution is restricted under RBI Liberalised Remittance Scheme (LRS) regulations.
                </p>
                <p className="text-[11px] text-slate-400">
                  FIN-SENTIMENT strictly refuses to route unsupported US securities to Indian order books or open misleading trade links. You may copy the ticker symbol for external research.
                </p>
              </div>

              {/* Action Buttons: Close and Copy Ticker */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                {route.ticker && (
                  <button
                    type="button"
                    onClick={() => handleCopyTicker(route.ticker || '')}
                    className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 hover:text-white border border-navy-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                    title="Copy ticker symbol"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span>Copied {route.ticker}!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 text-slate-400" />
                        <span>Copy Symbol ({route.ticker})</span>
                      </>
                    )}
                  </button>
                )}

                <button
                  type="button"
                  onClick={onClose}
                  className="w-full sm:w-auto py-3 px-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors cursor-pointer text-center"
                >
                  Close / Cancel
                </button>
              </div>
            </div>
          )}

          {/* CASE 3: General Market / Unsupported Headline */}
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
