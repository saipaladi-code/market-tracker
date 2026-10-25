import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface SentimentBadgeProps {
  sentiment?: 'positive' | 'negative' | 'neutral' | string;
  confidence?: number;
  showIcon?: boolean;
  size?: 'xs' | 'sm' | 'md';
}

export const SentimentBadge: React.FC<SentimentBadgeProps> = ({
  sentiment = 'neutral',
  confidence,
  showIcon = true,
  size = 'sm',
}) => {
  const norm = (sentiment || 'neutral').toLowerCase();

  let containerStyles = 'bg-slate-800/60 text-slate-300 border-slate-700/60';
  let dotColor = 'bg-slate-400';
  let Icon = Minus;
  let label = 'Neutral';

  if (norm === 'positive' || norm === 'bullish') {
    containerStyles = 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_-3px_rgba(16,185,129,0.2)]';
    dotColor = 'bg-emerald-400';
    Icon = TrendingUp;
    label = 'Bullish';
  } else if (norm === 'negative' || norm === 'bearish') {
    containerStyles = 'bg-rose-950/40 text-rose-400 border-rose-500/30 shadow-[0_0_12px_-3px_rgba(244,63,94,0.2)]';
    dotColor = 'bg-rose-400';
    Icon = TrendingDown;
    label = 'Bearish';
  } else if (norm === 'neutral') {
    containerStyles = 'bg-amber-950/40 text-amber-300 border-amber-500/30 shadow-[0_0_12px_-3px_rgba(245,158,11,0.2)]';
    dotColor = 'bg-amber-400';
    Icon = Minus;
    label = 'Neutral';
  }

  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-[10px] gap-1',
    sm: 'px-2.5 py-0.5 text-xs gap-1.5',
    md: 'px-3 py-1 text-xs gap-2',
  }[size];

  const iconSizes = {
    xs: 'w-2.5 h-2.5',
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-md font-medium border backdrop-blur-sm transition-all ${containerStyles} ${sizeClasses}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} shrink-0`} />
      {showIcon && <Icon className={`${iconSizes} shrink-0`} />}
      <span className="font-semibold tracking-wide uppercase text-[10px] sm:text-[11px]">{label}</span>
      {confidence !== undefined && (
        <span className="opacity-90 font-mono text-[10px] sm:text-[11px] font-bold border-l border-current/20 pl-1.5 ml-0.5">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
};
