import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  RefreshCw,
  AlertCircle,
  Search,
  Menu,
  Clock,
  Server,
  LogOut,
  ChevronDown
} from 'lucide-react';

interface NavbarProps {
  lastUpdated?: string;
  isDemo?: boolean;
  feedStatus?: string;
  onRefresh?: () => Promise<void>;
  onOpenMobileMenu?: () => void;
  onOpenBackendSettings?: () => void;
}

const PAGE_METADATA: Record<string, { title: string; section: string; desc: string }> = {
  '/': { title: 'Executive Sentiment Overview', section: 'Analytics Terminal', desc: 'Real-time tone & divergence metrics' },
  '/analyze': { title: 'FinBERT Interactive Lab', section: 'AI Testing Workbench', desc: 'Direct financial sentiment & explainable AI analysis' },
  '/news': { title: 'Financial News Intelligence Feed', section: 'Data Stream', desc: 'Classified headlines with duplicate filtering' },
  '/companies': { title: 'Company Sentiment Deep Dive', section: 'Securities Analysis', desc: 'Individual stock tone & coverage breakdown' },
  '/conflicts': { title: 'Bullish/Bearish Conflict Detector', section: 'Divergence Engine', desc: 'Companies facing simultaneous opposing narratives' },
  '/sectors': { title: 'Market Sector Sentiment Heatmap', section: 'Macro Analytics', desc: 'Net tone distribution across economic sectors' },
  '/alerts': { title: 'Sentiment Alerts & Risk Watchlist', section: 'Risk Surveillance', desc: 'Automated warnings for negative sentiment surges' },
  '/data-quality': { title: 'System Integrity & Telemetry', section: 'Operations & QA', desc: 'FinBERT health, provider status & deduplication metrics' },
  '/assistant': { title: 'AI News Research Assistant', section: 'Conversational Intelligence', desc: 'Grounded question answering over news corpus' },
};

const TRACKED_COMPANIES = [
  { name: 'Nvidia', ticker: 'NVDA' },
  { name: 'Apple', ticker: 'AAPL' },
  { name: 'Microsoft', ticker: 'MSFT' },
  { name: 'Tesla', ticker: 'TSLA' },
  { name: 'Alphabet', ticker: 'GOOGL' },
  { name: 'Amazon', ticker: 'AMZN' },
  { name: 'JPMorgan Chase', ticker: 'JPM' },
  { name: 'Pfizer', ticker: 'PFE' },
  { name: 'ExxonMobil', ticker: 'XOM' },
];

