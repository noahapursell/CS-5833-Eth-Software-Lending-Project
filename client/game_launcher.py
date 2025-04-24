import sys
import time
from typing import List, Tuple

import typer
from rich import print
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from web3 import Web3

from lib.account.user import User
from lib.game_rental.game_rental import GameRental
from lib.game_rental.models import Game, RentableGame

app = typer.Typer(
    help="CLI that talks directly to the on‑chain GameRental smart‑contract."
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────


def to_eth(wei: int) -> str:
    """Convert wei → ETH (4‑decimal string)."""
    return f"{Web3.from_wei(wei, 'ether'):.4f} ETH"


def select_from_table(header: str, rows: List[Tuple[str, ...]]) -> int:
    """
    Render a Rich table, return the zero‑based index of the selected row.
    Returns –1 when the user cancels.
    """
    if not rows:
        return -1

    table = Table(title=header)
    table.add_column("#")
    for _ in rows[0]:
        table.add_column()

    for idx, row in enumerate(rows, 1):
        table.add_row(str(idx), *map(str, row))

    print(table)
    try:
        choice = IntPrompt.ask("Pick a number (0 to cancel)")
        return choice - 1 if 0 < choice <= len(rows) else -1
    except (ValueError, typer.Abort):
        return -1

# ─────────────────────────────────────────────────────────────────────────────
# Developer: publish a new game
# ─────────────────────────────────────────────────────────────────────────────


def publish_game(user: User):
    """Register a brand‑new game on‑chain (developer action)."""
    try:
        game_id = IntPrompt.ask("Game ID (integer)")
        price_eth = float(Prompt.ask("Purchase price (ETH)"))
        default_owner_rate = int(
            Prompt.ask("Default owner rate (wei/min)",
                       default="100000000000000")
        )
        dev_rate = int(
            Prompt.ask("Developer rental rate (wei/min)",
                       default="100000000000000")
        )
    except (ValueError, typer.Abort):
        print("[yellow]Cancelled.[/yellow]")
        return

    print(
        f"\nSummary:\n  Game ID: {game_id}\n  Price: {price_eth} ETH\n"
        f"  Default owner rate: {default_owner_rate} wei/min\n"
        f"  Dev rate: {dev_rate} wei/min"
    )
    if not Confirm.ask("Publish this game?"):
        print("[yellow]Publish cancelled.[/yellow]")
        return

    try:
        receipt = GameRental.register_game(
            user,
            game_id=game_id,
            price_wei=Web3.to_wei(price_eth, "ether"),
            default_owner_rate=default_owner_rate,
            dev_rate=dev_rate,
        )
        print(
            f"[green]Game published. TX: {receipt.transactionHash.hex()}[/green]")
    except Exception as exc:
        print(f"[red]Publish failed: {exc}[/red]")

# ─────────────────────────────────────────────────────────────────────────────
# View library
# ─────────────────────────────────────────────────────────────────────────────


def show_library(user: User):
    owned = GameRental.get_user_games(user)
    rentals = GameRental.get_user_rentals(user)

    if not owned and not rentals:
        print("[yellow]Your library is empty.[/yellow]")
        return

    if owned:
        table = Table(title="Owned games")
        table.add_column("Game ID")
        table.add_column("Purchase price")
        table.add_column("Default owner rate (wei/min)")
        for g in owned:
            table.add_row(str(g.game_id), to_eth(
                g.price), str(g.default_owner_rate))
        print(table)

    if rentals:
        table = Table(title="Active rentals")
        table.add_column("Game ID")
        table.add_column("Owner")
        table.add_column("Rate (wei/min)")
        for r in rentals:
            table.add_row(str(r.game_id), r.owner_address, str(r.owner_rate))
        print(table)

# ─────────────────────────────────────────────────────────────────────────────
# Owner: advertise / stop advertising
# ─────────────────────────────────────────────────────────────────────────────


def advertise(user: User, make_rentable: bool):
    owned = GameRental.get_user_games(user)
    if not owned:
        print("[yellow]You do not own any games.[/yellow]")
        return

    idx = select_from_table(
        "Select one of your games", [
            (g.game_id, to_eth(g.price)) for g in owned]
    )
    if idx == -1:
        return

    game = owned[idx]
    if make_rentable:
        receipt = GameRental.make_game_rentable(user, game)
        state = "rentable"
    else:
        receipt = GameRental.make_game_unrentable(user, game)
        state = "NOT rentable"

    print(
        f"[green]Game {game.game_id} is now {state}. "
        f"TX: {receipt.transactionHash.hex()}[/green]"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Browse & BUY
# ─────────────────────────────────────────────────────────────────────────────


def browse_buyable_games(user: User) -> List[Game]:
    all_games = GameRental.get_buyable_games()
    owned_ids = {g.game_id for g in GameRental.get_user_games(user)}
    listings = [g for g in all_games if g.game_id not in owned_ids]

    if not listings:
        print("[yellow]No games available for purchase.[/yellow]")
        return []

    table = Table(title="Games available to buy")
    table.add_column("#")
    table.add_column("Game ID")
    table.add_column("Price (ETH)")
    table.add_column("Developer")
    for i, g in enumerate(listings, 1):
        table.add_row(str(i), str(g.game_id), to_eth(g.price), g.developer)
    print(table)
    return listings


def purchase_game(user: User):
    options = browse_buyable_games(user)
    if not options:
        return

    idx = select_from_table(
        "Select a game to purchase", [(o.game_id,) for o in options]
    )
    if idx == -1:
        return

    game = options[idx]
    print(f"Selected game {game.game_id} for {to_eth(game.price)}")
    if not Confirm.ask("Proceed with purchase?"):
        print("[yellow]Purchase cancelled.[/yellow]")
        return

    try:
        receipt = GameRental.buy_game(user, game)
        print(
            f"[green]Purchase successful. TX: {receipt.transactionHash.hex()}[/green]")
    except Exception as exc:
        print(f"[red]Purchase failed: {exc}[/red]")

# ─────────────────────────────────────────────────────────────────────────────
# Renting
# ─────────────────────────────────────────────────────────────────────────────


def browse_rentals(user: User) -> List[RentableGame]:
    listings: List[RentableGame] = []
    for g in GameRental.get_buyable_games():
        for r in GameRental.get_available_rentals(g):
            if r.owner_address.lower() != user.account.address.lower():
                listings.append(r)

    if not listings:
        print("[yellow]No games available to rent.[/yellow]")
        return []

    table = Table(title="Games available to rent")
    table.add_column("#")
    table.add_column("Game ID")
    table.add_column("Owner")
    table.add_column("Rate (wei/min)")
    for i, r in enumerate(listings, 1):
        table.add_row(str(i), str(r.game_id),
                      r.owner_address, str(r.owner_rate))
    print(table)
    return listings


def rent_game(user: User):
    options = browse_rentals(user)
    if not options:
        return
    idx = select_from_table(
        "Select a game to rent", [(r.game_id, r.owner_address)
                                  for r in options]
    )
    if idx == -1:
        return
    rentable = options[idx]
    eth = float(Prompt.ask("Deposit amount in ETH", default="0.1"))
    receipt = GameRental.rent_game(user, rentable, eth_deposit_amount=eth)
    print(
        f"[green]Rental started. TX: {receipt.transactionHash.hex()}[/green]")


def stop_rental(user: User):
    active = GameRental.get_user_rentals(user)
    if not active:
        print("[yellow]You have no active rentals.[/yellow]")
        return
    idx = select_from_table(
        "Select rental to stop", [(r.game_id, r.owner_address) for r in active]
    )
    if idx == -1:
        return
    receipt = GameRental.stop_renting(user, active[idx])
    print(
        f"[green]Rental stopped. TX: {receipt.transactionHash.hex()}[/green]")

# ─────────────────────────────────────────────────────────────────────────────
# Play
# ─────────────────────────────────────────────────────────────────────────────


def play_game(user: User):
    owned = GameRental.get_user_games(user)
    rentals = [
        r for r in GameRental.get_user_rentals(user) if GameRental.can_play(user, r)
    ]
    selectable: List[Tuple[str, Game | RentableGame]] = [
        (f"Owned {g.game_id}", g) for g in owned
    ] + [(f"Rental {r.game_id}", r) for r in rentals]

    if not selectable:
        print("[yellow]No games you can play right now.[/yellow]")
        return

    idx = select_from_table("Select a game", [lbl for lbl, _ in selectable])
    if idx == -1:
        return
    label, _ = selectable[idx]
    print(f"[blue]Launching {label}… (Ctrl‑C to quit)[/blue]")
    try:
        while True:
            time.sleep(1)
            if idx < len(owned):
                print(f"[blue] You are game owner [/blue]")
            else:
                renting_index = idx - len(owned)
                can_play = GameRental.can_play(
                    renter=user, rentable_game=rentals[renting_index])
                print(f"[red]Renting... Can Play: {can_play} [/red]")
                if not can_play:
                    break
            print(f"Playing Game {label} ... (Ctrl-C to quit)")
    except KeyboardInterrupt:
        print("[yellow]Exited game.[/yellow]")

# ─────────────────────────────────────────────────────────────────────────────
# Funds
# ─────────────────────────────────────────────────────────────────────────────


def deposit(user: User):
    eth = float(Prompt.ask("Amount in ETH", default="0.1"))
    receipt = GameRental.deposit_funds(user, eth)
    print(
        f"[green]Deposited {eth} ETH. TX: {receipt.transactionHash.hex()}[/green]")


def withdraw(user: User):
    receipt = GameRental.withdraw_renter_balance(user)
    print(
        f"[green]Withdrew renter balance. TX: {receipt.transactionHash.hex()}[/green]")

# ─────────────────────────────────────────────────────────────────────────────
# Owner Dashboard
# ─────────────────────────────────────────────────────────────────────────────


def get_owner_rentals(user: User) -> List[Tuple[int, int, str]]:
    """
    Returns all of the user's rentable games.
    Output: List of (game_id, owner_rate, owner_address)
    """
    rentals = []
    owned_games = GameRental.get_user_games(user)
    for game in owned_games:
        available = GameRental.get_available_rentals(game)
        for listing in available:
            if listing.owner_address.lower() == user.account.address.lower():
                rentals.append(
                    (listing.game_id, listing.owner_rate, listing.owner_address))
    return rentals


def collect_rent_for_all_games(user: User):
    """Collect rent for all active rentals of the user's owned games."""
    owned_games = GameRental.get_user_games(user)
    for game in owned_games:
        try:
            receipt = GameRental.collect_rent(
                user, game.game_id, user.account.address)
            if receipt:
                print(
                    f"[green]Collected rent for game {game.game_id}. "
                    f"TX: {receipt.transactionHash.hex()}[/green]"
                )
        except Exception as exc:
            print(
                f"[red]Failed to collect rent for game {game.game_id}: {exc}[/red]")


def create_dashboard_table(rentals: List[Tuple[int, int, str]]) -> Table:
    table = Table(title="Owner Dashboard - Rentable Listings")
    table.add_column("Game ID")
    table.add_column("Rate (wei/min)")
    table.add_column("Owner Address")

    for game_id, owner_rate, owner_address in rentals:
        table.add_row(str(game_id), str(owner_rate), owner_address)
    return table


def owner_dashboard_menu(user: User):
    auto_collect = Confirm.ask(
        "Enable auto rent collection every 10 minutes?", default=False)
    last_collection = time.time()

    while True:
        print("\n[yellow]=== Owner Dashboard ===[/yellow]")
        print("[1] View active rentable listings")
        print("[2] Manually collect rent from all games")
        print("[3] Withdraw owner payout for a game")
        print("[4] End Rental")
        print("[5] View games that own me money")
        print("[0] Exit dashboard")

        if auto_collect and (time.time() - last_collection) >= 600:
            print("[blue]Auto-collecting rent...[/blue]")
            owned_games = GameRental.get_user_games(user)
            for game in owned_games:
                try:
                    receipt = GameRental.collect_rent(user, RentableGame(
                        **game.model_dump(),
                        owner_address=user.account.address,
                        owner_rate=game.default_owner_rate
                    ))
                    print(
                        f"[green]Auto-collected rent for Game {game.game_id}. TX: {receipt.transactionHash.hex()}[/green]")
                except Exception as exc:
                    print(
                        f"[red]Auto-collect failed for Game {game.game_id}: {exc}[/red]")
            last_collection = time.time()

        choice = Prompt.ask("Choose an option").strip()
        if choice == "0":
            print("[yellow]Exiting owner dashboard.[/yellow]")
            break

        elif choice == "1":
            rentals = get_owner_rentals(user)
            if rentals:
                print(create_dashboard_table(rentals))
            else:
                print("[yellow]You have no games listed for rent.[/yellow]")

        elif choice == "2":
            owned_games = GameRental.get_user_games(user)
            for game in owned_games:
                try:
                    receipt = GameRental.collect_rent(user, RentableGame(
                        **game.model_dump(),
                        owner_address=user.account.address,
                        owner_rate=game.default_owner_rate
                    ))
                    print(
                        f"[green]Collected rent for Game {game.game_id}. TX: {receipt.transactionHash.hex()}[/green]")
                except Exception as exc:
                    print(
                        f"[red]Failed to collect rent for Game {game.game_id}: {exc}[/red]")

        elif choice == "3":
            games = GameRental.get_user_games(user)
            if not games:
                print("[yellow]You don't own any games.[/yellow]")
                continue
            idx = select_from_table("Select a game to withdraw payout", [
                                    (g.game_id,) for g in games])
            if idx == -1:
                continue
            try:
                receipt = GameRental.withdraw_owner_payout(
                    user, games[idx].game_id)
                print(
                    f"[green]Withdrew payout for Game {games[idx].game_id}. TX: {receipt.transactionHash.hex()}[/green]")
            except Exception as exc:
                print(f"[red]Withdraw failed: {exc}[/red]")

        elif choice == "4":
            games = GameRental.get_user_games(user=user)
            if not games:
                print("[yello]You don't own any games.[/yellow]")
                continue
            idx = select_from_table(header="Select a game to stop renting", rows=[
                                    (g.game_id, ) for g in games])
            if idx == -1:
                continue
            try:
                receipt = GameRental.stop_renting(user=user, rentable_game=RentableGame(
                    **games[idx].model_dump(),
                    owner_address=user.account.address,
                    owner_rate=games[idx].default_owner_rate
                ))

                print(
                    f"[green]Stopping rental {games[idx].game_id}. TX: {receipt.transactionHash.hex()}[/green]")
            except Exception as exc:
                print(f"[red]Withdraw failed: {exc}[/red]")
        elif choice == "5":
            def create_owner_table(info: list[dict]) -> Table:
                table = Table(title="Owner – unpaid balances")
                table.add_column("Game ID")
                table.add_column("Unpaid balance")
                for item in info:
                    table.add_row(str(item["game_id"]),
                                  to_eth(item["owner_payout"]))
                return table
            owing = GameRental.get_owner_games_info(user.account.address)
            owing = [o for o in owing if o["owner_payout"] > 0]
            if owing:
                print(create_owner_table(owing))
            else:
                print(
                    "[green]No outstanding balances – everything collected.[/green]")
            continue
        else:
            print("[red]Invalid selection.[/red]")
# ─────────────────────────────────────────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def cli():
    """Launch the interactive GameRental shell."""
    pk = Prompt.ask("Enter your Ethereum private key", password=True).strip()
    try:
        user = User(pk)
    except Exception as e:
        print(f"[red]Invalid private key: {e}[/red]")
        raise typer.Exit()

    print(f"Logged in as [green]{user.account.address}[/green]")

    menu = {
        "1": ("Publish a new game", lambda: publish_game(user)),
        "2": ("View my game library", lambda: show_library(user)),
        "3": ("Advertise one of my games for rent", lambda: advertise(user, True)),
        "4": ("Remove a game from rent", lambda: advertise(user, False)),
        "5": ("Browse games available to BUY", lambda: browse_buyable_games(user)),
        "6": ("Purchase a game", lambda: purchase_game(user)),
        "7": ("Browse games available to rent", lambda: browse_rentals(user)),
        "8": ("Rent a game", lambda: rent_game(user)),
        "9": ("Stop one of my rentals", lambda: stop_rental(user)),
        "10": ("Launch / play a game", lambda: play_game(user)),
        "11": ("Deposit funds", lambda: deposit(user)),
        "12": ("Withdraw unused deposit", lambda: withdraw(user)),
        "13": ("View owner dashboard", lambda: owner_dashboard_menu(user)),
        "14": ("View developer dashboard", lambda: developer_dashboard_menu(user)),
        "0": ("Exit", None),
    }

    while True:
        print("\n[yellow]=== Main menu ===[/yellow]")
        for key, (title, _) in menu.items():
            print(f"[{key}] {title}")
        choice = Prompt.ask("Select option").strip()

        if choice == "0":
            print("Good‑bye!")
            sys.exit(0)

        if choice not in menu:
            print("[red]Invalid selection.[/red]")
            continue

        try:
            menu[choice][1]()
        except Exception as exc:
            print(f"[red]Error: {exc}[/red]")
            time.sleep(1)


# ─────────────────────────────────────────────────────────────────────────────
# Developer dashboard (for the account that *published* games)
# ─────────────────────────────────────────────────────────────────────────────

def create_dev_table(payouts: list[dict]) -> Table:
    """Pretty table for unpaid developer balances."""
    table = Table(title="Developer – unpaid balances")
    table.add_column("Game ID")
    table.add_column("Unpaid balance")
    for item in payouts:
        table.add_row(str(item["game_id"]), to_eth(item["dev_payout"]))
    return table


def developer_dashboard_menu(user: User):
    """
    Interactive dashboard for a developer (publisher).

    • [1] lists every game the caller published and how much is still owed  
    • [2] lets the dev withdraw the unpaid balance for one of the games
    """
    while True:
        print("\n[yellow]=== Developer Dashboard ===[/yellow]")
        print("[1] View games that owe me money")
        print("[2] Withdraw payout for a game")
        print("[0] Exit dashboard")

        choice = Prompt.ask("Choose an option").strip()
        if choice == "0":
            print("[yellow]Exiting developer dashboard.[/yellow]")
            break

        elif choice == "1":          # ─── list unpaid balances ───
            payouts = GameRental.get_dev_games_info(user.account.address)
            if not payouts:
                print("[yellow]You have not published any games.[/yellow]")
                continue

            owing = [p for p in payouts if p["dev_payout"] > 0]
            if owing:
                print(create_dev_table(owing))
            else:
                print("[green]All caught up — no outstanding balances.[/green]")

        elif choice == "2":          # ─── withdraw for a single game ───
            payouts = GameRental.get_dev_games_info(user.account.address)
            owing = [p for p in payouts if p["dev_payout"] > 0]
            if not owing:
                print("[yellow]No games currently owe you money.[/yellow]")
                continue

            idx = select_from_table(
                "Select a game to withdraw payout",
                [(p["game_id"], to_eth(p["dev_payout"])) for p in owing],
            )
            if idx == -1:
                continue

            game_id = owing[idx]["game_id"]
            try:
                receipt = GameRental.withdraw_dev_payout(user, game_id)
                print(
                    f"[green]Withdrew payout for Game {game_id}. "
                    f"TX: {receipt.transactionHash.hex()}[/green]"
                )
            except Exception as exc:
                print(f"[red]Withdraw failed: {exc}[/red]")

        else:
            print("[red]Invalid selection.[/red]")


if __name__ == "__main__":
    app()
