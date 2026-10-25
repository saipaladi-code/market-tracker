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
  Cpu
} from 'lucide-react';

interface SidebarProps {
  modelStatus?: string;
  isDemo?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ modelStatus = 'ready', isDemo = false }) => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'FinBERT Live Lab', path: '/analyze', icon: Sparkles },
    { name: 'Financial News Feed', path: '/news', icon: Newspaper },
    { name: 'Company Deep Dive', path: '/companies', icon: Building2 },
    { name: 'Sentiment Conflicts', path: '/conflicts', icon: GitCompareArrows },
    { name: 'Sector Heatmap', path: '/sectors', icon: Grid3X3 },
    { name: 'Alerts & History', path: '/alerts', icon: BellRing },
    { name: 'Data Quality & Health', path: '/data-quality', icon: ShieldCheck },
    { name: 'AI News Assistant', path: '/assistant', icon: BotMessageSquare },
  ];

  return (
    <aside className="w-64 bg-navy-900 border-r border-navy-700/60 flex flex-col shrink-0 min-h-screen">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-navy-700/60">
        <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-wide text-white">FIN-SENTIMENT</h1>
          <p className="text-[11px] text-slate-400 font-mono">FinBERT AI Platform</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div className="p-4 border-t border-navy-700/60 bg-navy-950/40 space-y-2">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">FinBERT Model</span>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            {modelStatus.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">News Source</span>
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${
            isDemo 
              ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
              : 'bg-blue-500/10 text-blue-300 border-blue-500/20'
          }`}>
            {isDemo ? 'DEMO DATASET' : 'LIVE NEWSAPI'}
          </span>
        </div>
      </div>
    </aside>
  );
};
