import { useRef, useState, useCallback, useEffect } from 'react';
import type { CalendarEvent, ChatResponse } from '../api/client';

export interface FloatingTask {
  title: string;
  date: string;
  account: string;
  y: number;
}

type ViewMode = 'daily' | 'monthly' | 'yearly';

interface CalendarViewProps {
  response: ChatResponse | null;
  floatingTasks: FloatingTask[];
  selectedDate: string;
  loadingDay: boolean;
  onFetchDay: (date: string) => void;
  onDeleteEvent?: (accountId: string, eventId: string) => void;
  onRemoveFloatingTask?: (title: string, date: string) => void;
}

function formatTime(iso: string): string {
  if (!iso || !iso.includes('T')) return '';
  const match = iso.match(/T(\d{2}):(\d{2})/);
  if (!match) return '';
  const h = parseInt(match[1], 10);
  const m = match[2];
  return `${h % 12 || 12}:${m} ${h >= 12 ? 'PM' : 'AM'}`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
}

function FixedEventCard({
  event,
  onCancel,
}: {
  event: CalendarEvent;
  onCancel?: (accountId: string, eventId: string) => void;
}) {
  const isWork = event.account === 'work';
  const canCancel = event.id && onCancel;
  return (
    <div className="group/card border-l-[3px] border-l-indigo-500 bg-indigo-50/60 rounded-r-lg px-3 py-2 mb-1.5 min-h-[52px] flex flex-col justify-center">
      <div className="flex items-center gap-2 min-h-0">
        <span className="text-[10px] opacity-60 shrink-0">📌</span>
        <span
          className="text-xs font-semibold text-gray-800 truncate min-w-0 flex-1"
          title={event.summary || undefined}
        >
          {event.summary || '(No title)'}
        </span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0 ${
          isWork ? 'bg-indigo-100 text-indigo-700' : 'bg-pink-100 text-pink-700'
        }`}>
          {isWork ? '💼' : '🏠'}
        </span>
        {canCancel && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onCancel(event.account, event.id!); }}
            className="shrink-0 w-6 h-6 min-w-[24px] flex items-center justify-center rounded text-gray-400 hover:text-red-600 hover:bg-red-50 text-sm leading-none"
            title="Cancel event"
          >
            ×
          </button>
        )}
      </div>
      <div className="text-[11px] text-gray-500 mt-0.5">
        {formatTime(event.start)}
        {event.end ? ` – ${formatTime(event.end)}` : ''}
      </div>
      {event.attendees && event.attendees.length > 0 && (
        <div className="text-[10px] text-gray-400 mt-0.5 truncate">
          👥 {event.attendees.filter(a => !a.email.includes('self')).map(a => a.displayName || a.email).slice(0, 3).join(', ')}
        </div>
      )}
    </div>
  );
}

function DraggableFloating({ task, onDragEnd }: { task: FloatingTask; onDragEnd: (key: string, y: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [offsetY, setOffsetY] = useState(0);
  const [currentY, setCurrentY] = useState(task.y);
  const key = `${task.title}:${task.date}`;

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (!ref.current) return;
    setDragging(true);
    setOffsetY(e.clientY - ref.current.getBoundingClientRect().top);
    ref.current.setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging || !ref.current) return;
    const parent = ref.current.parentElement;
    if (!parent) return;
    const parentRect = parent.getBoundingClientRect();
    const newY = Math.max(0, Math.min(e.clientY - parentRect.top - offsetY, parentRect.height - 48));
    setCurrentY(newY);
  }, [dragging, offsetY]);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    setDragging(false);
    if (ref.current) ref.current.releasePointerCapture(e.pointerId);
    onDragEnd(key, currentY);
  }, [currentY, key, onDragEnd]);

  const isWork = task.account === 'work';

  return (
    <div
      ref={ref}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      style={{ transform: `translateY(${currentY}px)` }}
      className={`absolute right-0 w-[100px] border-l-[3px] border-l-amber-400 rounded-lg px-2 py-1.5 cursor-grab active:cursor-grabbing select-none transition-shadow ${
        dragging ? 'shadow-lg z-20 bg-amber-100 opacity-90' : 'shadow-sm bg-amber-50/90 hover:shadow-md'
      }`}
    >
      <div className="flex items-center gap-1">
        <span className="text-[9px]">🔄</span>
        <span className="text-[10px] font-semibold text-amber-900 truncate">{task.title}</span>
      </div>
      <div className="text-[9px] text-amber-700 mt-0.5 flex items-center gap-1">
        <span>{isWork ? '💼' : '🏠'}</span>
        <span className="text-amber-500">drag</span>
      </div>
    </div>
  );
}

const SLOT_START_HOUR = 7;
const SLOT_END_HOUR = 20;

const TIME_SLOTS = Array.from({ length: SLOT_END_HOUR - SLOT_START_HOUR + 1 }, (_, idx) => {
  const hour = SLOT_START_HOUR + idx;
  const period = hour >= 12 ? 'PM' : 'AM';
  const h12 = hour % 12 || 12;
  return `${h12} ${period}`;
});

function getHour(iso: string): number {
  const match = iso.match(/T(\d{2})/);
  return match ? parseInt(match[1], 10) : -1;
}

// --- Month grid helpers ---
function getMonthDays(year: number, month: number): (number | null)[][] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startPad = first.getDay();
  const daysInMonth = last.getDate();
  const total = startPad + daysInMonth;
  const rows: (number | null)[][] = [];
  let row: (number | null)[] = [];
  for (let i = 0; i < startPad; i++) row.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    row.push(d);
    if (row.length === 7) {
      rows.push(row);
      row = [];
    }
  }
  if (row.length) {
    while (row.length < 7) row.push(null);
    rows.push(row);
  }
  return rows;
}

function dateKey(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export function CalendarView({
  response,
  floatingTasks,
  selectedDate,
  loadingDay,
  onFetchDay,
  onDeleteEvent,
  onRemoveFloatingTask,
}: CalendarViewProps) {
  const [taskPositions, setTaskPositions] = useState<Record<string, number>>({});
  const [viewMode, setViewMode] = useState<ViewMode>('daily');
  const [gridMonth, setGridMonth] = useState(() => {
    const [y, m] = selectedDate.split('-').map(Number);
    return { year: y, month: (m || 1) - 1 };
  });
  useEffect(() => {
    const [y, m] = selectedDate.split('-').map(Number);
    if (y && m) setGridMonth({ year: y, month: m - 1 });
  }, [selectedDate]);

  const events = response?.existing_events;
  const responseDate = response?.parsed_task?.date;
  const fixedEvents: CalendarEvent[] = (
    responseDate === selectedDate
      ? [...(events?.work || []), ...(events?.personal || [])]
      : []
  ).filter(e => e.category !== 'floating').sort((a, b) => a.start.localeCompare(b.start));

  const floatingForDay = floatingTasks.filter(t => t.date === selectedDate);
  const hasFixed = fixedEvents.length > 0;
  const hasFloating = floatingForDay.length > 0;
  const isEmpty = !hasFixed && !hasFloating && !loadingDay;

  const handleDragEnd = useCallback((key: string, y: number) => {
    setTaskPositions(prev => ({ ...prev, [key]: y }));
  }, []);

  const handleDayClick = useCallback((date: string) => {
    onFetchDay(date);
    setViewMode('daily');
  }, [onFetchDay]);

  const monthDays = getMonthDays(gridMonth.year, gridMonth.month);
  const prevMonth = () => setGridMonth(prev => (prev.month === 0 ? { year: prev.year - 1, month: 11 } : { year: prev.year, month: prev.month - 1 }));
  const nextMonth = () => setGridMonth(prev => (prev.month === 11 ? { year: prev.year + 1, month: 0 } : { year: prev.year, month: prev.month + 1 }));

  const [selY, selM, selD] = selectedDate.split('-').map(Number);
  const isSelected = (d: number | null) => d !== null && gridMonth.year === selY && gridMonth.month === selM - 1 && selD === d;
  const isToday = (d: number | null) => {
    if (d === null) return false;
    const t = new Date();
    return gridMonth.year === t.getFullYear() && gridMonth.month === t.getMonth() && d === t.getDate();
  };

  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl border border-gray-100 shadow-sm h-full flex flex-col overflow-hidden">
      {/* Header + view tabs */}
      <div className="px-3 py-2 border-b border-gray-100 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold text-gray-800">Calendar</h2>
          <div className="flex rounded-lg bg-gray-100 p-0.5">
            {(['daily', 'monthly', 'yearly'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
                className={`px-2.5 py-1 text-[10px] font-medium rounded-md transition-colors ${
                  viewMode === mode ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {mode === 'daily' ? '📅 Daily' : mode === 'monthly' ? '🗓️ Month' : '📊 Year'}
              </button>
            ))}
          </div>
        </div>
        {selectedDate && <p className="text-[11px] text-gray-500">{formatDate(selectedDate)}</p>}
      </div>

      {/* Month grid */}
      {(viewMode === 'monthly' || viewMode === 'yearly') && (
        <div className="px-3 py-2 border-b border-gray-50 shrink-0">
          <div className="flex items-center justify-between mb-1.5">
            <button type="button" onClick={prevMonth} className="p-1 rounded hover:bg-gray-100 text-gray-600 text-xs font-medium">
              ‹
            </button>
            <span className="text-xs font-semibold text-gray-700">
              {new Date(gridMonth.year, gridMonth.month).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
            </span>
            <button type="button" onClick={nextMonth} className="p-1 rounded hover:bg-gray-100 text-gray-600 text-xs font-medium">
              ›
            </button>
          </div>
          <div className="grid grid-cols-7 gap-0.5 text-center">
            {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d) => (
              <div key={d} className="text-[9px] text-gray-400 font-medium py-0.5">{d}</div>
            ))}
            {monthDays.map((row, ri) =>
              row.map((d, ci) => (
                <button
                  key={`${ri}-${ci}`}
                  type="button"
                  disabled={d === null}
                  onClick={() => d !== null && handleDayClick(dateKey(gridMonth.year, gridMonth.month, d))}
                  className={`min-w-[28px] h-7 rounded text-[11px] font-medium ${
                    d === null ? 'invisible' : isSelected(d)
                      ? 'bg-oasis-600 text-white'
                      : isToday(d)
                        ? 'bg-oasis-100 text-oasis-800'
                        : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {d ?? ''}
                </button>
              ))
            )}
          </div>
          <p className="text-[10px] text-gray-400 mt-1">Click a day to see schedule</p>
        </div>
      )}

      {/* Legend */}
      <div className="px-3 py-1.5 border-b border-gray-50 flex items-center gap-3 text-[10px] text-gray-500 shrink-0">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-indigo-500" /> Fixed</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-amber-400" /> Floating</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-indigo-100" /> Work</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-pink-100" /> Personal</span>
      </div>

      {/* Floating tasks strip — always visible above timeline */}
      {viewMode === 'daily' && (hasFloating || loadingDay) && (
        <div className="px-3 py-2 border-b border-amber-100 bg-amber-50/50 shrink-0">
          <div className="text-[10px] font-semibold text-amber-800 mb-1.5">🔄 Floating tasks (no time)</div>
          {loadingDay ? (
            <p className="text-[11px] text-amber-600">Loading…</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {floatingForDay.map((ft) => (
                <span
                  key={`${ft.title}:${ft.date}`}
                  className="inline-flex items-center gap-1 pl-2 pr-1 py-1 rounded-lg bg-amber-100 border border-amber-200 text-[11px] font-medium text-amber-900"
                >
                  <span>🔄</span>
                  {ft.title}
                  <span className="text-amber-600">{ft.account === 'work' ? '💼' : '🏠'}</span>
                  {onRemoveFloatingTask && (
                    <button
                      type="button"
                      onClick={() => onRemoveFloatingTask(ft.title, ft.date)}
                      className="ml-0.5 w-5 h-5 flex items-center justify-center rounded text-amber-600 hover:text-red-600 hover:bg-red-50 shrink-0"
                      title="Remove floating task"
                    >
                      ×
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Daily timeline + draggable column */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-2 min-h-0">
        {viewMode === 'yearly' && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500">Pick a month, then click a day in Month view.</p>
            {Array.from({ length: 12 }, (_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  const y = new Date().getFullYear();
                  setGridMonth({ year: y, month: i });
                  setViewMode('monthly');
                }}
                className="w-full text-left px-3 py-2 rounded-lg border border-gray-100 hover:bg-gray-50 text-sm font-medium text-gray-700"
              >
                {new Date(2000, i).toLocaleDateString(undefined, { month: 'long' })}
              </button>
            ))}
          </div>
        )}

        {viewMode === 'daily' && (
          isEmpty && !loadingDay ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 py-8">
              <span className="text-3xl mb-2">📭</span>
              <p className="text-xs">No events for this day</p>
              <p className="text-[10px] mt-1">Click a date in Month view or ask in chat</p>
            </div>
          ) : (
            <div className="relative flex">
              <div className="flex-1 space-y-0">
                {TIME_SLOTS.map((label, idx) => {
                  const hour = idx + SLOT_START_HOUR;
                  const slotEvents = fixedEvents.filter(e => getHour(e.start) === hour);
                  const hasEvent = slotEvents.length > 0;
                  return (
                    <div key={label} className="flex gap-2 min-h-[2.75rem] group">
                      <div className="w-10 shrink-0 text-[10px] text-gray-400 pt-1 text-right pr-1">{label}</div>
                      <div className={`flex-1 border-t border-gray-100 pt-1 pb-1 ${!hasEvent ? 'group-hover:bg-emerald-50/50 rounded-r-lg' : ''}`}>
                        {hasEvent ? slotEvents.map((ev, i) => <FixedEventCard key={ev.id || i} event={ev} onCancel={onDeleteEvent} />) : (
                          <div className="text-[10px] text-emerald-400 opacity-0 group-hover:opacity-100 pl-1 pt-0.5">Free</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              {hasFloating && (
                <div className="relative w-[108px] shrink-0 ml-1 min-h-[200px]">
                  {floatingForDay.map((ft) => (
                    <DraggableFloating
                      key={`${ft.title}:${ft.date}`}
                      task={{ ...ft, y: taskPositions[`${ft.title}:${ft.date}`] ?? ft.y }}
                      onDragEnd={handleDragEnd}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        )}
      </div>

      {/* Footer */}
      {(hasFixed || hasFloating || loadingDay) && viewMode === 'daily' && (
        <div className="px-3 py-2 border-t border-gray-100 flex justify-between text-[11px] text-gray-500 shrink-0">
          <span>{fixedEvents.length} fixed{hasFloating ? ` · ${floatingForDay.length} floating` : ''}</span>
        </div>
      )}
    </div>
  );
}

