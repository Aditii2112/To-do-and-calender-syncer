import type { QueryEvent } from '../api/client';

interface QueryResultsViewProps {
  events: QueryEvent[];
  query: string;
}

function formatEventDate(start: string): string {
  const d = new Date(start);
  const date = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  const time = start.includes('T')
    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';
  return time ? `${date} at ${time}` : date;
}

export function QueryResultsView({ events, query }: QueryResultsViewProps) {
  if (!events.length) return null;

  return (
    <div className="mt-3 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="text-sm font-semibold text-gray-800 mb-2">
        🔍 Results for "{query}"
      </div>
      <ul className="space-y-2">
        {events.map((e, i) => (
          <li key={i} className="flex flex-col gap-0.5 px-3 py-2 rounded-lg bg-gray-50 border border-gray-100">
            <span className="font-medium text-sm text-gray-800">{e.summary || '(No title)'}</span>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{formatEventDate(e.start)}</span>
              <span className="text-gray-300">•</span>
              <span className={e.account === 'work' ? 'text-indigo-600' : 'text-pink-600'}>
                {e.account === 'work' ? '💼' : '🏠'} {e.account}
              </span>
              {e.attendees && e.attendees.length > 0 && (
                <>
                  <span className="text-gray-300">•</span>
                  <span>
                    👥 {e.attendees.map(a => a.displayName || a.email).join(', ')}
                  </span>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
