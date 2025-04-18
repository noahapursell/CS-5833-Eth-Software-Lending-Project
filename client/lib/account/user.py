from web3 import Web3
from eth_account import Account
from lib.config.settings import Settings

settings = Settings()

class User:

    def __init__(self, private_key: str):
        self.account = Account.from_key(private_key)

    def get_balance(self):
        return settings.web3.eth.get_balance(self.account.address) 