# Westmarch Bot

A Discord bot for managing character information and economy in a West Marches-style D&D campaign. This bot uses a Google Sheet as a lightweight database to track player characters, items, and market transactions.

## Features

The bot is designed to automate many of the bookkeeping tasks associated with a West Marches campaign.

*   **Character Management**:
    *   Create new characters for players.
    *   Track character experience (XP), level, and currency.
    *   Automatically calculates starting gold based on starting level.
    *   Allows players to purchase items with a `/buy` command.
*   **Item Database**:
    *   Pulls item information (name, cost, rarity) from a dedicated sheet.
*   **DM Tools**:
    *   Log games to automatically award XP and gold to participating players.
    *   Maintains a `GameLog` sheet to track which players participated in each game.
*   **Economy Tracking**:
    *   Logs all item purchases to a market transaction log.

## Setup

To get the bot up and running, you will need to configure your environment and the Google Sheet that will act as the database. The tests are also fully configured and can be run with `pytest`.

### 1. Google Sheets & API

1.  **Create a Google Sheet**: Create a new Google Sheet. This will be your database.
2.  **Create Worksheets**: Inside the sheet, create four worksheets named exactly: `Characters`, `Items`, `MarketLog`, and `GameLog`.
3.  **Set Up Headers**: Add the required column headers to the first row of each sheet.
    *   **Characters**: `player id`, `character name`, `character id`, `currency`, `experience`, `level`
    *   **Items**: `item name`, `cost`, `rarity`
    *   **MarketLog**: `date`, `character id`, `item name`, `price`, `quantity`, `notes`
    *   **GameLog**: `date`, `dm id`, `p1 id`, `p2 id`, `p3 id`, `p4 id`, `p5 id`, `p6 id`
4.  **Google Cloud Service Account**:
    *   Create a service account in the Google Cloud Platform console.
    *   Enable the Google Sheets API and Google Drive API for your project.
    *   Download the JSON credentials file for the service account.
    *   Share your Google Sheet with the service account's email address, giving it Editor permissions.

### 2. Bot Configuration

1.  **Clone the repository.**
2.  **Install dependencies**: `pip install -r requirements.txt` (A `requirements.txt` file should be created with libraries like `gspread`, `google-auth-oauthlib`, and `discord.py`).
    *   *Note: Faster package managers like `uv` can also be used (`uv pip install -r requirements.txt`).*
3.  **Environment File**: Create a `.env` file in the root directory and add your Discord bot token to it: `DISCORD_BOT_TOKEN="your_token_here"`.
4.  **Configuration**: Open the `config.py` file and update it with your server-specific values, such as `GOOGLE_SHEET_NAME`, role IDs, and any future channel IDs.
5.  **Credentials**: Place your downloaded Google Cloud JSON credentials file in the project directory and ensure its name matches the `CREDENTIALS_FILE` variable in `config.py`.

## Roadmap

Here are some of the planned features and improvements for the bot:

*   **Player-Facing Commands**:
    *   `/pricecheck <items...>`: A command for players to quickly check the total price of a group of items. This helps them manage their inventory's total gold value against server-imposed limits for games.

*   **Scribe & Economy Features**:
    *   **Player Inventories**: Implement a system to track which items each player owns.
    *   `/sell <player> <item>`: A command for Scribes to sell an item from a player's inventory, updating their currency and logging the transaction in the `MarketLog`.
    *   `/check_inventory <player>`: A command for Scribes to view a player's current item inventory.

*   **Discord Integration & Logging**:
    *   **Game Completion Posts**: Automatically post a summary message to a designated channel when a DM uses the `/log_game` command.
    *   **Audit Channel**: Post logs of command usage to a private channel for server moderation and debugging purposes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
