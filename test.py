import asyncio

from utils.sheet_manager import SheetManager


async def test():
    manager = SheetManager("credentials.json", "TSI 2024 WorkBook Dev")
    data = await manager.get_character_information("1")
    print(data)


asyncio.run(test())
