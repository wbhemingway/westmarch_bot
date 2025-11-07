from unittest.mock import MagicMock, patch

import pytest

import config
from utils.exceptions import CharacterAlreadyExists, CharacterNotFound
from utils.sheet_manager import SheetManager


@pytest.fixture
async def manager_and_mocks():
    """Pytest fixture to set up a SheetManager with mocked dependencies."""
    with (
        patch("utils.sheet_manager.Credentials") as mock_credentials,
        patch("utils.sheet_manager.gspread") as mock_gspread,
    ):
        mock_credentials.from_service_account_file.return_value = MagicMock()

        manager = SheetManager("fake_creds.json", "fake_sheet")

        mock_worksheet = MagicMock()
        mock_workbook = MagicMock()
        mock_workbook.worksheet.return_value = mock_worksheet
        mock_client = MagicMock()
        mock_client.open.return_value = mock_workbook
        mock_gspread.authorize.return_value = mock_client

        mock_headers = [
            manager.C_H_PLAYER_ID,
            manager.C_H_CHAR_NAME,
            manager.C_H_CHAR_ID,
            manager.C_H_CURRENCY,
            manager.C_H_XP,
            manager.C_H_LEVEL,
        ]
        mock_worksheet.row_values.return_value = mock_headers

        await manager._connect()

        yield manager, mock_worksheet


async def test_connect_success(manager_and_mocks):
    """Test that _connect correctly populates column indexes."""
    manager, _ = manager_and_mocks
    assert manager.c_player_id == 1
    assert manager.c_char_name == 2
    assert manager.c_char_id == 3
    assert manager.c_currency == 4
    assert manager.c_xp == 5
    assert manager.c_level == 6


@pytest.mark.parametrize(
    "level, expected_gold",
    [
        (3, 0),
        (5, config.GP_PER_GAME_T1 * 2),
        (9, (config.GP_PER_GAME_T1 * 2) + (config.GP_PER_GAME_T2 * 4)),
    ],
)
async def test_get_starting_gold(manager_and_mocks, level, expected_gold):
    """Test the starting gold calculation for different levels."""
    manager, _ = manager_and_mocks
    gold = await manager._get_starting_gold(level)
    assert gold == expected_gold


async def test_get_character_information_success(manager_and_mocks):
    """Test successfully retrieving character information."""
    manager, mock_worksheet = manager_and_mocks
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
    manager, mock_worksheet = manager_and_mocks
    mock_worksheet.get_all_records.return_value = []

    with pytest.raises(CharacterNotFound):
        await manager.get_character_information(99999)


async def test_set_character_currency_success(manager_and_mocks):
    """Test successfully updating a character's currency."""
    manager, mock_worksheet = manager_and_mocks
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
    manager, mock_worksheet = manager_and_mocks
    mock_worksheet.get_all_records.return_value = []

    with pytest.raises(CharacterNotFound):
        await manager.set_character_currency(99999, 500)


async def test_create_new_character_success(manager_and_mocks):
    """Test the successful creation of a new character."""
    manager, mock_worksheet = manager_and_mocks
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
    expected_gold = await manager._get_starting_gold(start_lvl)

    assert appended_row[0] == new_char_name
    assert appended_row[1] == str(new_player_id)
    assert appended_row[3] == str(expected_gold)
    assert appended_row[4] == str(expected_xp)
    assert appended_row[5] == str(start_lvl)


async def test_create_new_character_already_exists(manager_and_mocks):
    """Test that creating a duplicate character raises CharacterAlreadyExists."""
    manager, mock_worksheet = manager_and_mocks
    player_id = 12345
    mock_worksheet.get_all_records.return_value = [
        {manager.C_H_PLAYER_ID: str(player_id), manager.C_H_CHAR_NAME: "Old Name"}
    ]

    with pytest.raises(CharacterAlreadyExists):
        await manager.create_new_character("Another Name", player_id, 5)
