"""track_accounts.py — live ETH‑balance dashboard
================================================
Now **robust** multi‑series graphing; no more crash before first data point.

```bash
# All accounts graph
python track_accounts.py -m graph --all
```
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

from lib.config import settings
from lib.account.user import User

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
private_keys: List[str] = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
    "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",
    "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",
    "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",
    "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",
    "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6",
    "0xf214f2b2cd398c806f84e317254e0f0b801d0643303237d97a22a48e01628897",
    "0x701b615bbdfb9de65240bc28bd21bbc0d996645a3dd57e7b12bc2bdf6f192c82",
    "0xa267530f49f8280200edf313ee7af6b827f2a8bce2897751d06a843f644967b1",
    "0x47c99abed3324a2707c28affff1267e45918ec8c3f20b8aa892e8b065d2942dd",
    "0xc526ee95bf44d8fc405a158bb884d9d1238d99f0612e9f33d006bb0789009aaa",
    "0x8166f546bab6da521a8369cab06c5d2b9e46670292d85c875ee9ec20e84ffb61",
    "0xea6c44ac03bff858b476bba40716402b03e41b8e97e276d1baec7c37d42484a0",
    "0x689af8efa8c651a91ad287602527f3af2fe9f6501a7ac4b061667b5a93e037fd",
    "0xde9be858da4a475276426320d5e9262ecfc3ba460bfac56360bfa6c4c28b4ee0",
    "0xdf57089febbacf7ba0bc227dafbffa9fc08a93fdc68e1e42411a14efcf23656e",
]

# ---------------------------------------------------------------------------
# Optional ASCII chart backend
# ---------------------------------------------------------------------------
try:
    import asciichartpy  # type: ignore
except ImportError:
    asciichartpy = None  # noqa: N816 – keep camelCase for external lib


console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True)


class Dashboard:
    """Real-time dashboard of ETH balances with table or graph view."""

    def __init__(self, accounts: List[User], interval: float = 1.0, graph_account: Optional[int] = 0, all_accounts: bool = False):
        self.accounts = accounts
        self.interval = interval
        self.graph_account = graph_account
        self.all_accounts = all_accounts
        self.history: dict[int, list[float]] = {
            i: [] for i in range(len(accounts))}

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------
    def _poll_balances(self) -> None:
        for idx, acc in enumerate(self.accounts):
            wei = acc.get_balance()
            eth_val = settings.Web3.from_wei(wei, "ether")
            self.history[idx].append(float(eth_val))

    # -------------------------------------------------------------------
    # Renderables
    # -------------------------------------------------------------------
    def _render_table(self) -> Table:
        table = Table(
            title=f"Account Balances · {datetime.now():%Y-%m-%d %H:%M:%S}",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        table.add_column("#", justify="right", no_wrap=True)
        table.add_column("Address", overflow="fold")
        table.add_column("Balance (ETH)", justify="right")

        for idx, acc in enumerate(self.accounts):
            latest = self.history[idx][-1] if self.history[idx] else settings.Web3.from_wei(
                acc.get_balance(), "ether")
            table.add_row(str(idx), getattr(
                acc, "address", "<unknown>"), f"{latest:,.4f}")
        return table

    def _render_graph(self) -> Panel | Text:
        if asciichartpy is None:
            return Text("Graph view needs `asciichartpy` (pip install asciichartpy)", style="bold red")

        # MULTI‑SERIES --------------------------------------------------
        if self.all_accounts:
            max_len = max(1, max(len(h) for h in self.history.values()))
            series_list: list[list[float]] = []
            for i in range(len(self.accounts)):
                s = self.history[i][-max_len:]
                if len(s) < max_len:
                    s = [0.0] * (max_len - len(s)) + s  # pad with zeroes
                series_list.append(s)
            chart = asciichartpy.plot(series_list, {"height": 12})
            title = f"ALL accounts | Last {max_len} samples | {datetime.now():%H:%M:%S}"
            legend = "  ".join(str(i) for i in range(len(self.accounts)))
            return Panel.fit(f"{chart}\nAcct #: {legend}", title=title, border_style="cyan")

        # SINGLE‑SERIES --------------------------------------------------
        if self.graph_account is None or self.graph_account >= len(self.accounts):
            return Text("Invalid graph‑account index", style="bold red")

        series = self.history[self.graph_account][-120:] or [0.0]
        chart = asciichartpy.plot(series, {"height": 12})
        title = f"Account {self.graph_account} | Last {len(series)} samples | {datetime.now():%H:%M:%S}"
        return Panel.fit(chart, title=title, border_style="cyan")

    # -------------------------------------------------------------------
    # Main loop
    # -------------------------------------------------------------------
    def run(self, mode: str) -> None:
        mode = mode.lower()
        # Prime at least one data point to avoid empty-series crash
        self._poll_balances()
        render_fn = self._render_table if mode == "table" else self._render_graph

        with Live(render_fn(), console=console, refresh_per_second=4) as live:
            try:
                while True:
                    time.sleep(self.interval)
                    self._poll_balances()
                    live.update(render_fn())
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped dashboard.[/]")


# ---------------------------------------------------------------------------
# Shared runner
# ---------------------------------------------------------------------------

def _run_dashboard(mode: str, interval: float, graph_account: Optional[int], all_accounts: bool) -> None:
    accounts = [User(k) for k in private_keys]
    Dashboard(accounts, interval=interval, graph_account=graph_account,
              all_accounts=all_accounts).run(mode)


# ---------------------------------------------------------------------------
# Root callback
# ---------------------------------------------------------------------------
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    mode: str = typer.Option(
        "table", "--mode", "-m", help="Display mode: table or graph", case_sensitive=False),
    interval: float = typer.Option(
        1.0, "--interval", "-i", help="Polling interval in seconds"),
    graph_account: Optional[int] = typer.Option(
        0, "--graph-account", "-g", help="Account index to graph (ignored if --all)"),
    all_accounts: bool = typer.Option(
        False, "--all", help="Graph all accounts at once"),
):
    if ctx.invoked_subcommand is None:
        _run_dashboard(mode, interval, graph_account, all_accounts)


# ---------------------------------------------------------------------------
# Explicit sub‑command (legacy)
# ---------------------------------------------------------------------------
@app.command()
def dashboard(
    mode: str = typer.Option(
        "table", "--mode", "-m", help="Display mode: table or graph", case_sensitive=False),
    interval: float = typer.Option(
        1.0, "--interval", "-i", help="Polling interval in seconds"),
    graph_account: Optional[int] = typer.Option(
        0, "--graph-account", "-g", help="Account index to graph (ignored if --all)"),
    all_accounts: bool = typer.Option(
        False, "--all", help="Graph all accounts at once"),
):
    _run_dashboard(mode, interval, graph_account, all_accounts)


if __name__ == "__main__":
    app()
