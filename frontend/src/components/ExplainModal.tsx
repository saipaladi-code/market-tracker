import React from 'react';
import { X, HelpCircle, AlertTriangle, Info, Cpu } from 'lucide-react';
import { SentimentAnalysisResult } from '../types';
import { SentimentBadge } from './SentimentBadge';

interface ExplainModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: SentimentAnalysisResult | null;
}

export const ExplainModal: React.FC<ExplainModalProps> = ({ isOpen, onClose, result }) => {
  if (!isOpen || !result) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-navy-750 rounded-xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-navy-700/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-400" />
            <h3 className="font-semibold text-white text-base">FinBERT Prediction Breakdown</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Headline Display */}
          <div>
            <label className="text-xs text-slate-400 uppercase font-mono tracking-wider block mb-1">
              Analyzed Financial Headline
            </label>
            <p className="p-3 bg-navy-950 rounded-lg border border-navy-800 text-sm font-medium text-slate-100 leading-relaxed">
              "{result.text}"
            </p>
          </div>

          {/* Model Class Probabilities */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-navy-950 rounded-lg border border-navy-800 text-center">
              <span className="text-xs text-slate-400 block mb-1">Positive Prob</span>
              <span className="text-lg font-bold text-emerald-400 font-mono">
                {(result.scores.positive * 100).toFixed(1)}%
              </span>
            </div>
            <div className="p-3 bg-navy-950 rounded-lg border border-navy-800 text-center">
              <span className="text-xs text-slate-400 block mb-1">Neutral Prob</span>
              <span className="text-lg font-bold text-amber-400 font-mono">
                {(result.scores.neutral * 100).toFixed(1)}%
              </span>
            </div>
            <div className="p-3 bg-navy-950 rounded-lg border border-navy-800 text-center">
              <span className="text-xs text-slate-400 block mb-1">Negative Prob</span>
              <span className="text-lg font-bold text-rose-400 font-mono">
                {(result.scores.negative * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Perturbation-based Word Salience */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-slate-400 uppercase font-mono tracking-wider flex items-center gap-1.5">
                <span>Perturbation Attribution Salience</span>
                <span title="Measures drop in confidence when the token is masked.">
                  <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                </span>
              </label>
              <span className="text-[11px] text-blue-400 font-mono">Method: Token Masking Delta</span>
            </div>

            {result.tokens && result.tokens.length > 0 ? (
              <div className="space-y-2">
                {result.tokens.map((token, idx) => {
                  const isPositiveImpact = token.impact > 0;
                  return (
                    <div
                      key={idx}
                      className="flex items-center justify-between px-3 py-2 bg-navy-950/70 border border-navy-800 rounded-md text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-blue-300 font-semibold bg-blue-900/30 px-2 py-0.5 rounded border border-blue-800/40">
                          {token.token}
                        </span>
                        <span className="text-slate-400">
                          direction: <strong className="text-slate-200 capitalize">{token.direction}</strong>
                        </span>
                      </div>
                      <div className="font-mono font-medium">
                        <span className={isPositiveImpact ? 'text-emerald-400' : 'text-slate-400'}>
                          {isPositiveImpact ? `+${(token.impact * 100).toFixed(1)}%` : `${(token.impact * 100).toFixed(1)}%`}
                        </span>
                        <span className="text-slate-500 text-[10px] ml-1">delta</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-3 bg-navy-950 rounded border border-navy-800">
                Single-token sentence or uniform attribution across tokens.
              </p>
            )}
          </div>

          {/* AI Attribution & Financial Limitations Disclaimer */}
          <div className="p-3.5 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs space-y-1.5 text-amber-200/90">
            <div className="flex items-center gap-2 font-semibold text-amber-400">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Model Scope & Attribution Limitations</span>
            </div>
            <p className="leading-relaxed">
              {result.explanation_note}
            </p>
            <p className="text-[11px] text-amber-300/70">
              Highlighted tokens are evaluated via local perturbation (observing softmax shift upon word masking). 
              Never equate text tone with guaranteed equity price trajectory.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-navy-700/60 bg-navy-950/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-navy-800 hover:bg-navy-750 text-slate-200 rounded-md text-xs font-medium transition-colors"
          >
            Close Breakdown
          </button>
        </div>
      </div>
    </div>
  );
};
