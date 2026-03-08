import { useCallback, useEffect, useState } from 'react';
import { chat, deleteEvent, fetchEventsForDay, type ChatResponse } from './api/client';
import { AppShell } from './components/AppShell';
import { CalendarView, type FloatingTask } from './components/CalendarView';
import { ChatPane } from './components/ChatPane';

const STORAGE_KEY = 'oasis_floating_tasks';

function loadFloatingTasksFromStorage(): FloatingTask[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((t: unknown, i: number) => {
      if (t && typeof t === 'object' && 'title' in t && 'date' in t && 'account' in t) {
        return {
          title: String((t as { title: unknown }).title),
          date: String((t as { date: unknown }).date),
          account: String((t as { account: unknown }).account),
          y: typeof (t as { y?: unknown }).y === 'number' ? (t as { y: number }).y : i * 56,
        };
      }
      return null;
    }).filter((t): t is FloatingTask => t !== null);
  } catch {
    return [];
  }
}

function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function App() {
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [floatingTasks, setFloatingTasks] = useState<FloatingTask[]>(loadFloatingTasksFromStorage);
  const [selectedDate, setSelectedDate] = useState<string>(todayStr());
  const [loadingDay, setLoadingDay] = useState(false);

  const handleFetchDay = useCallback(async (date: string) => {
    setSelectedDate(date);
    setLoadingDay(true);
    try {
      const data = await fetchEventsForDay(date);
      setLastResponse({
        final_decision: '',
        needs_booking_ui: false,
        parsed_task: {
          title: '',
          date: data.date,
          category: 'fixed',
          account_id: 'personal',
          intent: 'summarize',
          summary_horizon: 'daily',
        },
        existing_events: data.existing_events,
        suggested_slots: undefined,
        query_events: undefined,
        summary_horizon: 'daily',
      });
    } catch {
      setLoadingDay(false);
      return;
    }
    setLoadingDay(false);
  }, []);

  // Persist floating tasks to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(floatingTasks));
    } catch {
      // ignore quota or disabled storage
    }
  }, [floatingTasks]);

  // On first load, show today and fetch today's events
  useEffect(() => {
    handleFetchDay(todayStr());
  }, [handleFetchDay]);

  const handleResponse = useCallback((res: ChatResponse) => {
    setLastResponse(prev => {
      if (!prev) return res;
      // Some chat responses (e.g. create flow ask/choice) intentionally do not include events.
      // Keep the current calendar events so fixed items don't disappear on the right panel.
      const keepExistingEvents = !res.existing_events && !!prev.existing_events;
      return {
        ...res,
        existing_events: keepExistingEvents ? prev.existing_events : res.existing_events,
      };
    });
    // Query responses should not hijack the calendar's selected day.
    if (res.parsed_task?.date && res.parsed_task.intent !== 'query') {
      setSelectedDate(res.parsed_task.date);
    }

    // Only add to floating list when user explicitly chose "Floating" (strict: must be false, not undefined).
    if (
      res.parsed_task.intent === 'create' &&
      res.parsed_task.category === 'floating' &&
      res.needs_floating_vs_fixed_choice === false
    ) {
      setFloatingTasks(prev => {
        const key = `${res.parsed_task.title}:${res.parsed_task.date}`;
        const exists = prev.some(t => `${t.title}:${t.date}` === key);
        if (exists) return prev;
        return [
          ...prev,
          {
            title: res.parsed_task.title,
            date: res.parsed_task.date,
            account: res.parsed_task.account_id,
            y: prev.length * 56,
          },
        ];
      });
    }
  }, []);

  const handleDeleteEvent = useCallback(async (accountId: string, eventId: string) => {
    try {
      await deleteEvent({ account_id: accountId, event_id: eventId });
      await handleFetchDay(selectedDate);
    } catch (e) {
      console.error(e);
      alert(e instanceof Error ? e.message : 'Could not delete event.');
    }
  }, [selectedDate, handleFetchDay]);

  const handleRemoveFloatingTask = useCallback((title: string, date: string) => {
    setFloatingTasks(prev => prev.filter(t => !(t.title === title && t.date === date)));
  }, []);

  const handleBookedSuccess = useCallback(
    (date: string, title?: string, startTime?: string, endTime?: string, accountId?: string) => {
      if (!date) return;
      if (title) {
        setFloatingTasks(prev => prev.filter(t => !(t.title === title && t.date === date)));
      }
      // Optimistic update: show the new event on the calendar immediately
      const st = startTime || '09:00';
      const et = endTime || '10:00';
      const acc = accountId || 'personal';
      const newEvent = {
        summary: title || 'Event',
        start: `${date}T${st}:00`,
        end: `${date}T${et}:00`,
        account: acc,
        category: 'fixed' as const,
      };
      setLastResponse(prev => {
        if (!prev) return prev;
        const work = prev.existing_events?.work ?? [];
        const personal = prev.existing_events?.personal ?? [];
        if (prev.parsed_task?.date !== date) {
          return {
            ...prev,
            parsed_task: { ...prev.parsed_task, date },
            existing_events: {
              work: acc === 'work' ? [newEvent] : [],
              personal: acc === 'personal' ? [newEvent] : [],
            },
            summary_horizon: 'daily',
          };
        }
        const mergedWork = acc === 'work' ? [...work, newEvent] : work;
        const mergedPersonal = acc === 'personal' ? [...personal, newEvent] : personal;
        return {
          ...prev,
          existing_events: { work: mergedWork, personal: mergedPersonal },
        };
      });
      setSelectedDate(date);
      // Refetch to get real event (with id for delete) after API has it
      setTimeout(() => handleFetchDay(date), 800);
    },
    [handleFetchDay]
  );

  return (
    <AppShell>
      <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 h-[calc(100vh-5rem)] min-h-0">
        <div className="flex-1 min-w-0 min-h-0">
          <ChatPane onResponse={handleResponse} onBookedSuccess={handleBookedSuccess} />
        </div>
        <div className="w-full lg:min-w-[400px] lg:max-w-[480px] shrink-0 min-h-0">
          <CalendarView
            response={lastResponse}
            floatingTasks={floatingTasks}
            selectedDate={selectedDate}
            loadingDay={loadingDay}
            onFetchDay={handleFetchDay}
            onDeleteEvent={handleDeleteEvent}
            onRemoveFloatingTask={handleRemoveFloatingTask}
          />
        </div>
      </div>
    </AppShell>
  );
}

export default App;
