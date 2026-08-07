from __future__ import annotations

import webbrowser
from datetime import date

import typer
from rich.console import Console
from rich.table import Table

from cardarb.alerts.notifier import print_console_alert, send_email_alert
from cardarb.alerts.report import get_daily_opportunities, render_html_report
from cardarb.bubble.index import run_bubble_scoring
from cardarb.config import OUTPUT_DIR
from cardarb.db.database import connection, init_db
from cardarb.ml.predict import ModelNotTrainedError, run_predictions
from cardarb.ml.train import train_model
from cardarb.pipeline.features import build_features
from cardarb.pipeline.ingest import run_ingest
from cardarb.positions import pnl as pnl_module
from cardarb.positions import tracker
from cardarb.scanner.ranker import run_scan

app = typer.Typer(add_completion=False, help="Sports Card Arbitrage — Phase 1 MVP CLI")
positions_app = typer.Typer(help="Manage tracked positions")
app.add_typer(positions_app, name="positions")

console = Console()


def _resolve_date(as_of: str | None) -> date:
    return date.fromisoformat(as_of) if as_of else date.today()


@app.command()
def ingest(as_of: str = typer.Option(None, help="YYYY-MM-DD, defaults to today")) -> None:
    """Pull market data from configured sources (mock or real) into raw_* tables."""
    init_db()
    target_date = _resolve_date(as_of)
    run_ingest(target_date)
    console.print(f"[green]Ingest complete for {target_date.isoformat()}[/green]")


@app.command()
def train() -> None:
    """Train the price-rise logistic regression classifier on a synthetic dataset."""
    metrics = train_model()
    console.print(
        f"[green]Model trained.[/green] accuracy={metrics['accuracy']} "
        f"precision={metrics['precision']} recall={metrics['recall']} "
        f"(n_train={metrics['n_train']}, n_test={metrics['n_test']})"
    )


@app.command()
def scan(as_of: str = typer.Option(None, help="YYYY-MM-DD, defaults to today")) -> None:
    """Build features, bubble scores, ML predictions, and rank today's opportunities."""
    init_db()
    target_date = _resolve_date(as_of)
    build_features(target_date)
    run_bubble_scoring(target_date)
    try:
        run_predictions(target_date)
    except ModelNotTrainedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    ranked = run_scan(target_date)
    console.print(f"[green]Scanned {len(ranked)} cards for {target_date.isoformat()}[/green]")


@app.command()
def report(
    as_of: str = typer.Option(None, help="YYYY-MM-DD, defaults to today"),
    top: int = typer.Option(20, help="Number of opportunities to show"),
    html: bool = typer.Option(True, help="Also render an HTML report to output/"),
    email: bool = typer.Option(False, help="Send the report by email if SMTP is configured"),
) -> None:
    """View the latest ranked opportunities for a given day."""
    target_date = _resolve_date(as_of)
    df = get_daily_opportunities(target_date, top_n=top)
    print_console_alert(df)
    if html:
        html_path = render_html_report(df, target_date)
        console.print(f"HTML report: {html_path}")
    if email:
        sent = send_email_alert(df)
        console.print("[green]Email sent[/green]" if sent else "[yellow]SMTP not configured, email skipped[/yellow]")


@app.command(name="daily-run")
def daily_run(as_of: str = typer.Option(None, help="YYYY-MM-DD, defaults to today")) -> None:
    """Runs the full pipeline: ingest -> features -> bubble -> predict -> scan -> report.

    This is the one command to schedule via cron/launchd (see scripts/daily_run.sh).
    """
    init_db()
    target_date = _resolve_date(as_of)

    run_ingest(target_date)
    build_features(target_date)
    run_bubble_scoring(target_date)
    try:
        run_predictions(target_date)
    except ModelNotTrainedError:
        console.print("[yellow]No trained model found. Run `cardarb train` first.[/yellow]")
        raise typer.Exit(code=1)
    run_scan(target_date)
    tracker.refresh_current_prices()

    df = get_daily_opportunities(target_date)
    print_console_alert(df)
    html_path = render_html_report(df, target_date)
    console.print(f"HTML report: {html_path}")
    send_email_alert(df)


@app.command()
def approve(
    opportunity_id: int,
    buy_price: float = typer.Option(None, help="Actual price you paid; defaults to the listed current price"),
    notes: str = typer.Option("", help="Optional notes"),
) -> None:
    """Log a manual approval/purchase decision and open a tracked position.

    This only records that YOU bought the card manually elsewhere — it never
    executes a trade itself.
    """
    position_id = tracker.approve_opportunity(opportunity_id, actual_buy_price=buy_price, notes=notes)
    console.print(f"[green]Opportunity {opportunity_id} approved -> position {position_id} opened.[/green]")


@positions_app.command(name="list")
def positions_list(status: str = typer.Option(None, help="Filter by status: open|closed")) -> None:
    """List tracked positions."""
    query = "SELECT * FROM positions"
    params: tuple = ()
    if status:
        query += " WHERE status = ?"
        params = (status,)

    with connection() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]

    if not rows:
        console.print("[yellow]No positions found.[/yellow]")
        return

    columns = ["id", "card_id", "buy_price", "buy_date", "status", "current_market_price", "sell_price", "sell_date"]
    table = Table(title="Positions")
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*(str(row.get(col, "")) for col in columns))
    console.print(table)


@positions_app.command(name="show")
def positions_show(position_id: int) -> None:
    """Show a single position and its computed P&L."""
    with connection() as conn:
        row = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,)).fetchone()
    if row is None:
        console.print(f"[red]No position with id {position_id}[/red]")
        raise typer.Exit(code=1)

    position = dict(row)
    console.print(position)
    console.print(pnl_module.position_pnl(position))


@positions_app.command(name="close")
def positions_close(
    position_id: int,
    sell_price: float = typer.Option(..., help="Actual price you sold it for"),
    sell_date: str = typer.Option(None, help="YYYY-MM-DD, defaults to today"),
    sell_fees: float = typer.Option(0.0, help="Marketplace/shipping fees paid on the sale"),
) -> None:
    """Log the manual sale of an already-open position."""
    target_date = _resolve_date(sell_date)
    tracker.close_position(position_id, sell_price, target_date, sell_fees)
    console.print(f"[green]Position {position_id} closed.[/green]")


@positions_app.command(name="refresh-prices")
def positions_refresh_prices() -> None:
    """Refresh current_market_price for all open positions from the latest features."""
    updated = tracker.refresh_current_prices()
    console.print(f"[green]Refreshed {updated} open position(s).[/green]")


@app.command()
def pnl() -> None:
    """Show the portfolio-level P&L summary: win rate, realized/unrealized, avg ROIC."""
    summary = pnl_module.portfolio_summary()
    table = Table(title="Portfolio Summary")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in summary.items():
        table.add_row(key, str(value))
    console.print(table)


@app.command()
def dashboard(as_of: str = typer.Option(None, help="YYYY-MM-DD, defaults to today")) -> None:
    """Open the latest HTML report in a browser."""
    target_date = _resolve_date(as_of)
    html_path = OUTPUT_DIR / f"report_{target_date.isoformat()}.html"
    if not html_path.exists():
        console.print(f"[red]No report found at {html_path}. Run `cardarb daily-run` or `cardarb report` first.[/red]")
        raise typer.Exit(code=1)
    webbrowser.open(html_path.as_uri())


if __name__ == "__main__":
    app()
