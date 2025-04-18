import typer
import json
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style, init
import time
import sys
import os

# Initialize colorama for cross-platform color support
init(autoreset=True)

app = typer.Typer()

# Path to the JSON file for persistent data
DATA_FILE = Path("game_data.json")

def load_data():
    """Load game library and lending records from the JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"games": [], "lending_records": []}

def save_data(data):
    """Save game library and lending records to the JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_game_lent(game_name, owner, data):
    """Check if a specific game owned by a user is currently lent."""
    return any(r["game_name"] == game_name and r["owner"] == owner and r["end_time"] is None for r in data["lending_records"])

def view_game_library(data, username):
    """View the user's game library, including owned and borrowed games."""
    # Get owned games
    owned_games = [g for g in data["games"] if g["owner"] == username]
    # Get borrowed games (active lending records where user is the borrower)
    borrowed_records = [r for r in data["lending_records"] if r["borrower"] == username and r["end_time"] is None]
    
    print(f"\n{Fore.BLUE}{Style.BRIGHT}=== Your Game Library ==={Style.RESET_ALL}")
    
    # Display owned games
    if owned_games:
        print(f"{Fore.CYAN}Owned Games:{Style.RESET_ALL}")
        for game in owned_games:
            # Check if the owned game is currently lent out
            active_lending = next((r for r in data["lending_records"] if r["game_name"] == game["name"] and r["owner"] == username and r["end_time"] is None), None)
            lending_status = f"{Fore.YELLOW} (Currently Lent to {active_lending['borrower']}){Style.RESET_ALL}" if active_lending else ""
            status = f"{Fore.GREEN}Lendable at {game['lending_rate_percent']}%/day{Style.RESET_ALL}" if game["lendable"] else f"{Fore.RED}Not lendable{Style.RESET_ALL}"
            print(f"- {game['name']:<20} | {game['original_price_eth']} ETH | {status}{lending_status}")
    
    # Display borrowed games
    if borrowed_records:
        print(f"{Fore.CYAN}Borrowed Games:{Style.RESET_ALL}")
        for record in borrowed_records:
            print(f"- {record['game_name']:<20} | Borrowed from {record['owner']}")
    
    if not owned_games and not borrowed_records:
        print(f"{Fore.YELLOW}Your library is empty.{Style.RESET_ALL}")

def advertise_game(data, username):
    """Advertise a game as lendable by setting a lending rate."""
    owned_games = [g for g in data["games"] if g["owner"] == username and not g["lendable"]]
    if not owned_games:
        print(f"{Fore.YELLOW}You have no games to advertise.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}Select a game to advertise as lendable:{Style.RESET_ALL}")
    for i, game in enumerate(owned_games, 1):
        print(f"{Fore.GREEN}[{i}] {game['name']} ({game['original_price_eth']} ETH){Style.RESET_ALL}")
    while True:
        try:
            choice = int(input(f"{Fore.CYAN}Enter the number: {Style.RESET_ALL}")) - 1
            if 0 <= choice < len(owned_games):
                selected_game = owned_games[choice]
                rate = float(input(f"{Fore.CYAN}Enter lending rate (% of original price per day): {Style.RESET_ALL}"))
                selected_game["lendable"] = True
                selected_game["lending_rate_percent"] = rate
                save_data(data)
                daily_rate = (rate / 100) * selected_game["original_price_eth"]
                print(f"{Fore.GREEN}Advertised {selected_game['name']} at {rate}% per day ({daily_rate} ETH/day).{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")

def stop_advertising_game(data, username):
    """Stop advertising a game as lendable."""
    lendable_games = [g for g in data["games"] if g["owner"] == username and g["lendable"]]
    if not lendable_games:
        print(f"{Fore.YELLOW}You have no games advertised as lendable.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}Select a game to stop advertising:{Style.RESET_ALL}")
    for i, game in enumerate(lendable_games, 1):
        print(f"{Fore.GREEN}[{i}] {game['name']}{Style.RESET_ALL}")
    while True:
        try:
            choice = int(input(f"{Fore.CYAN}Enter the number: {Style.RESET_ALL}")) - 1
            if 0 <= choice < len(lendable_games):
                selected_game = lendable_games[choice]
                selected_game["lendable"] = False
                selected_game["lending_rate_percent"] = None
                save_data(data)
                print(f"{Fore.GREEN}Stopped advertising {selected_game['name']} as lendable.{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")

