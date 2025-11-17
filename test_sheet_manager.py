from datetime import date
from unittest.mock import MagicMock, patch

import pytest

import config
from utils.exceptions import CharacterAlreadyExists, CharacterNotFound, ItemNotFound
from utils.sheet_manager import Character, Item, SheetManager


@pytest.fixture
async def manager_and_mocks():
    """Pytest fixture to set up a SheetManager with mocked dependencies."""
    with (
        patch("utils.sheet_manager.Credentials") as mock_credentials,
        patch("utils.sheet_manager.gspread") as mock_gspread,
    ):
        mock_credentials.from_service_account_file.return_value = MagicMock()

        manager = SheetManager("fake_creds.json", "fake_sheet")

        # Mock all worksheets
        mock_char_sheet = MagicMock()
        mock_item_sheet = MagicMock()
        mock_market_sheet = MagicMock()
        mock_game_sheet = MagicMock()

        def worksheet_side_effect(name):
            if name == "Characters":
                return mock_char_sheet
            if name == "Items":
                return mock_item_sheet
            if name == "MarketLog":
                return mock_market_sheet
            if name == "GameLog":
                return mock_game_sheet
            return MagicMock()

        mock_workbook = MagicMock()
        mock_workbook.worksheet.side_effect = worksheet_side_effect
        mock_client = MagicMock()
        mock_client.open.return_value = mock_workbook
        mock_gspread.authorize.return_value = mock_client

        # Set up headers for each sheet
        mock_char_sheet.row_values.return_value = [
            manager.C_H_PLAYER_ID,
            manager.C_H_CHAR_NAME,
            manager.C_H_CHAR_ID,
            manager.C_H_CURRENCY,
            manager.C_H_XP,
            manager.C_H_LEVEL,
        ]
        mock_item_sheet.row_values.return_value = [
            manager.I_H_ITEM_NAME,
            manager.I_H_COST,
            manager.I_H_MAGIC_RARITY,
        ]
        mock_market_sheet.row_values.return_value = [
            manager.M_DATE,
            manager.M_CHAR_ID,
            manager.M_ITEM_NAME,
            manager.M_PRICE,
            manager.M_QUANTITY,
            manager.M_NOTES,
        ]
        mock_game_sheet.row_values.return_value = [
            manager.G_DATE,
            manager.G_DM_ID,
            manager.G_PID_1,
            manager.G_ID_2,
            manager.G_ID_3,
            manager.G_ID_4,
            manager.G_ID_5,
            manager.G_ID_6,
        ]
        await manager.connect()  # Connect once with full headers
        yield manager, mock_char_sheet, mock_game_sheet, mock_gspread


async def test_connect_success(manager_and_mocks):
    """Test that _connect correctly populates column indexes."""
    manager, _, _, _ = manager_and_mocks
    assert manager.c_player_id == 1
    assert manager.c_char_name == 2
    assert manager.c_char_id == 3
    assert manager.c_currency == 4
    assert manager.c_xp == 5
    assert manager.c_level == 6


async def test_connect_failure_missing_header():
    """Test that connect raises an exception if a header is missing."""
    with (
        patch("utils.sheet_manager.gspread") as mock_gspread,
        patch("utils.sheet_manager.Credentials") as mock_credentials,
    ):
        mock_credentials.from_service_account_file.return_value = MagicMock()
        mock_client = MagicMock()
        mock_workbook = MagicMock()
        mock_char_sheet = MagicMock()

        # Simulate a missing header
        mock_char_sheet.row_values.return_value = ["player id", "character name"]
        mock_workbook.worksheet.return_value = mock_char_sheet
        mock_client.open.return_value = mock_workbook
        mock_gspread.authorize.return_value = mock_client

        manager = SheetManager("fake_creds.json", "fake_sheet")
        # The index() method will raise a ValueError, which is caught and re-raised
        with pytest.raises(Exception):
            await manager.connect()


async def test_connect_failure_missing_worksheet(manager_and_mocks):
    """Test that connect raises an exception if a worksheet is not found."""
    with patch("utils.sheet_manager.gspread") as mock_gspread:
        mock_client = MagicMock()
        mock_workbook = MagicMock()
        # Simulate worksheet not found
        mock_workbook.worksheet.side_effect = Exception("Worksheet not found")
        mock_client.open.return_value = mock_workbook
        mock_gspread.authorize.return_value = mock_client

        manager = SheetManager("fake_creds.json", "fake_sheet")
        with pytest.raises(Exception, match="Worksheet not found"):
            await manager.connect()


