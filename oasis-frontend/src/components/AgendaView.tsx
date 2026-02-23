import type { CalendarEvent } from '../api/client';
import './AgendaView.css';

interface AgendaViewProps {
  work: CalendarEvent[];
  personal: CalendarEvent[];
  date: string;
}

function formatTime(s: string): string {
  if (!s) return 'All day';
  const match = s.match(/T(\d{2}):(\d{2})/);
  if (!match) return s;
  const h = parseInt(match[1], 10);
  const m = match[2];
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${m} ${period}`;
}

function EventList({ events, title }: { events: CalendarEvent[]; title: string }) {
  if (!events.length) return null;
  return (
    <section className="agenda-section">
      <div className="agenda-section__title">{title} account</div>
      <ul className="agenda-section__list">
        {events.map((e, i) => (
          <li key={i} className="agenda-event">
            <span className="agenda-event__time">{formatTime(e.start)}</span>
            <span className="agenda-event__summary">{e.summary || '(No title)'}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function AgendaView({ work, personal, date }: AgendaViewProps) {
  const hasEvents = work.length > 0 || personal.length > 0;
  if (!hasEvents) return null;

  return (
    <div className="agenda-view">
      <div className="agenda-view__header">📅 Agenda for {date}</div>
      <EventList events={work} title="Work" />
      <EventList events={personal} title="Personal" />
    </div>
  );
}
