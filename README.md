# Westmarch Bot

A Discord bot for managing character information and economy in a West Marches-style D&D campaign. This bot uses a Google Sheet as a lightweight database to track player characters, items, and market transactions.

## Features

The bot is designed to automate many of the bookkeeping tasks associated with a West Marches campaign.

*   **Character Management**:
    *   Create new characters for players.
    *   Track character experience (XP), level, and currency.
    *   Automatically calculates starting gold based on starting level.
*   **Item Database**:
    *   Pulls item information (name, cost, rarity) from a dedicated sheet.
*   **Economy Tracking**:
    *   Logs all item purchases to a market transaction log.

## Setup

To get the bot up and running, you will need to configure your environment and the Google Sheet that will act as the database.

### 1. Google Sheets & API

1.  **Create a Google Sheet**: Create a new Google Sheet. This will be your database.
2.  **Create Worksheets**: Inside the sheet, create three worksheets named exactly: `Characters`, `Items`, and `MarketLog`.
3.  **Set Up Headers**: Add the required column headers to the first row of each sheet.
    *   **Characters**: `player id`, `character name`, `character id`, `currency`, `experience`, `level`
    *   **Items**: `item name`, `cost`, `rarity`
    *   **MarketLog**: `date`, `character id`, `item name`, `price`, `quantity`, `notes`
4.  **Google Cloud Service Account**:
    *   Create a service account in the Google Cloud Platform console.
    *   Enable the Google Sheets API and Google Drive API for your project.
    *   Download the JSON credentials file for the service account.
    *   Share your Google Sheet with the service account's email address, giving it Editor permissions.

### 2. Bot Configuration

1.  **Clone the repository.**
2.  **Install dependencies**: `pip install -r requirements.txt` (A `requirements.txt` file should be created with libraries like `gspread`, `google-auth-oauthlib`, and `discord.py`).
3.  **Configuration**: Create a `config.py` file to store settings like your Discord bot token, starting level, and XP requirements.
4.  **Credentials**: Place your downloaded Google Cloud JSON credentials file in the project directory.

## Roadmap

Here are some of the planned features and improvements:

-   **Player Commands**:
    -   Implement a `/buy` command for players to purchase items from the `Items` sheet.
-   **DM Tools**:
    -   Create a `dm` cog with commands for managing games and awarding XP/gold.
-   **Testing**:
    -   Develop a suite of unit tests to ensure bot stability and data integrity.

