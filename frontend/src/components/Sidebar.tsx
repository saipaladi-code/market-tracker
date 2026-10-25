import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Sparkles,
  Newspaper,
  Building2,
  GitCompareArrows,
  Grid3X3,
  BellRing,
  ShieldCheck,
  BotMessageSquare,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Cpu,
  Database,
  Globe,
  X
} from 'lucide-react';

interface SidebarProps {
  modelStatus?: string;
  isDemo?: boolean;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  activeConflictsCount?: number;
  unreadAlertsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  modelStatus = 'ready',
  isDemo = false,
  isCollapsed,
  setIsCollapsed,
  mobileOpen,
  setMobileOpen,
  activeConflictsCount = 0,
  unreadAlertsCount = 0,
}) => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard, badge: null },
    { name: 'FinBERT Live Lab', path: '/analyze', icon: Sparkles, badge: 'CPU' },
    { name: 'Financial News Feed', path: '/news', icon: Newspaper, badge: null },
    { name: 'Company Deep Dive', path: '/companies', icon: Building2, badge: null },
    {
      name: 'Sentiment Conflicts',
      path: '/conflicts',
      icon: GitCompareArrows,
      badge: activeConflictsCount > 0 ? String(activeConflictsCount) : null,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30'
    },
    { name: 'Sector Heatmap', path: '/sectors', icon: Grid3X3, badge: null },
    {
      name: 'Alerts & History',
      path: '/alerts',
      icon: BellRing,
      badge: unreadAlertsCount > 0 ? String(unreadAlertsCount) : null,
      badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30'
    },
    { name: 'Data Quality & Health', path: '/data-quality', icon: ShieldCheck, badge: null },
    { name: 'AI News Assistant', path: '/assistant', icon: BotMessageSquare, badge: 'RAG' },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-navy-950 border-r border-navy-750/70 select-none">
      {/* Brand Header */}
      <div className={`h-16 flex items-center px-4 border-b border-navy-750/60 justify-between ${isCollapsed ? 'justify-center px-2' : ''}`}>
        {!isCollapsed ? (
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 shrink-0">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-sm tracking-wider text-white">FIN-SENTIMENT</span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  PRO
                </span>
              </div>
              <p className="text-[10px] text-slate-400 truncate tracking-tight">AI Financial News Intelligence</p>
            </div>
          </div>
        ) : (
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 shrink-0" title="FIN-SENTIMENT">
            <TrendingUp className="w-5 h-5" />
          </div>
        )}

        {/* Mobile close button */}
        <button
          onClick={() => setMobileOpen(false)}
          className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors"
          aria-label="Close navigation"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              title={isCollapsed ? item.name : undefined}
              className={({ isActive }) =>
                `group flex items-center rounded-lg font-medium transition-all duration-150 relative ${
                  isCollapsed ? 'justify-center px-2 py-2.5' : 'px-3 py-2.5 gap-3 text-xs'
                } ${
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 font-semibold shadow-sm shadow-blue-600/10'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-navy-850/80 border border-transparent'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-blue-500 rounded-r-full" />
                  )}
                  <Icon className={`w-4 h-4 shrink-0 transition-colors ${isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                  
                  {!isCollapsed && (
                    <div className="flex-1 flex items-center justify-between min-w-0">
                      <span className="truncate">{item.name}</span>
                      {item.badge && (
                        <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${item.badgeColor || 'bg-navy-800 text-slate-300 border-navy-700'}`}>
                          {item.badge}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Tooltip on collapsed state */}
                  {isCollapsed && (
                    <div className="absolute left-full ml-3 px-2.5 py-1 bg-navy-800 text-slate-100 text-xs rounded-md shadow-xl border border-navy-700 whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50">
                      {item.name}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Telemetry / Status */}
      <div className={`p-3 border-t border-navy-750/60 bg-navy-900/60 ${isCollapsed ? 'text-center' : 'space-y-2'}`}>
        {!isCollapsed ? (
          <>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                <span>FinBERT AI</span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {modelStatus.toUpperCase()}
              </span>
            </div>

            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-cyan-400" />
                <span>News Feed</span>
              </span>
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                isDemo 
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                  : 'bg-blue-500/10 text-blue-300 border-blue-500/20'
              }`}>
                {isDemo ? 'DEMO DATA' : 'LIVE API'}
              </span>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2" title={`FinBERT: ${modelStatus} | News: ${isDemo ? 'Demo' : 'Live'}`}>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>
        )}

        {/* Desktop Collapse Toggle Button */}
        <div className="pt-2 hidden md:block">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="w-full flex items-center justify-center gap-2 p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-navy-800 transition-colors text-xs"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : (
              <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-medium">
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Collapse Terminal</span>
              </div>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        className={`hidden md:block shrink-0 transition-all duration-200 h-screen sticky top-0 z-30 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/75 backdrop-blur-sm z-40 md:hidden animate-in fade-in duration-200"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile Slide-in Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 w-72 z-50 md:hidden transform transition-transform duration-200 ease-in-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
};
