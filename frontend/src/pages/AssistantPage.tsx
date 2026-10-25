import React, { useState } from 'react';
import {
  BotMessageSquare,
  Send,
  Sparkles,
  ExternalLink,
  AlertTriangle,
  RefreshCw,
  HelpCircle,
  FileText
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
        'Hello! I am your AI Financial News Assistant. I answer questions grounded strictly in currently verified news articles and local FinBERT sentiment classifications. Ask me about sentiment trends for Nvidia, Apple, Tesla, or any tracked company.',
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
          content: 'An error occurred while contacting the financial intelligence service. Please try again.',
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sampleQueries = [
    'What is the current news sentiment on Nvidia?',
    'Why is Tesla experiencing sentiment conflict?',
    'Compare sentiment between Apple and Microsoft',
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <BotMessageSquare className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-bold text-white">AI Financial News Assistant</h2>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono text-[10px] border border-blue-500/20">
            Grounded Retrieval RAG
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Inquires are synthesized using strictly verified news articles and stored FinBERT tone classifications.
        </p>
      </div>

      {/* Chat Messages Container */}
      <div className="bg-navy-900 border border-navy-750 rounded-xl p-5 min-h-[460px] flex flex-col justify-between space-y-4">
        <div className="space-y-4 overflow-y-auto max-h-[500px] pr-1">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} space-y-2`}
            >
              <div
                className={`max-w-[85%] rounded-xl p-4 text-xs leading-relaxed space-y-3 ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-navy-950 border border-navy-850 text-slate-200'
                }`}
              >
                <div className="whitespace-pre-line">{m.content}</div>

                {/* Grounded Article Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="pt-2 border-t border-navy-800 space-y-2">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                      Grounded Article References:
                    </span>
                    <div className="space-y-1.5">
                      {m.citations.map((c, i) => (
                        <div
                          key={i}
                          className="p-2 bg-navy-900/80 rounded border border-navy-800 flex items-center justify-between text-[11px]"
                        >
                          <div className="truncate pr-2">
                            <span className="text-blue-300 font-semibold mr-1.5">[{c.company}]</span>
                            <span className="text-slate-300">"{c.title}"</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <SentimentBadge sentiment={c.sentiment} confidence={c.confidence} />
                            <a
                              href={c.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-slate-400 hover:text-white"
                            >
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Disclaimer */}
                {m.disclaimer && (
                  <p className="text-[10px] text-amber-300/80 italic pt-1 border-t border-navy-800/60">
                    {m.disclaimer}
                  </p>
                )}
              </div>

              <span className="text-[10px] text-slate-500 font-mono px-1">
                {m.timestamp}
              </span>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 p-3 text-xs text-slate-400">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400" />
              <span>Grounded intelligence lookup in progress...</span>
            </div>
          )}
        </div>

        {/* Suggested Queries */}
        <div className="pt-2 border-t border-navy-800 space-y-2">
          <div className="flex flex-wrap gap-2">
            <span className="text-[10px] text-slate-500 self-center">Try:</span>
            {sampleQueries.map((q, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSend(q)}
                className="px-2.5 py-1 rounded bg-navy-950 hover:bg-navy-800 text-[11px] text-slate-300 border border-navy-800 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input field */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about company sentiment, conflicts, or news tone..."
              className="flex-1 bg-navy-950 border border-navy-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
