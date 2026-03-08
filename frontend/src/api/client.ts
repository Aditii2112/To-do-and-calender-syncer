const API_BASE = import.meta.env.VITE_API_BASE || '/api';

// --- Types ---

export interface EventAttendee {
  email: string;
  displayName: string;
}

export interface CalendarEvent {
  id?: string;
  summary: string;
  start: string;
  end: string;
  account: string;
  attendees?: EventAttendee[];
  description?: string;
  category?: 'fixed' | 'floating';
}

export interface QueryEvent {
  summary: string;
  start: string;
  end?: string;
  account: string;
  attendees?: EventAttendee[];
  description?: string;
  category?: string;
}

export interface ParsedTask {
  title: string;
  date: string;
  start_time?: string;
  end_time?: string;
  category: string;
  account_id: string;
  intent: string;
  summary_horizon?: string;
}

export interface SuggestedSlot {
  start_time: string;
  end_time: string;
  account_suggestions?: string[];
}

export interface ChatResponse {
  final_decision: string;
  needs_booking_ui: boolean;
  needs_floating_vs_fixed_choice?: boolean;
  parsed_task: ParsedTask;
  existing_events?: {
    work: CalendarEvent[];
    personal: CalendarEvent[];
  };
  suggested_slots?: SuggestedSlot[];
  query_events?: QueryEvent[];
  summary_horizon?: string;
}

export interface BookPayload {
  title: string;
  date: string;
  start_time: string;
  end_time?: string;
  account_id: string;
  category?: string;
  description?: string;
}

export interface BookResponse {
  ok: boolean;
  event_link?: string;
  message: string;
}

// --- Client functions ---

export async function chat(userInput: string, timezone?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: userInput, timezone }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Chat request failed');
  }
  return res.json();
}

export async function book(payload: BookPayload): Promise<BookResponse> {
  const res = await fetch(`${API_BASE}/book`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Booking failed');
  }
  return data;
}

export interface DeleteEventPayload {
  account_id: string;
  event_id: string;
}

export interface DeleteEventResponse {
  ok: boolean;
  message: string;
}

export async function deleteEvent(payload: DeleteEventPayload): Promise<DeleteEventResponse> {
  const res = await fetch(`${API_BASE}/event/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Delete failed');
  }
  return data;
}

/** Fetch events for a single day. Google API only — no LLM. Use when user clicks a date. */
export interface DayEventsResponse {
  date: string;
  existing_events: { work: CalendarEvent[]; personal: CalendarEvent[] };
}

export async function fetchEventsForDay(date: string): Promise<DayEventsResponse> {
  const res = await fetch(`${API_BASE}/events?date=${encodeURIComponent(date)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch events');
  }
  return res.json();
}

/** User chose "Assign a time" — get suggested slots (Google API only, no LLM). */
export interface BookingSlotsResponse {
  needs_booking_ui: boolean;
  suggested_slots: SuggestedSlot[];
  parsed_task: ParsedTask;
}

export async function fetchBookingSlots(parsed_task: ParsedTask): Promise<BookingSlotsResponse> {
  const res = await fetch(`${API_BASE}/booking/slots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parsed_task }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to get slots');
  }
  return res.json();
}
