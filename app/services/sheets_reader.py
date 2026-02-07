import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

def read_sheet():
    creds_path = os.getenv("GOOGLE_CREDS_PATH")
    sheet_id = os.getenv("SHEET_ID")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials = Credentials.from_service_account_file(
        creds_path,
        scopes=scopes
    )

    client = gspread.authorize(credentials)
    sheet = client.open_by_key(sheet_id)

    produto_ws = sheet.worksheet("produto")
    concorrentes_ws = sheet.worksheet("concorrentes")

    produto = produto_ws.get_all_records()
    concorrentes = concorrentes_ws.get_all_records()

    return {
        "produto": produto,
        "concorrentes": concorrentes
    }
