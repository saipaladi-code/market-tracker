import React from 'react';
import { X, HelpCircle, AlertTriangle, Cpu, TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react';
import { SentimentAnalysisResult } from '../types';
import { SentimentBadge } from './SentimentBadge';

interface ExplainModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: SentimentAnalysisResult | null;
}

export const ExplainModal: React.FC<ExplainModalProps> = ({ isOpen, onClose, result }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-navy-750 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl space-y-5">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-navy-750 flex items-center justify-between sticky top-0 bg-navy-900/95 backdrop-blur-md z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">FinBERT Explainable AI Breakdown</h3>
              <p className="text-[10px] text-slate-400 font-mono">Token Perturbation Salience</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        {!result ? (
          <div className="p-12 text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mx-auto" />
            <p className="text-xs text-slate-400 font-mono">Computing Token Perturbation Masking on CPU...</p>
          </div>
        ) : (
          <div className="p-6 space-y-5 pt-0">
            {/* Headline Display */}
            <div>
              <label className="text-[10px] text-slate-400 uppercase font-mono tracking-wider font-semibold block mb-1.5">
                Analyzed Financial Headline
              </label>
              <p className="p-3.5 bg-navy-950 rounded-xl border border-navy-800 text-xs font-medium text-slate-100 leading-relaxed">
                "{result.text}"
              </p>
            </div>

            {/* Verdict Header */}
            <div className="flex items-center justify-between p-3.5 bg-navy-950 rounded-xl border border-navy-800">
              <div>
                <span className="text-[10px] text-slate-400 block font-mono">Predicted Class</span>
                <SentimentBadge sentiment={result.sentiment} confidence={result.confidence} size="md" />
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block font-mono">Model</span>
                <span className="text-xs font-mono font-semibold text-white">{result.model_name}</span>
              </div>
            </div>

            {/* Class Probabilities Distribution */}
            <div className="grid grid-cols-3 gap-2.5 text-center">
              <div className="p-3 bg-navy-950 rounded-xl border border-navy-800">
                <span className="text-[10px] text-slate-400 block mb-1">Bullish</span>
                <span className="text-base font-bold text-emerald-400 font-mono">
                  {(result.scores.positive * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-3 bg-navy-950 rounded-xl border border-navy-800">
                <span className="text-[10px] text-slate-400 block mb-1">Neutral</span>
                <span className="text-base font-bold text-amber-400 font-mono">
                  {(result.scores.neutral * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-3 bg-navy-950 rounded-xl border border-navy-800">
                <span className="text-[10px] text-slate-400 block mb-1">Bearish</span>
                <span className="text-base font-bold text-rose-400 font-mono">
                  {(result.scores.negative * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Perturbation-based Word Salience */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-[10px] text-slate-400 uppercase font-mono tracking-wider font-semibold flex items-center gap-1.5">
                  <span>Token Attribution Impact</span>
                  <span title="Calculates delta confidence drop when individual token is masked.">
                    <HelpCircle className="w-3 h-3 text-slate-500" />
                  </span>
                </label>
                <span className="text-[10px] text-blue-400 font-mono">Method: Single Token Masking ΔP</span>
              </div>

              {result.tokens && result.tokens.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {result.tokens.map((token, idx) => {
                    const isPositiveImpact = token.impact > 0;
                    return (
                      <div
                        key={idx}
                        className="flex items-center justify-between px-3 py-2 bg-navy-950/80 border border-navy-800 rounded-lg text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-blue-300 font-bold bg-blue-900/30 px-2 py-0.5 rounded border border-blue-800/40">
                            {token.token}
                          </span>
                          <span className="text-slate-400 text-[11px] capitalize">
                            direction: <strong className="text-slate-200">{token.direction}</strong>
                          </span>
                        </div>
                        <div className="font-mono font-bold text-xs">
                          <span className={isPositiveImpact ? 'text-emerald-400' : 'text-slate-400'}>
                            {isPositiveImpact ? `+${(token.impact * 100).toFixed(1)}%` : `${(token.impact * 100).toFixed(1)}%`}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic p-3 bg-navy-950 rounded-xl border border-navy-800">
                  Single token text or uniform attention distribution.
                </p>
              )}
            </div>

            {/* Limitations Notice */}
            <div className="p-3.5 bg-navy-950 border border-navy-800 rounded-xl text-xs space-y-1 text-slate-400">
              <div className="flex items-center gap-2 font-bold text-slate-300">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Scientific Attribution Note</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                Word salience evaluates how removing tokens impacts FinBERT's semantic classification.
                This provides insight into lexical weighting and does not reflect security fundamentals.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
