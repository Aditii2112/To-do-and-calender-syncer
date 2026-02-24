import { useState, useRef, useEffect } from 'react';
import { chat, type ChatResponse } from '../api/client';
import { MessageBubble } from './MessageBubble';
import { BookingPanel } from './BookingPanel';
import { AgendaView } from './AgendaView';
import { QueryResultsView } from './QueryResultsView';
import './ChatPane.css';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

export function ChatPane() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setError(null);
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await chat(text);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.final_decision,
          response: res,
        },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-pane">
      <div className="chat-pane__messages">
        {messages.length === 0 && (
          <div className="chat-pane__empty">
            Ask about your calendar: “What’s my day look like?”, “When can I schedule gym tomorrow?”, “When did I last do laundry?”
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className="chat-pane__message-wrap">
            <MessageBubble role={m.role} content={m.content} />
            {m.role === 'assistant' && m.response && (
              <>
                {m.response.parsed_task.intent === 'summarize' && m.response.existing_events && (
                  <AgendaView
                    work={m.response.existing_events.work || []}
                    personal={m.response.existing_events.personal || []}
                    date={m.response.parsed_task.date}
                  />
                )}
                {m.response.parsed_task.intent === 'query' && m.response.query_events && m.response.query_events.length > 0 && (
                  <QueryResultsView
                    events={m.response.query_events}
                    query={m.response.parsed_task.title}
                  />
                )}
                {m.response.needs_booking_ui && (
                  <BookingPanel
                    parsedTask={m.response.parsed_task}
                    suggestedSlots={m.response.suggested_slots || []}
                  />
                )}
              </>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-pane__loading">🧠 Processing…</div>
        )}
        {error && (
          <div className="chat-pane__error">{error}</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-pane__form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-pane__input"
          placeholder="Ask about your calendar…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="chat-pane__send" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
