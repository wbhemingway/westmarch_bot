from dataclasses import dataclass

@dataclass
class character:
    player_id: int
    char_id: int
    name: str
    xp: int
    lvl: int
    cur: int
