import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config import GOOGLE_SHEETS_CREDS_FILE, GOOGLE_SHEET_NAME

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    return sheet

def ensure_headers(sheet):
    first_row = sheet.row_values(1)
    if not first_row:
        sheet.append_row(["Date", "Name", "Role", "Question", "Answer"])

def log_responses(name: str, role: str, questions: list, answers: list):
    sheet = get_sheet()
    ensure_headers(sheet)
    
    date_today = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    for question, answer in zip(questions, answers):
        sheet.append_row([date_today, name, role, question, answer])