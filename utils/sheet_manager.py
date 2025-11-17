import asyncio
import logging
import time
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

import config
from utils.decorators import with_lock
from utils.exceptions import CharacterAlreadyExists, CharacterNotFound, ItemNotFound
from utils.models import Character, Item, MarketLog

logger = logging.getLogger(__name__)


TIER_GP_MAP_DATA = [
    (config.T1_SET, config.GP_PER_GAME_T1),
    (config.T2_SET, config.GP_PER_GAME_T2),
    (config.T3_SET, config.GP_PER_GAME_T3),
    (config.T4_SET, config.GP_PER_GAME_T4),
    (config.T5_SET, config.GP_PER_GAME_T5),
]

TIER_GP_MAP = {
    level: gold for level_set, gold in TIER_GP_MAP_DATA for level in level_set
}


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
    # GameLog header names
    G_DATE = "date"
    G_DM_ID = "dm id"
    G_PID_1 = "p1 id"
    G_ID_2 = "p2 id"
    G_ID_3 = "p3 id"
    G_ID_4 = "p4 id"
    G_ID_5 = "p5 id"
    G_ID_6 = "p6 id"

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
        self.game_sheet = None

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
        # GameLog column indexes
        self.g_date = None
        self.g_dm_id = None
        self.g_pid_1 = None
        self.g_pid_2 = None
        self.g_pid_3 = None
        self.g_pid_4 = None
        self.g_pid_5 = None
        self.g_pid_6 = None

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
            self.game_sheet = await asyncio.to_thread(
                self.workbook.worksheet, "GameLog"
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

            g_headers = await asyncio.to_thread(self.game_sheet.row_values, 1)
            self.g_date = g_headers.index(self.G_DATE) + 1
            self.g_dm_id = g_headers.index(self.G_DM_ID) + 1
            self.g_pid_1 = g_headers.index(self.G_PID_1) + 1
            self.g_pid_2 = g_headers.index(self.G_ID_2) + 1
            self.g_pid_3 = g_headers.index(self.G_ID_3) + 1
            self.g_pid_4 = g_headers.index(self.G_ID_4) + 1
            self.g_pid_5 = g_headers.index(self.G_ID_5) + 1
            self.g_pid_6 = g_headers.index(self.G_ID_6) + 1

        except Exception as e:
            logger.error(
                f"Failed to connect to Google Sheet or find headers: {e}", exc_info=True
            )
            raise e

    def _getlvl(self, exp: int) -> int:
        return exp // config.XP_PER_LEVEL + 1

    def _get_starting_gold(self, lvl: int) -> int:
        if lvl < 3:
            return 0

        total_gold = config.STARTING_GOLD
        for level in range(3, lvl):
            total_gold += TIER_GP_MAP.get(level, 0) * 4

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

    @with_lock
    async def get_all_items(self) -> list[Item]:
        """
        Gets all items from the 'Items' worksheet.
        """
        all_item_records = await asyncio.to_thread(self.item_sheet.get_all_records)
        items = [
            Item(
                name=rec[self.I_H_ITEM_NAME],
                rarity=rec[self.I_H_MAGIC_RARITY],
                cost=int(rec[self.I_H_COST]),
            )
            for rec in all_item_records
        ]
        return items

    async def get_item(self, item_name: str) -> Item:
        """
        Gets a single item by its name from the 'Items' worksheet.

        This method is case-insensitive.
        """
        all_items = await self.get_all_items()
        for item in all_items:
            if item.name.lower() == item_name.lower():
                return item
        raise ItemNotFound(f"Item '{item_name}' not found.")

    @with_lock
    async def get_character_information(self, player_id: int) -> Character:
        """
        Gets all information for a character as a Character object.
        """
        all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
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

    @with_lock
    async def get_characters_by_ids(self, player_ids: list[int]) -> list[Character]:
        """
        Gets all information for multiple characters in a single sheet read.
        """
        if not player_ids:
            return []

        all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
        player_id_set = set(player_ids)
        found_characters = []
        found_player_ids = set()

        for record in all_records:
            try:
                record_player_id = int(record[self.C_H_PLAYER_ID])
                if record_player_id in player_id_set:
                    char = await self._record_to_character(record)
                    found_characters.append(char)
                    found_player_ids.add(record_player_id)
            except (ValueError, KeyError):
                continue

        missing_ids = player_id_set - found_player_ids
        if missing_ids:
            logger.warning(f"Character lookup failed for player IDs: {missing_ids}")
            raise CharacterNotFound("Could not find characters for some players.")

        return found_characters

    @with_lock
    async def set_character_currency(self, player_id: int, new_curr: int):
        """
        Updates a character's currency using a lock and a row lookup.
        """
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

    @with_lock
    async def create_new_character(
        self,
        char_name: str,
        player_id: int,
        start_lvl: int | None = None,
    ) -> Character:
        """
        Creates a new character in the sheet and returns its data as a Character object.
        """
        final_start_lvl = start_lvl or config.STARTING_LEVEL

        all_records = await asyncio.to_thread(self.char_sheet.get_all_records)
        existing = await self._find_record(player_id, all_records)
        if existing:
            logger.warning(f"Attempted to create duplicate character for {player_id}")
            raise CharacterAlreadyExists(
                f"Player {player_id} already has a character: {existing[self.C_H_CHAR_NAME]}"
            )

        char_id = int(time.time() * 1000)

        starting_xp = (final_start_lvl - 1) * config.XP_PER_LEVEL
        starting_gold = self._get_starting_gold(final_start_lvl)

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
        logger.info(f"Created new character '{char_name}' for player {player_id}")
        new_char = await self._record_to_character(new_char_data)
        return new_char

    @with_lock
    async def new_market_log_entry(
        self,
        char_info: Character,
        item: Item,
        quantity: int = 1,
        notes: str = "standard",
    ):
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

    @with_lock
    async def get_all_market_log_entries(self) -> list[MarketLog]:
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

    @with_lock
    async def log_game(self, dm_id: int, players: list[Character]) -> None:
        """
        Awards XP and Gold to a list of characters for playing a game.
        This is optimized to read the sheet once and write updates in a batch.
        """
        all_records = await asyncio.to_thread(self.char_sheet.get_all_records)

        player_ids_str = [str(p.player_id) for p in players]
        cells_to_update = []
        player_ids_in_game = set(player_ids_str)
        for i, record in enumerate(all_records):
            try:
                record_player_id = str(record[self.C_H_PLAYER_ID])
            except (ValueError, KeyError):
                continue
            if record_player_id in player_ids_in_game:
                # +2 for header row and 0-based index
                row_index = i + 2

                current_xp = int(record[self.C_H_XP])
                current_lvl = int(record[self.C_H_LEVEL])
                current_gold = int(record[self.C_H_CURRENCY])
                gold_reward = TIER_GP_MAP.get(current_lvl, 0)

                new_xp = current_xp + config.XP_PER_GAME
                new_lvl = self._getlvl(new_xp)
                new_gold = current_gold + gold_reward

                cells_to_update.append(gspread.Cell(row_index, self.c_xp, str(new_xp)))
                cells_to_update.append(
                    gspread.Cell(row_index, self.c_level, str(new_lvl))
                )
                cells_to_update.append(
                    gspread.Cell(row_index, self.c_currency, str(new_gold))
                )

        if cells_to_update:
            await asyncio.to_thread(self.char_sheet.update_cells, cells_to_update)
            logger.info(
                f"Logged game for {len(players)} players. Applied {len(cells_to_update)} cell updates."
            )
            cur_date = date.today().strftime("%Y-%m-%d")
            row_data = [
                cur_date,
                str(dm_id),
            ]
            row_data.extend(player_ids_str)
            await asyncio.to_thread(self.game_sheet.append_row, row_data)
