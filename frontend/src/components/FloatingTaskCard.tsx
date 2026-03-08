import type { ParsedTask, SuggestedSlot } from '../api/client';

interface FloatingTaskCardProps {
  parsedTask: ParsedTask;
  suggestedSlots?: SuggestedSlot[];
}

function to12h(t: string): string {
  const [h, m] = t.split(':').map(Number);
  const period = h >= 12 ? 'PM' : 'AM';
  return `${(h % 12 || 12)}:${m.toString().padStart(2, '0')} ${period}`;
}

export function FloatingTaskCard({ parsedTask, suggestedSlots = [] }: FloatingTaskCardProps) {
  return (
    <div className="mt-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">🔄</span>
        <span className="font-semibold text-sm text-amber-900">{parsedTask.title}</span>
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 ml-auto">
          FLOATING
        </span>
      </div>

      <div className="text-xs text-amber-800 mb-2">
        📅 {parsedTask.date}
        {parsedTask.account_id && (
          <span className="ml-2">
            {parsedTask.account_id === 'work' ? '💼' : '🏠'} {parsedTask.account_id}
          </span>
        )}
      </div>

      {suggestedSlots.length > 0 && (
        <div className="mb-2">
          <p className="text-[11px] text-amber-700 font-medium mb-1">Good times to do this:</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestedSlots.map((s, i) => (
              <span
                key={i}
                className="px-2 py-1 text-[11px] font-medium bg-white border border-amber-200 text-amber-800 rounded-full"
              >
                {to12h(s.start_time)} – {to12h(s.end_time)}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-[11px] text-amber-600 italic">
        This task stays in your UI as a reminder — it won't be added to Google Calendar.
      </p>
    </div>
  );
}
