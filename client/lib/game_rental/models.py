from pydantic import BaseModel

class Game(BaseModel):
    game_id: int
    developer: str
    price: int  # in wei
    default_owner_rate: int
    dev_rate: int