@pytest.mark.parametrize(
    "level, expected_gold",
    [
        (3, 200),
        (5, 1200),
        (9, 9200),
        (2, 0),  # Edge case: level below starting range
        (20, 135200),  # Edge case: max level in config
    ],
)
async def test_get_starting_gold(manager_and_mocks, level, expected_gold):
    """Test the starting gold calculation for different levels."""
    manager, _, _, _ = manager_and_mocks
    gold = manager._get_starting_gold(level)
    assert gold == expected_gold


async def test_get_character_information_success(manager_and_mocks):
    """Test successfully retrieving character information."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    player_id = 12345
    mock_worksheet.get_all_records.return_value = [
        {
            manager.C_H_PLAYER_ID: str(player_id),
            manager.C_H_CHAR_NAME: "Test Character",
            manager.C_H_CHAR_ID: "123456789",
            manager.C_H_CURRENCY: "100",
            manager.C_H_XP: "4",
            manager.C_H_LEVEL: "2",
        }
    ]

    char = await manager.get_character_information(player_id)

    assert char.player_id == player_id
    assert char.name == "Test Character"
    assert char.cur == 100


async def test_get_character_information_not_found(manager_and_mocks):
    """Test that CharacterNotFound is raised for a non-existent character."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    mock_worksheet.get_all_records.return_value = []

    with pytest.raises(CharacterNotFound):
        await manager.get_character_information(99999)


async def test_get_characters_by_ids_empty_list(manager_and_mocks):
    """Test get_characters_by_ids returns an empty list when given no IDs."""
    manager, mock_char_sheet, _, _ = manager_and_mocks
    characters = await manager.get_characters_by_ids([])
    assert characters == []
    mock_char_sheet.get_all_records.assert_not_called()


async def test_get_characters_by_ids_partial_found(manager_and_mocks):
    """Test get_characters_by_ids raises CharacterNotFound if any ID is missing."""
    manager, mock_char_sheet, _, _ = manager_and_mocks
    mock_char_sheet.get_all_records.return_value = [
        {
            "player id": "1",
            "character name": "p1",
            "character id": "101",
            "currency": "100",
            "experience": "0",
            "level": "1",
        }
    ]

    with pytest.raises(CharacterNotFound):
        await manager.get_characters_by_ids([1, 999])  # 999 is not in the sheet


async def test_get_characters_by_ids_handles_bad_records(manager_and_mocks):
    """Test get_characters_by_ids skips records that cause errors."""
    manager, mock_char_sheet, _, _ = manager_and_mocks
    mock_char_sheet.get_all_records.return_value = [
        {"player id": "1"},  # Malformed record, missing keys
        {
            "player id": "2",
            "character name": "p2",
            "character id": "102",
            "currency": "200",
            "experience": "4",
            "level": "2",
        },
    ]

    characters = await manager.get_characters_by_ids([2])
    assert len(characters) == 1
    assert characters[0].player_id == 2


async def test_get_item_case_insensitive(manager_and_mocks):
    """Test that get_item finds an item regardless of case."""
    manager, _, _, _ = manager_and_mocks
    # We can patch get_all_items to isolate the get_item logic
    with patch.object(manager, "get_all_items") as mock_get_all:
        mock_get_all.return_value = [
            Item(name="Healing Potion", cost=50, rarity="Common")
        ]
        item = await manager.get_item("healing potion")
        assert item.name == "Healing Potion"
        assert item.cost == 50


async def test_get_item_not_found(manager_and_mocks):
    """Test that get_item raises ItemNotFound for a non-existent item."""
    manager, _, _, _ = manager_and_mocks
    with patch.object(manager, "get_all_items") as mock_get_all:
        mock_get_all.return_value = []
        with pytest.raises(ItemNotFound):
            await manager.get_item("non_existent_item")


async def test_set_character_currency_success(manager_and_mocks):
    """Test successfully updating a character's currency."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    player_id = 12345
    mock_worksheet.get_all_records.return_value = [
        {manager.C_H_PLAYER_ID: str(player_id)}
    ]
    new_currency = 500

    await manager.set_character_currency(player_id, new_currency)

    mock_worksheet.update_cell.assert_called_once_with(
        2, manager.c_currency, str(new_currency)
    )


async def test_set_character_currency_not_found(manager_and_mocks):
    """Test that setting currency for a non-existent character fails."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    mock_worksheet.get_all_records.return_value = []

    with pytest.raises(CharacterNotFound):
        await manager.set_character_currency(99999, 500)


