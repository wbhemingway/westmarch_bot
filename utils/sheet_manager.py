import asyncio
import logging
import random
import string

import gspread
from google.oauth2.service_account import Credentials

import config
from utils.exceptions import CharacterAlreadyExists, CharacterNotFound
from utils.models import Character

logger = logging.getLogger(__name__)


class SheetManager:
    def __init__(self, credentials_file: str, sheet_name: str):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self.creds = Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        self.sheet_name = sheet_name
        self.client = None
        self.workbook = None
        self.char_sheet = None

        self.lock = asyncio.Lock()

        # Character sheet header names
        self.C_H_PLAYER_ID = "player id"
        self.C_H_CHAR_NAME = "character name"
        self.C_H_CHAR_ID = "character id"
        self.C_H_CURRENCY = "currency"
        self.C_H_XP = "experience"
        self.C_H_LEVEL = "level"

        # Character sheet column indexes
        self.c_player_id = None
        self.c_char_name = None
        self.c_char_id = None
        self.c_col_currency = None
        self.c_col_xp = None
        self.c_col_level = None

    async def _connect(self):
        """
        Asynchronously connects to Google Sheets and loads column indexes.
        """

        try:
            self.client = await asyncio.to_thread(gspread.authorize, self.creds)
            self.workbook = await asyncio.to_thread(self.client.open, self.sheet_name)
            self.char_sheet = await asyncio.to_thread(
                self.workbook.worksheet, "Characters"
            )

            logger.info("SheetManager connecting and loading header indexes...")
            headers = await asyncio.to_thread(self.char_sheet.row_values, 1)
            print(headers)

            self.c_player_id = headers.index(self.C_H_PLAYER_ID) + 1
            self.c_char_name = headers.index(self.C_H_CHAR_NAME) + 1
            self.c_char_id = headers.index(self.C_H_CHAR_ID) + 1
            self.col_currency = headers.index(self.C_H_CURRENCY) + 1
            self.col_xp = headers.index(self.C_H_XP) + 1
            self.col_level = headers.index(self.C_H_LEVEL) + 1
            logger.info("SheetManager connection successful.")

        except Exception as e:
            logger.error(
                f"Failed to connect to Google Sheet or find headers: {e}", exc_info=True
            )
            raise e

    async def _record_to_character(self, record: dict) -> Character:
        """
        Helper to turn a record dict into a Character class.
        """
        char = Character(
            player_id=int(record[self.C_H_PLAYER_ID]),
            char_id=str(record[self.C_H_CHAR_ID]),
            name=str(record[self.C_H_CHAR_NAME]),
            lvl=int(record[self.C_H_LEVEL]),
            xp=int(record[self.C_H_XP]),
            cur=int(record[self.C_H_CURRENCY]),
        )
        return char

    async def _find_record(self, player_id: int, records: list[dict]) -> dict | None:
        """
        Helper to search a list of records for a player ID.
        """
        for record in records:
            if record[self.C_H_PLAYER_ID] == player_id:
                return record
        return None

    async def get_character_row(self, player_id: str | int):
        try:
            cell = await asyncio.to_thread(self.char_sheet.find, str(player_id))
            row = cell.row
            return row
        except gspread.exceptions.CellNotFound:
            logger.warning(
                f"Character lookup failed: No cell found for player ID {player_id}"
            )
            raise CharacterNotFound(
                f"No character found associated with Player ID {player_id}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in get_character_row for player_id {player_id}: {e}",
                exc_info=True,
            )
            raise e

    async def get_character_information(self, player_id: int) -> Character:
        """
        Gets all information for a character as a dictionary.
        """
        async with self.lock:
            try:
                all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
            except Exception as e:
                logger.error(f"Failed to get_all_records: {e}", exc_info=True)
                raise e

            record = await self._find_record(player_id, all_records)

            if record:
                char = await self._record_to_character(record)
                return char
            else:
                logger.warning(
                    f"Character lookup failed: No record found for player ID {player_id}"
                )
                raise CharacterNotFound(
                    f"No character found associated with Player ID {player_id}"
                )

    async def set_character_currency(self, player_id: int, new_curr: int):
        """
        Updates a character's currency using a lock and a row lookup.
        """
        async with self.lock:
            try:
                cell = await asyncio.to_thread(self.char_sheet.find, str(player_id))
                await asyncio.to_thread(
                    self.char_sheet.update_cell,
                    cell.row,
                    config.CURRENCY_COL,
                    str(new_curr),
                )
                logger.info(f"Updated currency for player {player_id} to {new_curr}")
            except gspread.exceptions.CellNotFound:
                logger.warning(
                    f"set_character_currency failed: No cell found for player ID {player_id}"
                )
                raise CharacterNotFound(f"No character found with ID {player_id}")
            except Exception as e:
                logger.error(
                    f"Unexpected error in set_character_currency for {player_id}: {e}",
                    exc_info=True,
                )
                raise e

    async def create_new_character(
        self,
        char_name: str,
        player_id: int,
        starting_curr: int,
        starting_exp: int,
        starting_lvl: int,
    ) -> Character:
        """
        Creates a new character row.
        """
        async with self.lock:
            try:
                all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
                existing = await self._find_record(player_id, all_records)
                if existing:
                    raise CharacterAlreadyExists(
                        f"Player {player_id} already has a character: {existing[self.C_H_CHAR_NAME]}"
                    )

                characters = string.ascii_uppercase + string.digits
                char_id = "".join(random.choice(characters) for _ in range(18))

                data_row = [
                    char_name,
                    player_id,
                    char_id,
                    str(starting_curr),
                    str(starting_exp),
                    str(starting_lvl),
                ]
                await asyncio.to_thread(self.char_sheet.append_row, data_row)
                new_char_data = {
                    self.C_H_CHAR_NAME: char_name,
                    self.C_H_PLAYER_ID: player_id,
                    self.C_H_CHAR_ID: char_id,
                    self.C_H_CURRENCY: starting_curr,
                    self.C_H_XP: starting_exp,
                    self.C_H_LEVEL: starting_lvl,
                }
                logger.info(
                    f"Created new character '{char_name}' for player {player_id}"
                )
                new_char = await self._record_to_character(new_char_data)
                return new_char
            except CharacterAlreadyExists:
                logger.warning(
                    f"Attempted to create duplicate character for {player_id}"
                )
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in crate_new_character for player_id : {e}",
                    exc_info=True,
                )
                raise e
