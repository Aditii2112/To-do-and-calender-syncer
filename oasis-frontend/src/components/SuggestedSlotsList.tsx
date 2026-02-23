import './SuggestedSlotsList.css';

export interface SuggestedSlot {
  start_time: string;
  end_time: string;
  account_suggestions?: string[];
}

interface SuggestedSlotsListProps {
  slots: SuggestedSlot[];
  onSelect: (startTime: string, endTime: string) => void;
}

function formatSlot(start: string, end: string): string {
  const to12h = (t: string) => {
    const [h, m] = t.split(':').map(Number);
    const period = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 || 12;
    return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
  };
  return `${to12h(start)} – ${to12h(end)}`;
}

export function SuggestedSlotsList({ slots, onSelect }: SuggestedSlotsListProps) {
  if (!slots.length) return null;

  return (
    <div className="suggested-slots">
      <div className="suggested-slots__title">🟢 Suggested times</div>
      <ul className="suggested-slots__list">
        {slots.map((s, i) => (
          <li key={i}>
            <button
              type="button"
              className="suggested-slots__btn"
              onClick={() => onSelect(s.start_time, s.end_time)}
            >
              {formatSlot(s.start_time, s.end_time)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
