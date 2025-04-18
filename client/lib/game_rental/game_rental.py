import json
from web3.exceptions import ContractLogicError

from lib.config.settings import Settings
from lib.account.user import User
from lib.game_rental.models import Game

settings = Settings()

with open("data/GameRental.json", "r") as f:
    abi = json.load(f)['abi']

contract_address = settings.game_rental_contract_address
contract = settings.web3.eth.contract(address=contract_address, abi=abi)


class GameRental:
    @staticmethod
    def print_contract_functions():
        for fn_name in contract.functions:
            print(f"Function name: {fn_name}")

    @staticmethod
    def get_buyable_games() -> list[Game]:
        (
            game_ids,
            developers,
            prices,
            default_owner_rates,
            dev_rates
        ) = contract.functions.getBuyableGames().call()

        games = []
        for i in range(len(game_ids)):
            game = Game(
                game_id=game_ids[i],
                developer=developers[i],
                price=prices[i],
                default_owner_rate=default_owner_rates[i],
                dev_rate=dev_rates[i]
            )
            games.append(game)

        return games

    @staticmethod
    def buy_game(user: User, game: Game):
        balance = user.get_balance()

        if balance < game.price:
            raise Exception(
                f"Balance of {user.get_balance()} is less than game price {game.price}")

        try:
            txn = contract.functions.buyGame(game.game_id).build_transaction({
                'from': user.account.address,
                'value': game.price,
                'nonce': settings.web3.eth.get_transaction_count(user.account.address),
                'gas': 250000,
                'gasPrice': settings.web3.to_wei('10', 'gwei')
                
            })

            signed_txn = user.account.sign_transaction(txn)
            
            tx_hash = settings.web3.eth.send_raw_transaction(signed_txn.raw_transaction)

            print("Transaction sent")

            receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)

            return receipt

        except ContractLogicError as e:
            print(f"Contract error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    @staticmethod
    def get_user_games(user: User) -> Game:
        game_ids = contract.functions.getOwnedGames(user.account.address).call()
        all_games = GameRental.get_buyable_games()

        return [game for game in all_games if game.game_id in game_ids]

    @staticmethod
    def make_game_rentable(user: User, game: Game):
        tx = contract.functions.setRentable(game.game_id, True).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address)
        })

        signed_tx = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def make_game_unrentable(user: User, game: Game):
        tx = contract.functions.setRentable(game.game_id, False).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address)
        })

        signed_tx = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt



    