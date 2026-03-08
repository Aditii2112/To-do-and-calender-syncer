export interface SuggestedSlot {
  start_time: string;
  end_time: string;
  account_suggestions?: string[];
}

interface SuggestedSlotsListProps {
  slots: SuggestedSlot[];
  onSelect: (startTime: string, endTime: string) => void;
}

function to12h(t: string): string {
  const [h, m] = t.split(':').map(Number);
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
}

export function SuggestedSlotsList({ slots, onSelect }: SuggestedSlotsListProps) {
  if (!slots.length) return null;

  return (
    <div className="mb-3">
      <div className="text-xs font-semibold text-emerald-700 mb-2 flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        Suggested times
      </div>
      <div className="flex flex-wrap gap-2">
        {slots.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(s.start_time, s.end_time)}
            className="px-3 py-1.5 text-xs font-medium border border-emerald-300 text-emerald-700 bg-emerald-50 rounded-full hover:bg-emerald-600 hover:text-white hover:border-emerald-600 transition-colors cursor-pointer"
          >
            {to12h(s.start_time)} – {to12h(s.end_time)}
          </button>
        ))}
      </div>
    </div>
  );
}