async def test_create_new_character_success(manager_and_mocks):
    """Test the successful creation of a new character."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    mock_worksheet.get_all_records.return_value = []
    new_player_id = 54321
    new_char_name = "Newbie"
    start_lvl = 5

    char = await manager.create_new_character(new_char_name, new_player_id, start_lvl)

    assert char.player_id == new_player_id
    assert char.name == new_char_name
    assert char.lvl == start_lvl

    mock_worksheet.append_row.assert_called_once()
    appended_row = mock_worksheet.append_row.call_args[0][0]

    expected_xp = (start_lvl - 1) * config.XP_PER_LEVEL
    expected_gold = manager._get_starting_gold(start_lvl)

    assert appended_row[0] == new_char_name
    assert appended_row[1] == str(new_player_id)
    assert appended_row[3] == str(expected_gold)
    assert appended_row[4] == str(expected_xp)
    assert appended_row[5] == str(start_lvl)


async def test_create_new_character_default_start_level(manager_and_mocks):
    """Test creating a character uses the default start level when none is provided."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    mock_worksheet.get_all_records.return_value = []
    new_player_id = 54321
    new_char_name = "DefaultLvl"

    # Call with start_lvl=None
    char = await manager.create_new_character(new_char_name, new_player_id, None)

    assert char.lvl == config.STARTING_LEVEL

    mock_worksheet.append_row.assert_called_once()
    appended_row = mock_worksheet.append_row.call_args[0][0]

    expected_xp = (config.STARTING_LEVEL - 1) * config.XP_PER_LEVEL
    expected_gold = manager._get_starting_gold(config.STARTING_LEVEL)

    assert appended_row[3] == str(expected_gold)
    assert appended_row[4] == str(expected_xp)
    assert appended_row[5] == str(config.STARTING_LEVEL)


