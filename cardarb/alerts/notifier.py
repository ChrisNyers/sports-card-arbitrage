from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

import pandas as pd
from rich.console import Console
from rich.table import Table

from cardarb import config

console = Console()


def print_console_alert(df: pd.DataFrame) -> None:
    if df.empty:
        console.print("[yellow]No opportunities found for today.[/yellow]")
        return

    if df["estimated_roic_pct"].max() <= 0:
        console.print(
            "[yellow]Note: every candidate today has a negative fee-adjusted ROIC estimate "
            "(round-trip marketplace fees are ~26% and none of today's price momentum clears that "
            "bar). This is expected on many days, not a bug — it means there's no real edge to act "
            "on today.[/yellow]"
        )

    table = Table(title="Daily Top Opportunities")
    table.add_column("Rank", justify="right")
    table.add_column("Player")
    table.add_column("Set / Grade")
    table.add_column("Price", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("ROIC %", justify="right")
    table.add_column("ML Prob", justify="right")
    table.add_column("Bubble", justify="right")

    for _, row in df.iterrows():
        table.add_row(
            str(row["rank"]),
            f"{row['player_name']} ({row['year']})",
            f"{row['set_name']} - {row['grade']}",
            f"${row['current_price']:.2f}",
            f"${row['target_sell_price']:.2f}",
            f"{row['estimated_roic_pct']:.1f}",
            f"{row['ml_prob_price_rise']:.2f}",
            f"{row['bubble_composite_score']:.0f}",
        )
    console.print(table)


def send_email_alert(df: pd.DataFrame) -> bool:
    """Emails the daily report. No-op (returns False) unless SMTP env vars are set —
    email is never required for daily-run to complete successfully."""
    if not config.smtp_configured():
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    to_addr = os.getenv("ALERT_EMAIL_TO")

    body = df.to_string(index=False) if not df.empty else "No opportunities today."
    msg = MIMEText(body)
    msg["Subject"] = "Daily Card Arbitrage Opportunities"
    msg["From"] = username or "cardarb@localhost"
    msg["To"] = to_addr

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(msg["From"], [to_addr], msg.as_string())
    return True
