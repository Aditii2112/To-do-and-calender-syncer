import { useEffect, useRef, useState } from 'react';
import { chat, fetchBookingSlots, type ChatResponse } from '../api/client';
import { AgendaView } from './AgendaView';
import { BookingPanel } from './BookingPanel';
import { FloatingTaskCard } from './FloatingTaskCard';
import { MessageBubble } from './MessageBubble';
import { QueryResultsView } from './QueryResultsView';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

interface ChatPaneProps {
  onResponse?: (res: ChatResponse) => void;
  onBookedSuccess?: (date: string, title?: string) => void;
}

const QUICK_ACTIONS = [
  { label: '📅 My day', prompt: "What does my day look like?" },
  { label: '📆 This week', prompt: "Summarize my week" },
  { label: '🕐 Schedule', prompt: "When can I schedule gym tomorrow?" },
  { label: '🔍 Search', prompt: "When did I last meet Prof Lee?" },
];

export function ChatPane({ onResponse, onBookedSuccess }: ChatPaneProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    setInput('');
    setError(null);
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await chat(text);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: res.final_decision, response: res },
      ]);
      onResponse?.(res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      setError(msg);
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
  };

  const updateMessageResponse = (index: number, updated: ChatResponse) => {
    setMessages(prev =>
      prev.map((msg, i) =>
        i === index && msg.role === 'assistant'
          ? { ...msg, content: updated.final_decision, response: updated }
          : msg
      )
    );
    onResponse?.(updated);
  };

  const handleChooseFloating = (index: number, res: ChatResponse) => {
    const updated: ChatResponse = {
      ...res,
      needs_floating_vs_fixed_choice: false,
      final_decision: 'Added as floating task. It will appear in your calendar list.',
      parsed_task: { ...res.parsed_task, category: 'floating' },
    };
    updateMessageResponse(index, updated);
  };

  const handleChooseAssignTime = async (index: number, res: ChatResponse) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBookingSlots(res.parsed_task);
      const updated: ChatResponse = {
        ...res,
        needs_booking_ui: true,
        needs_floating_vs_fixed_choice: false,
        parsed_task: { ...res.parsed_task, category: 'fixed' },
        suggested_slots: data.suggested_slots || [],
      };
      updateMessageResponse(index, updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load slots');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl border border-gray-100 shadow-sm h-full flex flex-col overflow-hidden">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <span className="text-4xl mb-3">🌴</span>
            <h2 className="text-lg font-bold text-oasis-800 mb-1">Welcome to Oasis OS</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-sm">
              Your AI calendar assistant. Ask about your schedule, find free time, or search for past events.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.label}
                  onClick={() => send(qa.prompt)}
                  className="px-3 py-1.5 text-xs font-medium text-oasis-700 bg-oasis-50 border border-oasis-200 rounded-full hover:bg-oasis-100 transition-colors cursor-pointer"
                >
                  {qa.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i}>
            <MessageBubble role={m.role} content={m.content} />
            {m.role === 'assistant' && m.response && (
              <>
                {m.response.parsed_task.intent === 'summarize' && m.response.existing_events && (
                  <AgendaView
                    work={m.response.existing_events.work || []}
                    personal={m.response.existing_events.personal || []}
                    date={m.response.parsed_task.date}
                    horizon={m.response.summary_horizon || m.response.parsed_task.summary_horizon}
                  />
                )}
                {m.response.parsed_task.intent === 'query' &&
                  m.response.query_events &&
                  m.response.query_events.length > 0 && (
                    <QueryResultsView
                      events={m.response.query_events}
                      query={m.response.parsed_task.title}
                    />
                  )}
                {m.response.needs_floating_vs_fixed_choice && (
                  <div className="mt-2 p-3 rounded-xl bg-oasis-50 border border-oasis-200">
                    <p className="text-xs text-gray-600 mb-2">
                      <span className="font-medium text-oasis-800">{m.response.parsed_task.title}</span>
                      {m.response.parsed_task.date && (
                        <span className="text-gray-500"> · {m.response.parsed_task.date}</span>
                      )}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleChooseFloating(i, m.response!)}
                        className="px-3 py-1.5 text-xs font-medium text-oasis-700 bg-white border border-oasis-200 rounded-lg hover:bg-oasis-100 transition-colors"
                      >
                        🔄 Floating (no set time)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleChooseAssignTime(i, m.response!)}
                        disabled={loading}
                        className="px-3 py-1.5 text-xs font-medium text-white bg-oasis-600 rounded-lg hover:bg-oasis-700 disabled:opacity-50 transition-colors"
                      >
                        📌 Assign a time
                      </button>
                    </div>
                  </div>
                )}
                {m.response.needs_booking_ui && (
                  <BookingPanel
                    parsedTask={m.response.parsed_task}
                    suggestedSlots={m.response.suggested_slots || []}
                    onBooked={(_, details) =>
                      details && onBookedSuccess?.(details.date, details.title, details.startTime, details.endTime, details.accountId)
                    }
                  />
                )}
                {m.response.parsed_task.intent === 'create' &&
                  m.response.parsed_task.category === 'floating' &&
                  !m.response.needs_booking_ui &&
                  !m.response.needs_floating_vs_fixed_choice && (
                    <FloatingTaskCard
                      parsedTask={m.response.parsed_task}
                      suggestedSlots={m.response.suggested_slots || []}
                    />
                  )}
              </>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span className="inline-flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-oasis-400 animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-oasis-400 animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-oasis-400 animate-bounce [animation-delay:300ms]" />
            </span>
            Thinking…
          </div>
        )}
        {error && (
          <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
        )}
        <div ref={endRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-gray-100 shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your calendar…"
            disabled={loading}
            className="flex-1 px-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:border-oasis-400 focus:ring-2 focus:ring-oasis-200 outline-none transition-all disabled:opacity-50 bg-white"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-2.5 text-sm font-semibold text-white bg-oasis-600 rounded-xl hover:bg-oasis-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 cursor-pointer"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
