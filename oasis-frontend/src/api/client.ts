/**
 * API client for Oasis OS backend.
 * Uses VITE_API_BASE or /api (proxied to backend) by default.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

// --- Types ---

export interface ParsedTask {
  title: string;
  date: string;
  start_time?: string;
  end_time?: string;
  category: string;
  account_id: string;
  intent: string;
}

export interface SuggestedSlot {
  start_time: string;
  end_time: string;
  account_suggestions?: string[];
}

export interface ChatResponse {
  final_decision: string;
  needs_booking_ui: boolean;
  parsed_task: ParsedTask;
  existing_events?: {
    work: CalendarEvent[];
    personal: CalendarEvent[];
  };
  suggested_slots?: SuggestedSlot[];
  query_events?: QueryEvent[];
}

export interface CalendarEvent {
  summary: string;
  start: string;
  end?: string;
  account: string;
}

export interface QueryEvent {
  summary: string;
  start: string;
  account: string;
}

export interface BookPayload {
  title: string;
  date: string;
  start_time: string;
  end_time?: string;
  account_id: string;
  category?: string;
}

export interface BookResponse {
  ok: boolean;
  event_link?: string;
  message: string;
}

// --- Client ---

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