def browse_lendable_games(data, username):
    """Browse all lendable games that are not owned by the user and not currently lent."""
    lendable_games = [g for g in data["games"] if g["lendable"] and not is_game_lent(g["name"], g["owner"], data) and g["owner"] != username]
    if not lendable_games:
        print(f"{Fore.YELLOW}No lendable games available.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.BLUE}{Style.BRIGHT}=== Lendable Games ==={Style.RESET_ALL}")
    for game in lendable_games:
        daily_rate = (game["lending_rate_percent"] / 100) * game["original_price_eth"]
        print(f"{Fore.GREEN}- {game['name']:<20} | Owner: {game['owner']:<10} | {game['lending_rate_percent']}% of {game['original_price_eth']} ETH/day = {daily_rate} ETH/day{Style.RESET_ALL}")

def request_lend_game(data, username):
    """Request to lend a game from the list of lendable games (excluding own games)."""
    lendable_games = [g for g in data["games"] if g["lendable"] and not is_game_lent(g["name"], g["owner"], data) and g["owner"] != username]
    if not lendable_games:
        print(f"{Fore.YELLOW}No lendable games available.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}Select a game to lend:{Style.RESET_ALL}")
    for i, game in enumerate(lendable_games, 1):
        daily_rate = (game["lending_rate_percent"] / 100) * game["original_price_eth"]
        print(f"{Fore.GREEN}[{i}] {game['name']} (Owner: {game['owner']}), {daily_rate} ETH/day{Style.RESET_ALL}")
    while True:
        try:
            choice = int(input(f"{Fore.CYAN}Enter the number: {Style.RESET_ALL}")) - 1
            if 0 <= choice < len(lendable_games):
                selected_game = lendable_games[choice]
                lending_record = {
                    "game_name": selected_game["name"],
                    "owner": selected_game["owner"],
                    "borrower": username,
                    "start_time": datetime.now().isoformat(),
                    "end_time": None,
                    "lending_rate_percent": selected_game["lending_rate_percent"]
                }
                data["lending_records"].append(lending_record)
                save_data(data)
                print(f"{Fore.GREEN}Started lending {selected_game['name']} from {selected_game['owner']}.{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")

def end_my_lending(data, username):
    """End a lending for a game the user is currently borrowing."""
    current_lendings = [r for r in data["lending_records"] if r["borrower"] == username and r["end_time"] is None]
    if not current_lendings:
        print(f"{Fore.YELLOW}You are not currently lending any games.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}Select a lending to end:{Style.RESET_ALL}")
    for i, record in enumerate(current_lendings, 1):
        print(f"{Fore.GREEN}[{i}] {record['game_name']} (Owner: {record['owner']}){Style.RESET_ALL}")
    while True:
        try:
            choice = int(input(f"{Fore.CYAN}Enter the number: {Style.RESET_ALL}")) - 1
            if 0 <= choice < len(current_lendings):
                selected_record = current_lendings[choice]
                selected_record["end_time"] = datetime.now().isoformat()
                save_data(data)
                print(f"{Fore.GREEN}Ended lending {selected_record['game_name']}.{Style.RESET_ALL}")
                break
            else:
                print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")

def view_dashboard(data, username):
    """View the lending records for the user's games and their own borrowings."""
    print(f"\n{Fore.BLUE}{Style.BRIGHT}=== Dashboard ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}Your Lending Records (games you own that are lent):{Style.RESET_ALL}")
    owned_lendings = [r for r in data["lending_records"] if r["owner"] == username]
    if owned_lendings:
        for record in owned_lendings:
            status = f"{Fore.RED}Ended at {record['end_time']}{Style.RESET_ALL}" if record["end_time"] else f"{Fore.GREEN}Active{Style.RESET_ALL}"
            print(f"- {record['game_name']:<20} | Borrower: {record['borrower']:<10} | Start: {record['start_time']:<25} | {status}")
    else:
        print(f"{Fore.YELLOW}No lending records for your games.{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Your Borrowing Records:{Style.RESET_ALL}")
    borrowed_lendings = [r for r in data["lending_records"] if r["borrower"] == username]
    if borrowed_lendings:
        for record in borrowed_lendings:
            status = f"{Fore.RED}Ended at {record['end_time']}{Style.RESET_ALL}" if record["end_time"] else f"{Fore.GREEN}Active{Style.RESET_ALL}"
            print(f"- {record['game_name']:<20} | Owner: {record['owner']:<10} | Start: {record['start_time']:<25} | {status}")
    else:
        print(f"{Fore.YELLOW}No borrowing records.{Style.RESET_ALL}")

