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
# GameRental.print_contract_functions()

# See Owned Games
owned_games = GameRental.get_user_games(user=user)
print(f"Owned Games: {owned_games}")

# Set Game as Rentable

make_rentable_receipt = GameRental.make_game_rentable(user=user, game=games[0])
print(f"{make_rentable_receipt=}")

rentable_games = GameRental.get_available_rentals(game=games[0])
print(f"Rentable Games: {rentable_games}")


current_rentals = GameRental.get_user_rentals(user=user)
print(f"Current Rentals: {current_rentals}")

user16 = User(private_key = "0xea6c44ac03bff858b476bba40716402b03e41b8e97e276d1baec7c37d42484a0")
print()
print()
# game_rent_receipt = GameRental.rent_game(user=user16, rentable_game=rentable_games[0])
# print(f"{game_rent_receipt=}")

current_rentals = GameRental.get_user_rentals(user=user16)
print(f"User 16 rentals: {current_rentals}")


can_play = GameRental.can_play(renter=user16, rentable_game=current_rentals[0])
print(f"{can_play=}")

print(user16.get_balance())

GameRental.stop_renting(user=user16, rentable_game=current_rentals[0])

print(user16.get_balance())