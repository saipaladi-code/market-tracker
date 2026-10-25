import React, { useState } from 'react';
import {
  BotMessageSquare,
  Send,
  Sparkles,
  ExternalLink,
  AlertTriangle,
  RefreshCw,
  HelpCircle,
  FileText,
  User,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2
} from 'lucide-react';
import { api } from '../services/api';
import { AssistantChatResponse } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    title: string;
    source: string;
    url: string;
    sentiment: string;
    confidence: number;
    company: string;
  }>;
  disclaimer?: string;
  timestamp: string;
}

export const AssistantPage: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Welcome to FIN-SENTIMENT Assistant. I answer research queries strictly grounded in currently indexed news articles and local FinBERT tone classifications. How can I assist your market analysis today?',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (queryText?: string) => {
    const text = (queryText !== undefined ? queryText : input).trim();
    if (!text || loading) return;

    const userMsg: Message = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const data: AssistantChatResponse = await api.chatAssistant(text);
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.response,
        citations: data.relevant_articles,
        disclaimer: data.disclaimer,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'An error occurred while contacting the financial intelligence service. Please verify your backend server connection.',
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sampleQueries = [
    'What is the overall sentiment of the available financial news?',
    'Which companies face the strongest negative news headlines?',
    'Compare news sentiment between Nvidia and Tesla',
    'Explain the current conflicting news signals',
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md shadow-sm">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <BotMessageSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono font-bold uppercase tracking-wider">
                GROUNDED RAG INTELLIGENCE
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              AI Financial News Research Assistant
            </h2>
          </div>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed max-w-2xl mt-1">
          Inquiries are synthesized using strictly verified news articles and FinBERT tone classifications.
          The assistant explains narrative divergence, cites exact article sources, and does not fabricate market prices.
        </p>
      </div>

      {/* Suggested Questions Carousel */}
      <div className="space-y-2">
        <span className="text-[11px] font-semibold text-slate-400 font-mono uppercase tracking-wider block">
          Suggested Research Questions:
        </span>
        <div className="flex flex-wrap gap-2">
          {sampleQueries.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              disabled={loading}
              className="px-3.5 py-1.5 rounded-xl bg-navy-900/90 hover:bg-navy-850 text-slate-300 hover:text-white border border-navy-750 text-xs font-medium transition-all text-left flex items-center gap-2 cursor-pointer shadow-sm"
            >
              <Sparkles className="w-3 h-3 text-cyan-400 shrink-0" />
              <span>{q}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Feed */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-5 min-h-[460px] flex flex-col justify-between space-y-4 shadow-sm">
        <div className="space-y-5 overflow-y-auto max-h-[550px] pr-2">
          {messages.map((m, idx) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={idx}
                className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-sm">
                    <BotMessageSquare className="w-4 h-4" />
                  </div>
                )}

                <div className={`space-y-3 max-w-2xl ${isUser ? 'items-end' : 'items-start'}`}>
                  {/* Message Bubble */}
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed whitespace-pre-wrap ${
                      isUser
                        ? 'bg-blue-600 text-white font-medium shadow-md shadow-blue-600/20'
                        : 'bg-navy-950/90 text-slate-200 border border-navy-800'
                    }`}
                  >
                    {m.content}
                  </div>

                  {/* Supporting News Citations */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold block">
                        Referenced News Citations ({m.citations.length} Verified Sources)
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {m.citations.map((c, i) => (
                          <div
                            key={i}
                            className="p-3 bg-navy-950 border border-navy-800 rounded-xl space-y-2 text-xs"
                          >
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="font-bold text-white font-mono">{c.company}</span>
                              <SentimentBadge sentiment={c.sentiment} confidence={c.confidence} size="xs" />
                            </div>
                            <h5 className="text-[11px] font-medium text-slate-200 line-clamp-2 leading-snug">
                              "{c.title}"
                            </h5>
                            <div className="pt-1.5 border-t border-navy-850 flex items-center justify-between text-[10px] text-slate-500">
                              <span>{c.source}</span>
                              {c.url && (
                                <a
                                  href={c.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium"
                                >
                                  <span>View Source</span>
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className={`text-[10px] text-slate-500 font-mono ${isUser ? 'text-right' : 'text-left'}`}>
                    {m.timestamp}
                  </div>
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-navy-800 border border-navy-700 flex items-center justify-center text-slate-300 shrink-0 mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex gap-3.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white shrink-0 mt-1 animate-pulse">
                <BotMessageSquare className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-navy-950/90 border border-navy-800 text-xs text-slate-400 flex items-center gap-3">
                <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
                <span>Synthesizing intelligence across indexed articles & FinBERT scores...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="pt-3 border-t border-navy-800 flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask a question about financial headlines, tone, or narrative divergence..."
            className="flex-1 bg-navy-950 border border-navy-700/80 rounded-xl px-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg shadow-blue-600/20 transition-all cursor-pointer shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send</span>
          </button>
        </form>
      </div>

      {/* Financial Disclaimer */}
      <div className="p-4 bg-navy-900/60 border border-navy-800 rounded-xl text-xs text-slate-400 flex items-center gap-3">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
        <p className="text-[11px] leading-relaxed">
          Assistant responses are grounded strictly in semantic tone analysis of retrieved financial news and FinBERT classifications.
          This does not constitute investment advice, financial forecasting, or portfolio recommendations.
        </p>
      </div>
    </div>
  );
};
