import json
from web3.exceptions import ContractLogicError

from lib.config.settings import Settings
from lib.account.user import User
from lib.game_rental.models import Game, RentableGame

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
    def get_available_rentals(game: Game) -> list[RentableGame]:
        owner_addresses, owner_rates = contract.functions.getAvailableRentals(
            game.game_id).call()

        game_rentals = [
            RentableGame(
                **game.model_dump(),
                owner_rate=owner_rates[i],
                owner_address=owner_addresses[i]
            )
            for i in range(len(owner_addresses))]

        return game_rentals

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

            tx_hash = settings.web3.eth.send_raw_transaction(
                signed_txn.raw_transaction)

            print("Transaction sent")

            receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)

            return receipt

        except ContractLogicError as e:
            print(f"Contract error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    @staticmethod
    def get_user_games(user: User) -> list[Game]:
        game_ids = contract.functions.getOwnedGames(
            user.account.address).call()
        all_games = GameRental.get_buyable_games()

        return [game for game in all_games if game.game_id in game_ids]

    @staticmethod
    def get_user_rentals(user: User) -> list[RentableGame]:
        (game_ids, owner_addresses, owner_rates) = contract.functions.getCurrentRentals(
            user.account.address).call()
        all_games = GameRental.get_buyable_games()

        games = [game for game in all_games if game.game_id in game_ids]
        games_dict = {game.game_id: game for game in games}

        rentals = [
            RentableGame(
                **games_dict[game_ids[i]].model_dump(),
                owner_rate=owner_rates[i],
                owner_address=owner_addresses[i]
            )
            for i in range(len(games))]

        return rentals

    @staticmethod
    def make_game_rentable(user: User, game: Game):
        tx = contract.functions.setRentable(game.game_id, True).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address)
        })

        signed_tx = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed_tx.raw_transaction)

        receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def make_game_unrentable(user: User, game: Game):
        tx = contract.functions.setRentable(game.game_id, False).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address)
        })

        signed_tx = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed_tx.raw_transaction)

        receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def rent_game(user: User, rentable_game: RentableGame, eth_deposit_amount: int = 10):
        deposit_amount = settings.web3.to_wei(eth_deposit_amount, "ether")
        balance = user.get_balance()

        if balance < deposit_amount:
            raise Exception(
                f"Balance of {user.get_balance()} is less than deposit ammount {deposit_amount}")

        tx = contract.functions.rentGame(rentable_game.game_id, rentable_game.owner_address).build_transaction({
            'from': user.account.address,
            'value': deposit_amount,
            'nonce': settings.web3.eth.get_transaction_count(user.account.address),
            'gas': 250000,
            'gasPrice': settings.web3.to_wei('10', 'gwei')
        })

        signed_txn = user.account.sign_transaction(tx)

        tx_hash = settings.web3.eth.send_raw_transaction(
            signed_txn.raw_transaction)
        print("Rent transaction sent")

        receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def can_play(renter: User, rentable_game: RentableGame) -> bool:
        try:
            return contract.functions.canPlay(
                rentable_game.game_id,
                rentable_game.owner_address,
                renter.account.address
            ).call()
        except ContractLogicError as err:
            raise RuntimeError(f"canPlay() reverted: {err}") from err

    @staticmethod
    def stop_renting(user: User, rentable_game: RentableGame):
        tx = contract.functions.stopRenting(
            rentable_game.game_id,
            rentable_game.owner_address
        ).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 250000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed_tx = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed_tx.raw_transaction)
        receipt = settings.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def register_game(user: User, game_id: int, price_wei: int, default_owner_rate: int, dev_rate: int):
        tx = contract.functions.registerGame(
            game_id,
            price_wei,
            default_owner_rate,
            dev_rate
        ).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 300000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed.raw_transaction)
        return settings.web3.eth.wait_for_transaction_receipt(tx_hash)

    @staticmethod
    def collect_rent(user: User, rentable_game: RentableGame):
        tx = contract.functions.collectRent(
            rentable_game.game_id,
            rentable_game.owner_address
        ).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 200000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed.raw_transaction)
        return settings.web3.eth.wait_for_transaction_receipt(tx_hash)

    @staticmethod
    def deposit_funds(user: User, eth_amount: int = 1):
        wei_amount = settings.web3.to_wei(eth_amount, "ether")
        tx = contract.functions.depositFunds().build_transaction({
            "from": user.account.address,
            "value": wei_amount,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 100000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed.raw_transaction)
        return settings.web3.eth.wait_for_transaction_receipt(tx_hash)

    @staticmethod
    def withdraw_owner_payout(user: User, game_id: int):
        tx = contract.functions.withdrawOwnerPayout(game_id).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 120000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed.raw_transaction)
        return settings.web3.eth.wait_for_transaction_receipt(tx_hash)

    @staticmethod
    def withdraw_dev_payout(user: User, game_id: int):
        tx = contract.functions.withdrawDevPayout(game_id).build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 120000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed.raw_transaction)
        return settings.web3.eth.wait_for_transaction_receipt(tx_hash)

    @staticmethod
    def withdraw_renter_balance(user: User):
        tx = contract.functions.withdrawRenterBalance().build_transaction({
            "from": user.account.address,
            "nonce": settings.web3.eth.get_transaction_count(user.account.address),
            "gas": 100000,
            "gasPrice": settings.web3.to_wei("10", "gwei")
        })
        signed = user.account.sign_transaction(tx)
        tx_hash = settings.web3.eth.send_raw_transaction(
            signed.raw_transaction)
        return settings.web3.eth.wait_for_transaction_receipt(tx_hash)

    @staticmethod
    def get_game_dev_info(game_id: int) -> tuple[str, int]:
        """
        Wrapper for the `getGameDevInfo(uint256)` Solidity view.

        Parameters
        ----------
        game_id : int
            The unique game identifier.

        Returns
        -------
        tuple[str, int]
            (developer address, unpaid developer payout in wei)
        """
        developer, dev_payout = contract.functions.getGameDevInfo(
            game_id
        ).call()
        return developer, dev_payout

    @staticmethod
    def get_published_games(dev_addr: str) -> list[Game]:
        """
        Wrapper for `getPublishedGames(address)`.

        Parameters
        ----------
        dev_addr : str
            Address of the developer.

        Returns
        -------
        list[Game]
            All `Game` objects whose `developer` matches `dev_addr`.
        """
        game_ids = contract.functions.getPublishedGames(dev_addr).call()

        # Re-use the general buy-list and filter in-memory
        all_games = GameRental.get_buyable_games()
        return [g for g in all_games if g.game_id in game_ids]

    @staticmethod
    def get_dev_games_info(dev_addr: str) -> list[dict[str, int]]:
        """
        Combine `getPublishedGames` and `getGameDevInfo` to fetch payout
        information for every game a developer has registered.

        Parameters
        ----------
        dev_addr : str
            Address of the developer.

        Returns
        -------
        list[dict[str, int]]
            One dict per game, with keys:
            - "game_id"   : uint256
            - "dev_payout": wei currently owed to the developer
        """
        # All game IDs owned by this developer
        game_ids = contract.functions.getPublishedGames(dev_addr).call()

        # Gather per-game payout info
        results = []
        for gid in game_ids:
            _, dev_payout = contract.functions.getGameDevInfo(gid).call()
            results.append({
                "game_id": gid,
                "dev_payout": dev_payout
            })

        return results

    @staticmethod
    def get_owner_games_info(owner_addr: str) -> list[dict[str, int]]:
        """
        Fetch unpaid balances for every game `owner_addr` owns.

        Returns
        -------
        list[dict]
            [{ "game_id": 1, "owner_payout": 123_000_000_000_000_000 }, …]
        """
        game_ids, payouts = contract.functions.getOwnerGamesInfo(
            owner_addr
        ).call()

        return [
            {"game_id": gid, "owner_payout": payouts[i]}
            for i, gid in enumerate(game_ids)
        ]
