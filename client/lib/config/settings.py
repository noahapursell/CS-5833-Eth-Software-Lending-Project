from pydantic_settings import BaseSettings
from web3 import Web3

class Settings(BaseSettings):
    eth_network_url: str
    game_rental_contract_address: str

    class Config:
        env_file= ".env"

    @property
    def web3(self) -> Web3:
       return Web3(Web3.HTTPProvider(self.eth_network_url))