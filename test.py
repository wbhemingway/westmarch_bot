from utils.sheet_manager import SheetManager

manager = SheetManager("credentials.json", "TSI 2024 WorkBook Dev")
manager.char_sheet.update_cell(3, 2, "Hello World!")
