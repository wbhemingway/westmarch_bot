import asyncio
import logging
import time
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

import config
from utils.exceptions import CharacterAlreadyExists, CharacterNotFound, ItemNotFound
from utils.models import Character, Item, MarketLog

logger = logging.getLogger(__name__)


class SheetManager:
    # Character sheet header names
    C_H_PLAYER_ID = "player id"
    C_H_CHAR_NAME = "character name"
    C_H_CHAR_ID = "character id"
    C_H_CURRENCY = "currency"
    C_H_XP = "experience"
    C_H_LEVEL = "level"
    # Item sheet header names
    I_H_ITEM_NAME = "item name"
    I_H_COST = "cost"
    I_H_MAGIC_RARITY = "rarity"
    # MarketLog header names
    M_DATE = "date"
    M_CHAR_ID = "character id"
    M_ITEM_NAME = "item name"
    M_PRICE = "price"
    M_QUANTITY = "quantity"
    M_NOTES = "notes"

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
        self.item_sheet = None
        self.market_sheet = None

        self.lock = asyncio.Lock()

        # Character sheet column indexes
        self.c_player_id = None
        self.c_char_name = None
        self.c_char_id = None
        self.c_currency = None
        self.c_xp = None
        self.c_level = None
        # Item sheet column indexes
        self.i_name = None
        self.i_cost = None
        self.i_rarity = None
        # MarketLog column indexes
        self.m_date = None
        self.m_char_id = None
        self.m_item_name = None
        self.m_price = None
        self.m_quantity = None
        self.m_notes = None

    async def connect(self):
        """
        Asynchronously connects to Google Sheets and loads column indexes.
        """

        try:
            self.client = await asyncio.to_thread(gspread.authorize, self.creds)
            self.workbook = await asyncio.to_thread(self.client.open, self.sheet_name)
            self.char_sheet = await asyncio.to_thread(
                self.workbook.worksheet, "Characters"
            )
            self.item_sheet = await asyncio.to_thread(self.workbook.worksheet, "Items")
            self.market_sheet = await asyncio.to_thread(
                self.workbook.worksheet, "MarketLog"
            )

            logger.info("SheetManager connecting and loading header indexes...")
            c_headers = await asyncio.to_thread(self.char_sheet.row_values, 1)

            self.c_player_id = c_headers.index(self.C_H_PLAYER_ID) + 1
            self.c_char_name = c_headers.index(self.C_H_CHAR_NAME) + 1
            self.c_char_id = c_headers.index(self.C_H_CHAR_ID) + 1
            self.c_currency = c_headers.index(self.C_H_CURRENCY) + 1
            self.c_xp = c_headers.index(self.C_H_XP) + 1
            self.c_level = c_headers.index(self.C_H_LEVEL) + 1

            i_headers = await asyncio.to_thread(self.item_sheet.row_values, 1)
            self.i_cost = i_headers.index(self.I_H_COST) + 1
            self.i_name = i_headers.index(self.I_H_ITEM_NAME) + 1
            self.i_rarity = i_headers.index(self.I_H_MAGIC_RARITY) + 1
            logger.info("SheetManager connection successful.")

            m_headers = await asyncio.to_thread(self.market_sheet.row_values, 1)
            self.m_date = m_headers.index(self.M_DATE) + 1
            self.m_char_id = m_headers.index(self.M_CHAR_ID) + 1
            self.m_item_name = m_headers.index(self.M_ITEM_NAME) + 1
            self.m_price = m_headers.index(self.M_PRICE) + 1
            self.m_quantity = m_headers.index(self.M_QUANTITY) + 1
            self.m_notes = m_headers.index(self.M_NOTES) + 1

        except Exception as e:
            logger.error(
                f"Failed to connect to Google Sheet or find headers: {e}", exc_info=True
            )
            raise e

    async def _getlvl(self, exp: int) -> int:
        return exp // config.XP_PER_LEVEL + 1

    async def _get_starting_gold(self, lvl: int) -> int:
        if lvl < 3:
            return 0

        level_to_gold_map = {
            **{level: config.GP_PER_GAME_T1 for level in config.T1_SET},
            **{level: config.GP_PER_GAME_T2 for level in config.T2_SET},
            **{level: config.GP_PER_GAME_T3 for level in config.T3_SET},
            **{level: config.GP_PER_GAME_T4 for level in config.T4_SET},
            **{level: config.GP_PER_GAME_T5 for level in config.T5_SET},
        }

        total_gold = config.STARTING_GOLD
        for level in range(3, lvl):
            total_gold += level_to_gold_map.get(level, 0) * 4

        return total_gold

    async def _record_to_character(self, record: dict) -> Character:
        """
        Helper to turn a record dict into a Character class.
        """
        char = Character(
            player_id=int(record[self.C_H_PLAYER_ID]),
            char_id=int(record[self.C_H_CHAR_ID]),
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
            if int(record[self.C_H_PLAYER_ID]) == player_id:
                return record
        return None

    async def get_all_items(self) -> list[Item]:
        """
        Gets all items from the 'Items' worksheet.
        """
        async with self.lock:
            try:
                all_item_records = await asyncio.to_thread(
                    self.item_sheet.get_all_records
                )
                items = [
                    Item(
                        name=rec[self.I_H_ITEM_NAME],
                        rarity=rec[self.I_H_MAGIC_RARITY],
                        cost=int(rec[self.I_H_COST]),
                    )
                    for rec in all_item_records
                ]
                return items
            except Exception as e:
                logger.error(f"Failed to get_all_items: {e}", exc_info=True)
                raise e

    async def get_item(self, item_name: str) -> Item:
        """
        Gets a single item by its name from the 'Items' worksheet.

        This method is case-insensitive.
        """
        try:
            all_items = await self.get_all_items()
            for item in all_items:
                if item.name.lower() == item_name.lower():
                    return item

            raise ItemNotFound(f"Item '{item_name}' not found.")
        except ItemNotFound:
            raise
        except Exception as e:
            logger.error(f"Failed to get_item '{item_name}': {e}", exc_info=True)
            raise e

    async def get_character_information(self, player_id: int) -> Character:
        """
        Gets all information for a character as a Character object.
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
                all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
                record_index = next(
                    (
                        i
                        for i, record in enumerate(all_records)
                        if int(record[self.C_H_PLAYER_ID]) == player_id
                    ),
                    -1,
                )

                if record_index == -1:
                    raise CharacterNotFound(f"No character found with ID {player_id}")

                # +2 to account for header row and 0-based index
                row_to_update = record_index + 2
                await asyncio.to_thread(
                    self.char_sheet.update_cell,
                    row_to_update,
                    self.c_currency,
                    str(new_curr),
                )
                logger.info(f"Updated currency for player {player_id} to {new_curr}")
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
        start_lvl: int | None = None,
    ) -> Character:
        """
        Creates a new character in the sheet and returns its data as a Character object.
        """
        async with self.lock:
            try:
                final_start_lvl = start_lvl or config.STARTING_LEVEL

                all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
                existing = await self._find_record(player_id, all_records)
                if existing:
                    raise CharacterAlreadyExists(
                        f"Player {player_id} already has a character: {existing[self.C_H_CHAR_NAME]}"
                    )

                char_id = int(time.time() * 1000)

                starting_xp = (final_start_lvl - 1) * config.XP_PER_LEVEL
                starting_gold = await self._get_starting_gold(final_start_lvl)

                data_row = [
                    char_name,
                    player_id,
                    char_id,
                    starting_gold,
                    starting_xp,
                    final_start_lvl,
                ]
                data_row = [str(i) for i in data_row]
                await asyncio.to_thread(self.char_sheet.append_row, data_row)
                new_char_data = {
                    self.C_H_CHAR_NAME: char_name,
                    self.C_H_PLAYER_ID: player_id,
                    self.C_H_CHAR_ID: char_id,
                    self.C_H_CURRENCY: starting_gold,
                    self.C_H_XP: starting_xp,
                    self.C_H_LEVEL: final_start_lvl,
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

    async def new_market_log_entry(
        self,
        char_info: Character,
        item: Item,
        quantity: int = 1,
        notes: str = "standard",
    ):
        async with self.lock:
            try:
                cur_date = date.today().strftime("%Y-%m-%d")
                data_row = [
                    cur_date,
                    char_info.char_id,
                    item.name,
                    item.cost,
                    quantity,
                    notes,
                ]
                await asyncio.to_thread(self.market_sheet.append_row, data_row)
            except Exception as e:
                logger.error(
                    f"Unexpected error in new_market_log_entry: {e}", exc_info=True
                )
                raise e

    async def get_all_market_log_entries(self) -> list[MarketLog]:
        async with self.lock:
            try:
                all_records = await asyncio.to_thread(self.market_sheet.get_all_records)
                records = [
                    MarketLog(
                        date=rec[self.M_DATE],
                        char_id=int(rec[self.M_CHAR_ID]),
                        item_name=rec[self.M_ITEM_NAME],
                        price=int(rec[self.M_PRICE]),
                        quantity=int(rec[self.M_QUANTITY]),
                        notes=rec[self.M_NOTES],
                    )
                    for rec in all_records
                ]
                return records
            except Exception as e:
                logger.error(
                    f"Failed to get_all_market_log_entries: {e}", exc_info=True
                )
                raise e
