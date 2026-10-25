import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface SentimentBadgeProps {
  sentiment?: 'positive' | 'negative' | 'neutral' | string;
  confidence?: number;
  showIcon?: boolean;
}

export const SentimentBadge: React.FC<SentimentBadgeProps> = ({
  sentiment = 'neutral',
  confidence,
  showIcon = true,
}) => {
  const norm = sentiment.toLowerCase();

  let styles = 'bg-slate-700/40 text-slate-300 border-slate-600/40';
  let Icon = Minus;

  if (norm === 'positive' || norm === 'bullish') {
    styles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    Icon = TrendingUp;
  } else if (norm === 'negative' || norm === 'bearish') {
    styles = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    Icon = TrendingDown;
  } else if (norm === 'neutral') {
    styles = 'bg-amber-500/10 text-amber-300 border-amber-500/20';
    Icon = Minus;
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${styles}`}>
      {showIcon && <Icon className="w-3 h-3" />}
      <span className="capitalize">{norm}</span>
      {confidence !== undefined && (
        <span className="opacity-75 text-[10px] font-mono">({Math.round(confidence * 100)}%)</span>
      )}
    </span>
  );
};