export const Navbar: React.FC<NavbarProps> = ({
  lastUpdated,
  isDemo = false,
  feedStatus = 'LIVE FEED',
  onRefresh,
  onOpenMobileMenu,
  onOpenBackendSettings,
}) => {
  const { user, logout } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentMeta = PAGE_METADATA[location.pathname] || {
    title: 'Financial Market Sentiment Tracker',
    section: 'Intelligence Platform',
    desc: 'FinBERT AI Analysis'
  };

  const handleRefresh = async () => {
    if (!onRefresh) return;
    try {
      setRefreshing(true);
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  const filteredCompanies = TRACKED_COMPANIES.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.ticker.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectCompany = (companyName: string) => {
    setSearchQuery('');
    setIsSearchOpen(false);
    navigate(`/companies?company=${encodeURIComponent(companyName)}`);
  };

  return (
    <header className="h-16 bg-navy-950/90 border-b border-navy-750/70 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20 backdrop-blur-md">
      {/* Left: Mobile hamburger & Page Breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors"
          aria-label="Open mobile navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:block">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">{currentMeta.section}</span>
            <span className="text-slate-600">/</span>
            <h1 className="font-semibold text-white tracking-tight">{currentMeta.title}</h1>
          </div>
          <p className="text-[11px] text-slate-400 truncate max-w-md hidden lg:block">
            {currentMeta.desc}
          </p>
        </div>
      </div>

      {/* Center: Global Search Bar */}
      <div className="relative max-w-xs sm:max-w-sm w-full mx-2 sm:mx-4">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsSearchOpen(true);
            }}
            onFocus={() => setIsSearchOpen(true)}
            placeholder="Search company (e.g. NVDA, Apple)..."
            className="w-full bg-navy-900/90 border border-navy-750 rounded-lg pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-sans"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery('');
                setIsSearchOpen(false);
              }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
            >
              ✕
            </button>
          )}
        </div>

        {/* Search Results Dropdown */}
        {isSearchOpen && searchQuery.trim().length > 0 && (
          <div className="absolute top-full mt-1.5 left-0 w-full bg-navy-900 border border-navy-700 rounded-lg shadow-2xl py-1 z-50 text-xs max-h-60 overflow-y-auto">
            <div className="px-3 py-1.5 text-[10px] font-mono uppercase text-slate-500 border-b border-navy-800">
              Matched Monitored Securities
            </div>
            {filteredCompanies.length > 0 ? (
              filteredCompanies.map((c) => (
                <button
                  key={c.ticker}
                  onClick={() => handleSelectCompany(c.name)}
                  className="w-full text-left px-3 py-2 hover:bg-navy-800 flex items-center justify-between text-slate-200 transition-colors"
                >
                  <span className="font-medium text-white">{c.name}</span>
                  <span className="font-mono text-blue-400 font-semibold bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
                    {c.ticker}
                  </span>
                </button>
              ))
            ) : (
              <div className="px-3 py-3 text-slate-400 text-center">
                No tracked company found for "{searchQuery}".
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Controls: Freshness, Mode, Refresh, Profile */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Data Mode Indicator */}
        {feedStatus === 'LIVE FEED' || (!isDemo && feedStatus !== 'DEMO DATA' && feedStatus !== 'API ERROR') ? (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-medium" title="Live financial news stream active">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="hidden md:inline font-mono">LIVE FEED</span>
          </div>
        ) : feedStatus === 'CACHED LIVE DATA' ? (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-300 text-[11px] font-medium" title="Displaying cached genuine articles">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden md:inline font-mono">CACHED LIVE DATA</span>
          </div>
        ) : feedStatus === 'API ERROR' ? (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px] font-medium" title="News provider or backend is unreachable">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden md:inline font-mono">API ERROR</span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] font-medium" title="Demonstration dataset active">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline font-mono">DEMO DATASET</span>
          </div>
        )}

        {/* Data Freshness Indicator */}
        <div className="hidden xl:flex items-center gap-2 text-[11px] text-slate-400 border border-navy-750 bg-navy-900/80 px-2.5 py-1 rounded-md">
          <Clock className="w-3.5 h-3.5 text-blue-400" />
          <span>Synced: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : 'Live'}</span>
        </div>

        {/* Backend Settings Button */}
        {onOpenBackendSettings && (
          <button
            onClick={onOpenBackendSettings}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-navy-900 hover:bg-navy-800 border border-navy-750 text-slate-300 hover:text-white text-xs font-medium transition-colors cursor-pointer"
            title="Configure Backend Server Endpoint"
          >
            <Server className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden sm:inline text-[11px] font-mono">Backend</span>
          </button>
        )}

        {/* Global Refresh Button */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition-all cursor-pointer"
          title="Fetch fresh articles and trigger FinBERT sentiment classification"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">{refreshing ? 'Syncing...' : 'Ingest News'}</span>
        </button>

        {/* Analyst Session Badge / User Dropdown */}
        {user ? (
          <div className="relative pl-2 border-l border-navy-750" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-navy-800/80 border border-transparent hover:border-navy-700 transition-colors cursor-pointer"
              title={`Logged in as ${user.full_name} (${user.email})`}
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 text-white font-bold text-[11px] flex items-center justify-center shadow-sm">
                {user.full_name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
                  .slice(0, 2)
                  .toUpperCase() || 'AN'}
              </div>
              <div className="hidden lg:flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-200 leading-tight truncate max-w-[120px]">
                  {user.full_name}
                </span>
                <span className="text-[10px] text-cyan-400 font-mono leading-tight">Analyst</span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
            </button>

            {/* Dropdown Menu */}
            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-navy-900 border border-navy-750 shadow-2xl py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3 py-2 border-b border-navy-750/70">
                  <p className="text-xs font-bold text-white truncate">{user.full_name}</p>
                  <p className="text-[11px] text-slate-400 font-mono truncate">{user.email}</p>
                  <div className="flex items-center gap-1.5 mt-1.5 text-[10px] text-emerald-400 font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Active Session</span>
                  </div>
                </div>

                <div className="pt-1">
                  <button
                    onClick={async () => {
                      setUserMenuOpen(false);
                      await logout();
                      navigate('/login');
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-300 hover:text-rose-200 hover:bg-rose-500/10 transition-colors text-left cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5 text-rose-400" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="pl-2 border-l border-navy-750">
            <button
              onClick={() => navigate('/login')}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors"
            >
              Sign In
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
