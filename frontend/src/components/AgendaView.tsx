import type { CalendarEvent } from '../api/client';

interface AgendaViewProps {
  work: CalendarEvent[];
  personal: CalendarEvent[];
  date: string;
  horizon?: string;
}

function formatTime(s: string): string {
  if (!s) return 'All day';
  const match = s.match(/T(\d{2}):(\d{2})/);
  if (!match) return s;
  const h = parseInt(match[1], 10);
  const m = match[2];
  const period = h >= 12 ? 'PM' : 'AM';
  return `${h % 12 || 12}:${m} ${period}`;
}

const HORIZON_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  daily: { emoji: '📅', label: 'Daily Agenda', color: 'text-indigo-700 bg-indigo-50 border-indigo-200' },
  weekly: { emoji: '📆', label: 'Weekly Summary', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  monthly: { emoji: '🗓️', label: 'Monthly Overview', color: 'text-amber-700 bg-amber-50 border-amber-200' },
  yearly: { emoji: '📊', label: 'Yearly Report', color: 'text-purple-700 bg-purple-50 border-purple-200' },
};

function EventList({ events, title, icon }: { events: CalendarEvent[]; title: string; icon: string }) {
  if (!events.length) return null;
  return (
    <div className="mb-3 last:mb-0">
      <h4 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-1.5">
        {icon} {title}
      </h4>
      <ul className="space-y-1">
        {events.map((e, i) => {
          const isFixed = e.category === 'fixed';
          return (
            <li
              key={i}
              className={`flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm ${
                isFixed ? 'bg-fixed-light border-l-2 border-l-fixed' : 'bg-floating-light border-l-2 border-l-floating'
              }`}
            >
              <span className="text-xs text-gray-500 w-16 shrink-0">{formatTime(e.start)}</span>
              <span className="font-medium text-gray-800 truncate">{e.summary || '(No title)'}</span>
              <span className="ml-auto text-[10px] opacity-70">{isFixed ? '📌' : '🔄'}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function AgendaView({ work, personal, date, horizon = 'daily' }: AgendaViewProps) {
  const hasEvents = work.length > 0 || personal.length > 0;
  if (!hasEvents) return null;

  const cfg = HORIZON_CONFIG[horizon] || HORIZON_CONFIG.daily;

  return (
    <div className={`mt-3 p-4 rounded-xl border ${cfg.color}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">{cfg.emoji}</span>
        <span className="font-semibold text-sm">{cfg.label}</span>
        <span className="text-xs opacity-70 ml-auto">{date}</span>
      </div>
      <EventList events={work} title="Work" icon="💼" />
      <EventList events={personal} title="Personal" icon="🏠" />
    </div>
  );
}
