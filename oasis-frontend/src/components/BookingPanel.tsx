import { useState } from 'react';
import type { ParsedTask } from '../api/client';
import type { BookPayload, BookResponse } from '../api/client';
import { SuggestedSlotsList } from './SuggestedSlotsList';
import { book } from '../api/client';
import './BookingPanel.css';

interface BookingPanelProps {
  parsedTask: ParsedTask;
  suggestedSlots?: { start_time: string; end_time: string; account_suggestions?: string[] }[];
  onBooked?: (result: BookResponse) => void;
}

export function BookingPanel({ parsedTask, suggestedSlots = [], onBooked }: BookingPanelProps) {
  const [startTime, setStartTime] = useState('10:00');
  const [endTime, setEndTime] = useState('11:00');
  const [accountId, setAccountId] = useState<string>(parsedTask.account_id || 'personal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BookResponse | null>(null);

  const isValidTimeRange = () => {
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    const startMin = sh * 60 + sm;
    const endMin = eh * 60 + em;
    return endMin > startMin;
  };

  const canConfirm = accountId && isValidTimeRange();

  const handleSlotSelect = (start: string, end: string) => {
    setStartTime(start);
    setEndTime(end);
  };

  const handleConfirm = async () => {
    if (!canConfirm) return;
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
      onBooked?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Booking failed');
    } finally {
      setLoading(false);
    }
  };

  if (result?.ok) {
    return (
      <div className="booking-panel booking-panel--success">
        <div className="booking-panel__success">✅ {result.message}</div>
        {result.event_link && (
          <a href={result.event_link} target="_blank" rel="noopener noreferrer" className="booking-panel__link">
            Open in Google Calendar
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="booking-panel">
      <div className="booking-panel__header">📅 Confirm booking</div>

      <SuggestedSlotsList
        slots={suggestedSlots}
        onSelect={handleSlotSelect}
      />

      <div className="booking-panel__fields">
        <div className="booking-panel__field">
          <label>Start time</label>
          <input
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            min="09:00"
            max="19:00"
          />
        </div>
        <div className="booking-panel__field">
          <label>End time</label>
          <input
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            min="09:00"
            max="19:00"
          />
        </div>
        <div className="booking-panel__field">
          <label>Account</label>
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="work">Work</option>
            <option value="personal">Personal</option>
          </select>
        </div>
      </div>

      {!isValidTimeRange() && (
        <div className="booking-panel__validation">End time must be after start time.</div>
      )}

      {error && <div className="booking-panel__error">{error}</div>}

      <button
        className="booking-panel__btn"
        onClick={handleConfirm}
        disabled={!canConfirm || loading}
      >
        {loading ? 'Booking…' : 'Add to calendar'}
      </button>
    </div>
  );
}
