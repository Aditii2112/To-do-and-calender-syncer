import { useState } from 'react';
import type { BookPayload, BookResponse, ParsedTask } from '../api/client';
import { book } from '../api/client';
import { SuggestedSlotsList } from './SuggestedSlotsList';

function addHour(time: string): string {
  const [h, m] = time.split(':').map(Number);
  const nh = Math.min(h + 1, 23);
  return `${nh.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

export interface BookedDetails {
  date: string;
  title: string;
  startTime: string;
  endTime: string;
  accountId: string;
}

interface BookingPanelProps {
  parsedTask: ParsedTask;
  suggestedSlots?: { start_time: string; end_time: string; account_suggestions?: string[] }[];
  onBooked?: (result: BookResponse, details?: BookedDetails) => void;
}

export function BookingPanel({ parsedTask, suggestedSlots = [], onBooked }: BookingPanelProps) {
  const [startTime, setStartTime] = useState(parsedTask.start_time || '10:00');
  const [endTime, setEndTime] = useState(parsedTask.end_time || addHour(parsedTask.start_time || '10:00'));
  const [accountId, setAccountId] = useState(parsedTask.account_id || 'personal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BookResponse | null>(null);

  const isValid = () => {
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    return eh * 60 + em > sh * 60 + sm;
  };

  const handleSlotSelect = (start: string, end: string) => {
    setStartTime(start);
    setEndTime(end);
  };

  const handleConfirm = async () => {
    if (!isValid()) return;
    setError(null);
    setLoading(true);
    try {
      const payload: BookPayload = {
        title: parsedTask.title,
        date: parsedTask.date,
        start_time: startTime,
        end_time: endTime,
        account_id: accountId,
        category: parsedTask.category,
      };
      const res = await book(payload);
      setResult(res);
      onBooked?.(res, {
        date: parsedTask.date,
        title: parsedTask.title,
        startTime,
        endTime,
        accountId,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Booking failed');
    } finally {
      setLoading(false);
    }
  };

  if (result?.ok) {
    return (
      <div className="mt-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
        <p className="text-emerald-800 font-medium text-sm">✅ {result.message}</p>
        {result.event_link && (
          <a
            href={result.event_link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 hover:underline text-xs mt-1 inline-block"
          >
            Open in Google Calendar →
          </a>
        )}
      </div>
    );
  }

  const categoryBadge =
    parsedTask.category === 'floating' ? (
      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-floating-light text-amber-700">
        🔄 FLOATING
      </span>
    ) : (
      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-fixed-light text-indigo-700">
        📌 FIXED
      </span>
    );

  return (
    <div className="mt-3 p-4 bg-white border border-gray-100 rounded-xl shadow-sm">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-semibold text-sm text-gray-800">📅 Confirm booking</span>
        {categoryBadge}
      </div>
      <p className="text-[11px] text-gray-400 mb-3">
        {parsedTask.category === 'floating'
          ? 'This is a floating task — it goes to your calendar only once you pick a time and confirm.'
          : 'Review the time below and confirm to add this to your Google Calendar.'}
      </p>

      <SuggestedSlotsList slots={suggestedSlots} onSelect={handleSlotSelect} />

      <div className="grid grid-cols-3 gap-3 mb-3">
        <label className="block">
          <span className="text-xs text-gray-500">Start</span>
          <input
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            className="mt-0.5 block w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm focus:border-oasis-400 focus:ring-1 focus:ring-oasis-300 outline-none"
          />
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">End</span>
          <input
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            className="mt-0.5 block w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm focus:border-oasis-400 focus:ring-1 focus:ring-oasis-300 outline-none"
          />
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">Account</span>
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="mt-0.5 block w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm focus:border-oasis-400 focus:ring-1 focus:ring-oasis-300 outline-none bg-white"
          >
            <option value="work">💼 Work</option>
            <option value="personal">🏠 Personal</option>
          </select>
        </label>
      </div>

      {!isValid() && (
        <p className="text-xs text-amber-600 mb-2">End time must be after start time.</p>
      )}
      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      <button
        onClick={handleConfirm}
        disabled={!isValid() || loading}
        className="w-full py-2 px-4 rounded-xl text-sm font-semibold text-white bg-oasis-600 hover:bg-oasis-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
      >
        {loading ? 'Booking…' : 'Add to calendar'}
      </button>
    </div>
  );
}
