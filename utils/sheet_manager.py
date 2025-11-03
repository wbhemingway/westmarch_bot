import gspread
import asyncio
from google.oauth2.service_account import Credentials


class SheetManager:
    def __init__(self, credentials_file: str, sheet_name: str):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        self.client = gspread.authorize(creds)

        self.workbook = self.client.open(sheet_name)
        self.char_sheet = self.workbook.worksheet("Characters")

        self.lock = asyncio.Lock()
