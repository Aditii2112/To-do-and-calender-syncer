from auth import get_calendar_service
from datetime import datetime, timedelta

def fetch_calendar_events(accounts, target_date):
    all_events = []
    
    # Using -08:00 to match America/Los_Angeles offset
    time_min = f"{target_date}T00:00:00-08:00"
    time_max = f"{target_date}T23:59:59-08:00"
    
    for acc in accounts:
        try:
            service = get_calendar_service(acc)
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=time_min, 
                timeMax=time_max,
                singleEvents=True, 
                orderBy='startTime'
            ).execute()
            
            items = events_result.get('items', [])
            for e in items:
                all_events.append({
                    "summary": e.get("summary"),
                    # Captured end time as requested for gap logic
                    "end": e.get("end").get("dateTime") or e.get("end").get("date"),
                    "start": e.get("start").get("dateTime") or e.get("start").get("date"),
                    "account": acc
                })
        except Exception as err:
            print(f"Error fetching from {acc}: {err}")
            
    return all_events

def create_calendar_event(account_name, summary, start_time_str):
    """
    Inserts a 1-hour event into the chosen account.
    start_time_str format: "YYYY-MM-DD HH:MM"
    """
    service = get_calendar_service(account_name) 
    
    start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(hours=1)
    
    event_body = {
        'summary': summary,
        'start': {
            'dateTime': start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'America/Los_Angeles'
        },
        'end': {
            'dateTime': end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'America/Los_Angeles'
        },
    }
    
    event = service.events().insert(calendarId='primary', body=event_body).execute()
    return event.get('htmlLink')

def search_calendar(accounts, query_text):
    all_events = []
    # Look from 30 days ago to 30 days in the future
    start_search = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
    end_search = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
    
    for acc in accounts:
        service = get_calendar_service(acc)
        results = service.events().list(
            calendarId='primary', 
            q=query_text, 
            timeMin=start_search, 
            timeMax=end_search, # Search into the future!
            singleEvents=True, 
            orderBy='startTime'
        ).execute()
        
        items = results.get('items', [])
        for e in items:
            all_events.append({
                "summary": e.get("summary"),
                "start": e.get("start").get("dateTime") or e.get("start").get("date"),
                "account": acc 
            })
    
    # Sort so the one closest to 'now' is first
    all_events.sort(key=lambda x: x['start']) 
    return all_events

if __name__ == "__main__":
    # Test block updated to generic accounts
    test_date = datetime.now().strftime("%Y-%m-%d")
    my_accounts = ["work", "personal"] 
    events = fetch_calendar_events(my_accounts, test_date)
    
    print(f"\n--- Events for {test_date} ---")
    for e in events:
        print(f"[{e['account']}] {e['start']} - {e['summary']}")