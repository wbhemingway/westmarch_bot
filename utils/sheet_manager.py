import asyncio

import gspread
from google.oauth2.service_account import Credentials

NAME_COL = 1
PLAYER_ID_COL = 2
CHARACTER_ID_COL = 3
CURRENCY_COL = 4
EXPERIENCE_COL = 5
LEVEL_COL = 6


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

    async def get_character_row(self, player_id):
        try:
            cell = await asyncio.to_thread(self.char_sheet.find, player_id)
            row = cell.row
            return row
        except Exception as e:
            print(f"error in get_char_row: {e}")
            return None

    async def get_character_information(self, player_id: str):
        row_num = await self.get_character_row(player_id)
        if not row_num:
            return None
        row_data = await asyncio.to_thread(self.char_sheet.row_values, row_num)
        return row_data

    async def set_character_currency(self, player_id: str, new_curr: int):
        row_num = await self.get_character_row(player_id)
        if not row_num:
            return None
        await asyncio.to_thread(
            self.char_sheet.update_cell, row_num, CURRENCY_COL, str(new_curr)
        )