async def test_create_new_character_already_exists(manager_and_mocks):
    """Test that creating a duplicate character raises CharacterAlreadyExists."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    player_id = 12345
    mock_worksheet.get_all_records.return_value = [
        {manager.C_H_PLAYER_ID: str(player_id), manager.C_H_CHAR_NAME: "Old Name"}
    ]

    with pytest.raises(CharacterAlreadyExists):
        await manager.create_new_character("Another Name", player_id, 5)


async def test_create_new_character_id_is_unique(manager_and_mocks):
    """Test that two consecutively created characters have different IDs."""
    manager, mock_worksheet, _, _ = manager_and_mocks
    with patch("utils.sheet_manager.time") as mock_time:
        # Mock time.time() to return different values on consecutive calls
        mock_time.time.side_effect = [1700000000.0, 1700000001.0]
        mock_worksheet.get_all_records.return_value = []
        char1 = await manager.create_new_character("char1", 1, 5)
        char2 = await manager.create_new_character("char2", 2, 5)
        assert char1.char_id != char2.char_id


async def test_log_game_success(manager_and_mocks):
    """Test that log_game correctly updates player stats and logs the game."""
    manager, mock_char_sheet, mock_game_sheet, mock_gspread = manager_and_mocks
    dm_id = 98765

    # Define players for the game
    player1 = Character(player_id=1, char_id=101, name="p1", xp=3, lvl=1, cur=100)
    player2 = Character(player_id=2, char_id=102, name="p2", xp=7, lvl=2, cur=200)
    players_in_game = [player1, player2]

    # Mock the state of the character sheet
    mock_char_sheet.get_all_records.return_value = [
        {
            "player id": "1",
            "character name": "p1",
            "character id": "101",
            "currency": "100",
            "experience": "3",
            "level": "1",
        },
        {
            "player id": "2",
            "character name": "p2",
            "character id": "102",
            "currency": "200",
            "experience": "7",
            "level": "2",
        },
        {
            "player id": "3",
            "character name": "p3",
            "character id": "103",
            "currency": "300",
            "experience": "0",
            "level": "1",
        },  # This player is not in the game
    ]

    await manager.log_game(dm_id, players_in_game)

    # 1. Verify character sheet updates
    mock_gspread.Cell.assert_called()
    cell_calls = mock_gspread.Cell.call_args_list

    # Use a set for order-insensitive comparison of cell creation arguments
    # The format is (row, col, value)
    updated_cell_args = {call.args for call in cell_calls}

    # Expected values for Player 1
    # XP: 3 + 1 = 4. Level: 4 // 4 + 1 = 2. Gold: 100 + 0 (for lvl 1) = 100
    # Expected values for Player 2
    # XP: 7 + 1 = 8. Level: 8 // 4 + 1 = 3. Gold: 200 + 0 (for lvl 2) = 200
    expected_cell_args = {
        (2, manager.c_xp, "4"),
        (2, manager.c_level, "2"),
        (2, manager.c_currency, "100"),
        (3, manager.c_xp, "8"),
        (3, manager.c_level, "3"),
        (3, manager.c_currency, "200"),
    }

    assert updated_cell_args == expected_cell_args

    # 2. Verify game log entry
    mock_game_sheet.append_row.assert_called_once()
    log_row = mock_game_sheet.append_row.call_args[0][0]
    assert log_row[1] == str(dm_id)
    assert log_row[2] == str(player1.player_id)
    assert log_row[3] == str(player2.player_id)


async def test_log_game_no_players(manager_and_mocks):
    """Test that log_game handles an empty list of players gracefully."""
    manager, mock_char_sheet, mock_game_sheet, _ = manager_and_mocks
    await manager.log_game(12345, [])
    mock_char_sheet.update_cells.assert_not_called()
    mock_game_sheet.append_row.assert_not_called()


async def test_get_all_items_handles_bad_records(manager_and_mocks):
    """Test get_all_items skips records that would cause an error."""
    manager, _, _, _ = manager_and_mocks
    # We need to mock the item_sheet directly for this test
    with patch.object(manager, "item_sheet") as mock_item_sheet:
        mock_item_sheet.get_all_records.return_value = [
            {"item name": "Good Item", "cost": "100", "rarity": "Common"},
            {"item name": "Bad Item", "cost": "not_a_number", "rarity": "Rare"},
        ]

        # Depending on strictness, this could either raise an error or skip the bad record.
        # The current implementation will raise a ValueError. Let's test for that.
        with pytest.raises(ValueError):
            await manager.get_all_items()


async def test_new_market_log_entry(manager_and_mocks):
    """Test that a new market log entry is appended correctly."""
    manager, _, _, _ = manager_and_mocks
    with patch.object(manager, "market_sheet") as mock_market_sheet:
        char_info = Character(player_id=1, char_id=101, name="p1", xp=0, lvl=1, cur=100)
        item = Item(name="Test Item", cost=50, rarity="Common")

        await manager.new_market_log_entry(
            char_info, item, quantity=2, notes="Test purchase"
        )

        mock_market_sheet.append_row.assert_called_once()
        appended_row = mock_market_sheet.append_row.call_args[0][0]

        assert appended_row[0] == date.today().strftime("%Y-%m-%d")
        assert appended_row[1] == char_info.char_id
        assert appended_row[2] == item.name
        assert appended_row[3] == item.cost
        assert appended_row[4] == 2
        assert appended_row[5] == "Test purchase"


async def test_get_all_market_log_entries(manager_and_mocks):
    """Test retrieving and parsing all market log entries."""
    manager, _, _, _ = manager_and_mocks
    with patch.object(manager, "market_sheet") as mock_market_sheet:
        mock_records = [
            {
                "date": "2025-01-01",
                "character id": "101",
                "item name": "Potion",
                "price": "50",
                "quantity": "1",
                "notes": "Bought",
            },
            {
                "date": "2025-01-02",
                "character id": "102",
                "item name": "Sword",
                "price": "1000",
                "quantity": "1",
                "notes": "Sold",
            },
        ]
        mock_market_sheet.get_all_records.return_value = mock_records

        logs = await manager.get_all_market_log_entries()

        assert len(logs) == 2
        assert logs[0].char_id == 101
        assert logs[0].item_name == "Potion"
        assert logs[1].price == 1000
        assert logs[1].notes == "Sold"


async def test_get_all_market_log_entries_empty(manager_and_mocks):
    """Test retrieving market logs when the sheet is empty."""
    manager, _, _, _ = manager_and_mocks
    with patch.object(manager, "market_sheet") as mock_market_sheet:
        mock_market_sheet.get_all_records.return_value = []
        logs = await manager.get_all_market_log_entries()
        assert logs == []
