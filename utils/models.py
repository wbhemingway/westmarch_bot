from dataclasses import dataclass


@dataclass
class Character:
    player_id: int
    char_id: int
    name: str
    xp: int
    lvl: int
    cur: int

@dataclass
class Item:
    name: str
    cost: int
    rarity: str

@dataclass
class MarketLog:
    date: str
    char_id: int
    item_name: str
    price: int
    quantity: int
    notes: str
    
