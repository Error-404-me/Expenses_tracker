from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path


DB_PATH = Path("data") / "expenses.sqlite3"


CATEGORIES = (
    "Food",
    "Transport",
    "Housing",
    "Utilities",
    "Health",
    "Education",
    "Shopping",
    "Entertainment",
    "Savings",
    "Other",
)

PAYMENT_METHODS = (
    "Cash",
    "Debit Card",
    "Credit Card",
    "E-Wallet",
    "Bank Transfer",
)

PIPELINE_MODES = ("ETL", "ELT")


@dataclass(frozen=True)
class Expense:
    id: int
    expense_date: str
    category: str
    merchant: str
    amount: float
    payment_method: str
    note: str
    pipeline_mode: str
    created_at: str


@dataclass(frozen=True)
class ExpenseStage:
    id: int
    raw_expense_date: str
    raw_category: str
    raw_merchant: str
    raw_amount: str
    raw_payment_method: str
    raw_note: str
    loaded_at: str


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                merchant TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                payment_method TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                pipeline_mode TEXT NOT NULL DEFAULT 'ETL',
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()}
        if "pipeline_mode" not in columns:
            conn.execute("ALTER TABLE expenses ADD COLUMN pipeline_mode TEXT NOT NULL DEFAULT 'ETL'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_stage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_expense_date TEXT NOT NULL,
                raw_category TEXT NOT NULL,
                raw_merchant TEXT NOT NULL,
                raw_amount TEXT NOT NULL,
                raw_payment_method TEXT NOT NULL,
                raw_note TEXT NOT NULL DEFAULT '',
                loaded_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_expense(
    expense_date: str,
    category: str,
    merchant: str,
    amount: float,
    payment_method: str,
    note: str = "",
    pipeline_mode: str = "ETL",
    db_path: Path = DB_PATH,
) -> int:
    init_db(db_path)
    cleaned_date, cleaned_category, cleaned_merchant, cleaned_amount, cleaned_payment, cleaned_note = clean_expense_values(
        expense_date,
        category,
        merchant,
        amount,
        payment_method,
        note,
    )
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses(expense_date, category, merchant, amount, payment_method, note, pipeline_mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned_date,
                cleaned_category,
                cleaned_merchant,
                cleaned_amount,
                cleaned_payment,
                cleaned_note,
                normalize_pipeline_mode(pipeline_mode),
                now_utc(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def save_expense_pipeline(
    expense_date: str,
    category: str,
    merchant: str,
    amount: float | str,
    payment_method: str,
    note: str = "",
    pipeline_mode: str = "ETL",
    db_path: Path = DB_PATH,
) -> dict:
    mode = normalize_pipeline_mode(pipeline_mode)
    if mode == "ELT":
        expense_id = save_expense_elt(
            expense_date,
            category,
            merchant,
            amount,
            payment_method,
            note,
            db_path=db_path,
        )
    else:
        cleaned = clean_expense_values(expense_date, category, merchant, amount, payment_method, note)
        expense_id = add_expense(*cleaned, pipeline_mode="ETL", db_path=db_path)

    return {
        "expense_id": expense_id,
        "mode": mode,
        "sql": pipeline_sql_preview(mode),
    }


def save_expense_elt(
    expense_date: str,
    category: str,
    merchant: str,
    amount: float | str,
    payment_method: str,
    note: str = "",
    db_path: Path = DB_PATH,
) -> int:
    init_db(db_path)
    clean_expense_values(expense_date, category, merchant, amount, payment_method, note)
    loaded_at = now_utc()
    category_placeholders = ", ".join("?" for _ in CATEGORIES)
    payment_placeholders = ", ".join("?" for _ in PAYMENT_METHODS)

    with sqlite3.connect(db_path) as conn:
        stage_cursor = conn.execute(
            """
            INSERT INTO expense_stage(raw_expense_date, raw_category, raw_merchant, raw_amount, raw_payment_method, raw_note, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(expense_date),
                str(category),
                str(merchant),
                str(amount),
                str(payment_method),
                str(note or ""),
                loaded_at,
            ),
        )
        stage_id = int(stage_cursor.lastrowid)
        conn.execute(
            f"""
            INSERT INTO expenses(expense_date, category, merchant, amount, payment_method, note, pipeline_mode, created_at)
            SELECT
                substr(trim(raw_expense_date), 1, 10),
                CASE WHEN raw_category IN ({category_placeholders}) THEN raw_category ELSE 'Other' END,
                COALESCE(NULLIF(trim(raw_merchant), ''), 'Unspecified'),
                ROUND(CAST(raw_amount AS REAL), 2),
                CASE WHEN raw_payment_method IN ({payment_placeholders}) THEN raw_payment_method ELSE 'Cash' END,
                trim(raw_note),
                'ELT',
                ?
            FROM expense_stage
            WHERE id = ?
            """,
            (*CATEGORIES, *PAYMENT_METHODS, loaded_at, stage_id),
        )
        expense_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
        return expense_id


def delete_expense(expense_id: int, db_path: Path = DB_PATH) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()


def list_expenses(
    month: str | None = None,
    category: str | None = None,
    db_path: Path = DB_PATH,
) -> list[Expense]:
    init_db(db_path)
    clauses: list[str] = []
    params: list[str] = []

    if month and month != "All":
        clauses.append("substr(expense_date, 1, 7) = ?")
        params.append(month)
    if category and category != "All":
        clauses.append("category = ?")
        params.append(category)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT id, expense_date, category, merchant, amount, payment_method, note, pipeline_mode, created_at
        FROM expenses
        {where}
        ORDER BY expense_date DESC, id DESC
        LIMIT 200
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [Expense(**dict(row)) for row in conn.execute(query, params).fetchall()]


def list_expense_stage(
    month: str | None = None,
    category: str | None = None,
    db_path: Path = DB_PATH,
) -> list[ExpenseStage]:
    init_db(db_path)
    clauses: list[str] = []
    params: list[str] = []

    if month and month != "All":
        clauses.append("substr(raw_expense_date, 1, 7) = ?")
        params.append(month)
    if category and category != "All":
        clauses.append("raw_category = ?")
        params.append(category)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT id, raw_expense_date, raw_category, raw_merchant, raw_amount, raw_payment_method, raw_note, loaded_at
        FROM expense_stage
        {where}
        ORDER BY loaded_at DESC, id DESC
        LIMIT 200
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [ExpenseStage(**dict(row)) for row in conn.execute(query, params).fetchall()]


def available_months(db_path: Path = DB_PATH) -> list[str]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT substr(expense_date, 1, 7) AS month
            FROM expenses
            ORDER BY month DESC
            """
        ).fetchall()
    months = [row[0] for row in rows if row[0]]
    current_month = date.today().isoformat()[:7]
    if current_month not in months:
        months.insert(0, current_month)
    return months


def expense_summary(
    month: str | None = None,
    category: str | None = None,
    db_path: Path = DB_PATH,
) -> dict:
    expenses = list_expenses(month=month, category=category, db_path=db_path)
    total = sum(expense.amount for expense in expenses)
    count = len(expenses)
    average = total / count if count else 0
    biggest = max(expenses, key=lambda item: item.amount, default=None)

    by_category: dict[str, float] = {}
    by_month: dict[str, float] = {}
    for expense in expenses:
        by_category[expense.category] = by_category.get(expense.category, 0) + expense.amount
        month_key = expense.expense_date[:7]
        by_month[month_key] = by_month.get(month_key, 0) + expense.amount

    return {
        "total": total,
        "count": count,
        "average": average,
        "biggest": biggest,
        "by_category": sorted(by_category.items(), key=lambda item: item[1], reverse=True),
        "by_month": sorted(by_month.items()),
        "expenses": expenses,
    }


def seed_sample_data(db_path: Path = DB_PATH) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    if count:
        return

    samples = (
        ("2026-05-01", "Food", "Lunch", 180.00, "E-Wallet", "Rice meal"),
        ("2026-05-02", "Transport", "Bus fare", 45.00, "Cash", "Morning commute"),
        ("2026-05-03", "Shopping", "Groceries", 980.75, "Debit Card", "Weekly essentials"),
        ("2026-05-05", "Utilities", "Internet", 1299.00, "Bank Transfer", "Monthly bill"),
        ("2026-05-07", "Health", "Pharmacy", 260.50, "Cash", "Medicine"),
        ("2026-04-22", "Entertainment", "Streaming", 399.00, "Credit Card", "Subscription"),
        ("2026-04-18", "Food", "Coffee", 155.00, "E-Wallet", "Meeting"),
    )
    for row in samples:
        add_expense(*row, db_path=db_path)


def clean_expense_values(
    expense_date: str,
    category: str,
    merchant: str,
    amount: float | str,
    payment_method: str,
    note: str = "",
) -> tuple[str, str, str, float, str, str]:
    cleaned_date = date.fromisoformat(str(expense_date).strip()).isoformat()
    cleaned_amount = round(float(str(amount).replace(",", "").strip()), 2)
    if cleaned_amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    cleaned_category = category if category in CATEGORIES else "Other"
    cleaned_payment = payment_method if payment_method in PAYMENT_METHODS else PAYMENT_METHODS[0]
    cleaned_merchant = str(merchant or "").strip() or "Unspecified"
    cleaned_note = str(note or "").strip()
    return cleaned_date, cleaned_category, cleaned_merchant, cleaned_amount, cleaned_payment, cleaned_note


def normalize_pipeline_mode(value: str) -> str:
    mode = str(value or "ETL").upper()
    return mode if mode in PIPELINE_MODES else "ETL"


def pipeline_sql_preview(pipeline_mode: str) -> str:
    mode = normalize_pipeline_mode(pipeline_mode)
    if mode == "ELT":
        return """-- ELT: load raw expense first
INSERT INTO expense_stage(raw_expense_date, raw_category, raw_merchant, raw_amount, raw_payment_method, raw_note, loaded_at)
VALUES (?, ?, ?, ?, ?, ?, ?);

-- Transform inside SQLite and load the curated table
INSERT INTO expenses(expense_date, category, merchant, amount, payment_method, note, pipeline_mode, created_at)
SELECT
    substr(trim(raw_expense_date), 1, 10),
    CASE WHEN raw_category IN (...) THEN raw_category ELSE 'Other' END,
    COALESCE(NULLIF(trim(raw_merchant), ''), 'Unspecified'),
    ROUND(CAST(raw_amount AS REAL), 2),
    CASE WHEN raw_payment_method IN (...) THEN raw_payment_method ELSE 'Cash' END,
    trim(raw_note),
    'ELT',
    ?
FROM expense_stage
WHERE id = ?;"""

    return """-- ETL: transform in Python before loading
INSERT INTO expenses(expense_date, category, merchant, amount, payment_method, note, pipeline_mode, created_at)
VALUES (?, ?, ?, ?, ?, ?, 'ETL', ?);"""


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
