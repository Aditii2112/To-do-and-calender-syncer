import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service(account_name: str):
    creds = None
    token_file = f'token_{account_name}.json'

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # prompt='select_account' forces Google to ask WHICH email you want to use
            creds = flow.run_local_server(port=0, prompt='select_account')

        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def check_auth_status():
    """Returns auth status for work and personal accounts."""
    status = {"work": False, "personal": False}
    for acc in ["work", "personal"]:
        try:
            token_file = f"token_{acc}.json"
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
                if creds and creds.valid:
                    status[acc] = True
                elif creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    status[acc] = True
        except Exception:
            pass
    return status


if __name__ == "__main__":
    print("Logging into Personal...")
    get_calendar_service("personal")
    print("Logging into Work...")
    get_calendar_service("work")