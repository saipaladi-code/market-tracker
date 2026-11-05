import React from 'react';
import { TrendingUp, Check } from 'lucide-react';
import { useBrokerPreference, BrokerId } from '../utils/brokerConfig';

interface BrokerSelectorProps {
  variant?: 'navbar' | 'sidebar' | 'compact';
  className?: string;
}

export const BrokerSelector: React.FC<BrokerSelectorProps> = ({
  variant = 'navbar',
  className = '',
}) => {
  const [selectedBroker, setBroker, hasExplicitSelection] = useBrokerPreference();

  const handleSelect = (broker: BrokerId) => {
    setBroker(broker);
  };

  if (variant === 'sidebar') {
    return (
      <div className={`space-y-1.5 ${className}`}>
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 uppercase tracking-wider">
          <span className="flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="font-semibold">Trading Broker</span>
          </span>
          {!hasExplicitSelection ? (
            <span className="text-[9px] font-bold text-amber-400 px-1.5 py-0.2 bg-amber-500/10 rounded border border-amber-500/30 animate-pulse">
              Choose
            </span>
          ) : (
            <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
              selectedBroker === 'upstox' 
                ? 'text-blue-300 bg-blue-500/10 border-blue-500/30' 
                : 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30'
            }`}>
              {selectedBroker === 'upstox' ? 'Upstox Active' : 'Groww Active'}
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-1 p-1 bg-navy-950/90 rounded-lg border border-navy-750">
          <button
            type="button"
            onClick={() => handleSelect('upstox')}
            className={`py-1.5 px-2 rounded-md text-[11px] font-semibold flex items-center justify-center gap-1 transition-all cursor-pointer ${
              selectedBroker === 'upstox' && hasExplicitSelection
                ? 'bg-blue-600 text-white shadow-sm shadow-blue-900/40 border border-blue-400/40'
                : 'text-slate-400 hover:text-white hover:bg-navy-850'
            }`}
            title="Route stock trades to Upstox Pro direct pages"
          >
            <span>Upstox Pro</span>
            {selectedBroker === 'upstox' && hasExplicitSelection && <Check className="w-3 h-3 text-blue-200" />}
          </button>
          <button
            type="button"
            onClick={() => handleSelect('groww')}
            className={`py-1.5 px-2 rounded-md text-[11px] font-semibold flex items-center justify-center gap-1 transition-all cursor-pointer ${
              selectedBroker === 'groww' && hasExplicitSelection
                ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-900/40 border border-emerald-400/40'
                : 'text-slate-400 hover:text-white hover:bg-navy-850'
            }`}
            title="Route stock trades to Groww direct pages"
          >
            <span>Groww</span>
            {selectedBroker === 'groww' && hasExplicitSelection && <Check className="w-3 h-3 text-emerald-200" />}
          </button>
        </div>
      </div>
    );
  }

  // Default: navbar pill
  return (
    <div
      className={`flex items-center gap-1 p-1 bg-navy-900/90 border border-navy-750 rounded-lg text-xs shrink-0 ${className}`}
      title="Choose default stock trading broker destination: Upstox Pro or Groww"
    >
      <span className="hidden md:inline text-[10px] font-mono text-slate-400 px-1 font-semibold uppercase shrink-0">
        Broker:
      </span>
      <button
        type="button"
        onClick={() => handleSelect('upstox')}
        className={`px-2 py-1 rounded text-[11px] font-medium transition-all cursor-pointer flex items-center gap-1 ${
          selectedBroker === 'upstox' && hasExplicitSelection
            ? 'bg-blue-600 text-white font-semibold shadow-sm border border-blue-400/30'
            : 'text-slate-400 hover:text-white hover:bg-navy-800'
        }`}
      >
        <span>Upstox</span>
        {selectedBroker === 'upstox' && hasExplicitSelection && <Check className="w-3 h-3 text-blue-200" />}
      </button>
      <button
        type="button"
        onClick={() => handleSelect('groww')}
        className={`px-2 py-1 rounded text-[11px] font-medium transition-all cursor-pointer flex items-center gap-1 ${
          selectedBroker === 'groww' && hasExplicitSelection
            ? 'bg-emerald-600 text-white font-semibold shadow-sm border border-emerald-400/30'
            : 'text-slate-400 hover:text-white hover:bg-navy-800'
        }`}
      >
        <span>Groww</span>
        {selectedBroker === 'groww' && hasExplicitSelection && <Check className="w-3 h-3 text-emerald-200" />}
      </button>
    </div>
  );
};
