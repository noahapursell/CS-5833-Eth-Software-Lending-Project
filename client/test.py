from lib.account.user import User

# User
user = User(private_key="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

print(f"User balance: {user.get_balance()}")


# Buy Game
from lib.game_rental.game_rental import GameRental
# # print(contract)
# print(GameRental.get_buyable_games())
games = GameRental.get_buyable_games()

# purchase = GameRental.buy_game(user=user, game=games[0])
# print(purchase)
# # GameRental.print_contract_functions()

# See Owned Games
# owned_games = GameRental.get_user_games(user=user)
# print(f"Owned Games: {owned_games}")

# Set Game as Rentable

make_rentable_receipt = GameRental.make_game_rentable(user=user, game=games[0])
print(f"{make_rentable_receipt=}")