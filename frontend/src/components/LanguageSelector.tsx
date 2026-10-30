import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Check, Search, ChevronDown, RotateCcw } from 'lucide-react';
import { SUPPORTED_LANGUAGES, Language } from '../i18n/languages';

export const LanguageSelector: React.FC = () => {
  const { i18n, t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentCode = (i18n.language || 'en').toLowerCase().split('-')[0];
  const currentLang = SUPPORTED_LANGUAGES.find(
    (l) => l.code.toLowerCase() === i18n.language.toLowerCase() || l.code === currentCode
  ) || SUPPORTED_LANGUAGES[0];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectLanguage = (lang: Language) => {
    i18n.changeLanguage(lang.code);
    setIsOpen(false);
    setSearch('');
  };

  const handleResetToEnglish = () => {
    i18n.changeLanguage('en');
    setIsOpen(false);
    setSearch('');
  };

  const filteredLanguages = SUPPORTED_LANGUAGES.filter(
    (l) =>
      l.name.toLowerCase().includes(search.toLowerCase()) ||
      l.native.toLowerCase().includes(search.toLowerCase()) ||
      l.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-navy-900 hover:bg-navy-800 border border-navy-750 hover:border-cyan-500/40 text-slate-300 hover:text-white text-xs font-medium transition-all cursor-pointer shadow-sm"
        title={t('nav.language', 'Language')}
      >
        <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        <span className="font-semibold text-[11px] text-cyan-300 max-w-[80px] sm:max-w-[110px] truncate">
          {currentLang.native}
        </span>
        <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 max-h-96 bg-navy-900 border border-navy-700/80 rounded-xl shadow-2xl py-2 z-50 flex flex-col backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="px-3 pb-2 border-b border-navy-800 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span>{t('nav.language', 'Global Language')} (20)</span>
            </div>
            {currentLang.code !== 'en' && (
              <button
                onClick={handleResetToEnglish}
                className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 font-mono transition-colors"
                title={t('nav.resetToEnglish', 'Reset to English')}
              >
                <RotateCcw className="w-2.5 h-2.5" />
                <span>EN</span>
              </button>
            )}
          </div>

          {/* Search Input */}
          <div className="p-2 border-b border-navy-800">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search language / భాష..."
                className="w-full pl-8 pr-2 py-1 text-xs bg-navy-800/90 text-slate-100 placeholder-slate-400 rounded-md border border-navy-700 focus:outline-none focus:border-cyan-500"
                autoFocus
              />
            </div>
          </div>

          {/* Language Options List */}
          <div className="overflow-y-auto flex-1 py-1 divide-y divide-navy-850/50">
            {filteredLanguages.map((lang) => {
              const isSelected =
                lang.code === currentLang.code ||
                lang.code === i18n.language ||
                (lang.code === 'zh' && i18n.language.startsWith('zh'));

              return (
                <button
                  key={lang.code}
                  onClick={() => handleSelectLanguage(lang)}
                  className={`w-full px-3 py-2 text-left flex items-center justify-between text-xs transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-500/10 text-cyan-300 font-semibold border-l-2 border-cyan-400'
                      : 'text-slate-300 hover:bg-navy-800/80 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase px-1 py-0.5 rounded bg-navy-800 text-slate-400 border border-navy-700">
                      {lang.code}
                    </span>
                    <span className="text-white text-xs font-medium">{lang.native}</span>
                    <span className="text-slate-500 text-[11px]">({lang.name})</span>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-cyan-400 shrink-0" />}
                </button>
              );
            })}
            {filteredLanguages.length === 0 && (
              <div className="p-4 text-center text-xs text-slate-500">
                No matching language found.
              </div>
            )}
          </div>

          {/* Quick Return to English Button */}
          <div className="pt-2 px-3 border-t border-navy-800 flex justify-end">
            <button
              onClick={handleResetToEnglish}
              className="text-[11px] text-slate-400 hover:text-cyan-300 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>{t('nav.resetToEnglish', 'Reset to English')}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
