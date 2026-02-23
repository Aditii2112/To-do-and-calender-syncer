import type { QueryEvent } from '../api/client';
import './QueryResultsView.css';

interface QueryResultsViewProps {
  events: QueryEvent[];
  query: string;
}

function formatEventDate(start: string): string {
  const d = new Date(start);
  const date = d.toLocaleDateString();
  const time = start.includes('T') ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
  return time ? `${date} at ${time}` : date;
}

export function QueryResultsView({ events, query }: QueryResultsViewProps) {
  if (!events.length) return null;

  return (
    <div className="query-results">
      <div className="query-results__header">Results for “{query}”</div>
      <ul className="query-results__list">
        {events.map((e, i) => (
          <li key={i} className="query-result-item">
            <span className="query-result-item__summary">{e.summary || '(No title)'}</span>
            <span className="query-result-item__meta">
              {formatEventDate(e.start)} • {e.account}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
