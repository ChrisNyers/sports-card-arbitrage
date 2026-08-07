from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from cardarb.config import DAILY_REPORT_TOP_N, OUTPUT_DIR
from cardarb.db.database import connection

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def get_daily_opportunities(as_of_date: date, top_n: int = DAILY_REPORT_TOP_N) -> pd.DataFrame:
    with connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT o.*, c.player_name, c.year, c.set_name, c.card_number, c.variant, c.sport, c.grade
            FROM opportunities o
            JOIN cards c ON c.card_id = o.card_id
            WHERE o.as_of_date = ?
            ORDER BY o.rank ASC
            LIMIT ?
            """,
            conn,
            params=(as_of_date.isoformat(), top_n),
        )
    return df


def render_html_report(df: pd.DataFrame, as_of_date: date) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape())
    template = env.get_template("daily_report.html.j2")
    html = template.render(
        as_of_date=as_of_date.isoformat(),
        opportunities=df.to_dict(orient="records"),
        generated_at=datetime.utcnow().isoformat(),
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"report_{as_of_date.isoformat()}.html"
    output_path.write_text(html)
    return output_path


def generate_daily_report(as_of_date: date, top_n: int = DAILY_REPORT_TOP_N) -> tuple[pd.DataFrame, Path]:
    df = get_daily_opportunities(as_of_date, top_n)
    html_path = render_html_report(df, as_of_date)
    return df, html_path
