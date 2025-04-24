from pydantic_settings import BaseSettings
from web3 import Web3, HTTPProvider
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

retry_strategy = Retry(
    total=10,              # 🔼 bump this to whatever you need
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=0.5,    # exponential sleep between tries
    allowed_methods=["POST"],  # JSON-RPC is POST
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://",  adapter)
session.mount("https://", adapter)


class Settings(BaseSettings):
    eth_network_url: str
    game_rental_contract_address: str

    class Config:
        env_file = ".env"

    @property
    def web3(self) -> Web3:
        return Web3(
            HTTPProvider(
                self.eth_network_url,
                request_kwargs={"timeout": 60},
                session=session                      # ← pass the custom session
            )
        )