def launch_game(data, username):
    """Launch a game with a terminal animation and allow returning to menu by typing 'exit'."""
    # Get games that the user can play (owned or currently borrowed)
    owned_games = [g for g in data["games"] if g["owner"] == username]
    borrowed_records = [r for r in data["lending_records"] if r["borrower"] == username and r["end_time"] is None]
    playable_games = owned_games + [g for g in data["games"] if any(r["game_name"] == g["name"] and r["owner"] == g["owner"] for r in borrowed_records)]
    
    if not playable_games:
        print(f"{Fore.YELLOW}You have no games to launch.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}Select a game to launch:{Style.RESET_ALL}")
    for i, game in enumerate(playable_games, 1):
        print(f"{Fore.GREEN}[{i}] {game['name']}{Style.RESET_ALL}")
    
    while True:
        try:
            choice = int(input(f"{Fore.CYAN}Enter the number: {Style.RESET_ALL}")) - 1
            if 0 <= choice < len(playable_games):
                selected_game = playable_games[choice]
                break
            else:
                print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
    
    # Clear the screen for animation
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Simple loading animation
    animation = ['|', '/', '-', '\\']
    print(f"{Fore.BLUE}Launching {selected_game['name']}...{Style.RESET_ALL}")
    for _ in range(20):  # Run animation for ~2 seconds
        for frame in animation:
            sys.stdout.write(f"\r{Fore.YELLOW}Loading {frame}{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
    
    # Clear the screen again
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display playing message
    print(f"{Fore.GREEN}{Style.BRIGHT}Playing {selected_game['name']}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Type 'exit' to return to the main menu{Style.RESET_ALL}")
    
    # Wait for 'exit' input
    while True:
        user_input = input().strip().lower()
        if user_input == 'exit':
            print(f"{Fore.YELLOW}Returning to main menu...{Style.RESET_ALL}")
            time.sleep(1)
            os.system('cls' if os.name == 'nt' else 'clear')
            return  # Return to main menu

def print_header():
    """Print a fancy header with the program name and version."""
    print(f"{Fore.BLUE}{Style.BRIGHT}{'=' * 40}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{Style.BRIGHT} Game Launcher Client v1.0 {Style.RESET_ALL}".center(40))
    print(f"{Fore.BLUE}{Style.BRIGHT}{'=' * 40}{Style.RESET_ALL}")

def print_welcome(username):
    """Print a stylized welcome message."""
    print(f"{Fore.MAGENTA}{Style.BRIGHT}Welcome, {username}!{Style.RESET_ALL}".center(40))

def print_farewell():
    """Print a stylized farewell message."""
    print(f"{Fore.MAGENTA}{Style.BRIGHT}Thanks for using Game Launcher! Goodbye!{Style.RESET_ALL}".center(40))

@app.command()
def main():
    """
    CLI Game Launcher Client - A visually appealing game library manager with lending features.
    """
    # Load data from JSON
    data = load_data()

    # Dummy login prompt
    username = input(f"{Fore.CYAN}Enter your login key: {Style.RESET_ALL}")
    print(f"{Fore.GREEN}Logged in as {username}{Style.RESET_ALL}")

    # Display header and welcome message
    print_header()
    print_welcome(username)

    # Main interactive loop
    while True:
        print(f"\n{Fore.BLUE}{Style.BRIGHT}=== Menu ==={Style.RESET_ALL}")
        print(f"{Fore.GREEN}[1] View my game library{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[2] Launch game{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[3] Advertise game as lendable{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[4] Stop advertising game as lendable{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[5] Browse lendable games{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[6] Request to lend a game{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[7] End my lending{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[8] View dashboard{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[9] Logout{Style.RESET_ALL}")
        choice = input(f"{Fore.CYAN}Select an option: {Style.RESET_ALL}")

        if choice == "1":
            view_game_library(data, username)
        elif choice == "2":
            launch_game(data, username)
        elif choice == "3":
            advertise_game(data, username)
        elif choice == "4":
            stop_advertising_game(data, username)
        elif choice == "5":
            browse_lendable_games(data, username)
        elif choice == "6":
            request_lend_game(data, username)
        elif choice == "7":
            end_my_lending(data, username)
        elif choice == "8":
            view_dashboard(data, username)
        elif choice == "9":
            print_farewell()
            break
        else:
            print(f"{Fore.RED}Invalid option. Please try again.{Style.RESET_ALL}")

if __name__ == "__main__":
    app()