import asyncio

from dotenv import load_dotenv

from utils.sheet_manager import SheetManager

load_dotenv()


async def test():
    manager = SheetManager("credentials.json", "TSI 2024 WorkBook Dev")
    data = await manager.get_character_information("142990967904010240")
    print(data)
    data = await manager.get_character_information("142990967904010240")
    print(data)
    await manager.set_character_currency("142990967904010240", 76)
    data = await manager.get_character_information("142990967904010240")
    print(data)


asyncio.run(test())
