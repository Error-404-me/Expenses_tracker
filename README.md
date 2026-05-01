# Expense Tracker with ETL and ELT

A Flet web app for tracking expenses in a local SQLite database. The app lets users add expenses, choose whether each save runs through an ETL or ELT pipeline, view the SQL used by the selected pipeline, and review spending analytics with bar charts.

## Run locally

```powershell
pip install -r requirements.txt
flet run -w -p 8550 main.py
```

Open http://localhost:8550 in your browser.

## What it does

- Saves expenses to `data/expenses.sqlite3`.
- Uses a Flet `DatePicker` for expense dates.
- Uses a Flet `DatePicker` for month filtering.
- Keeps filters and the **Add Expenses** action in the top header.
- Supports ETL mode: clean the input in Python, then insert curated data into SQLite.
- Supports ELT mode: load raw input into `expense_stage`, then transform into `expenses` using SQL.
- Shows the active pipeline SQL in the dashboard.
- Displays category analytics and monthly trends as bar charts.
- Shows the SQLite `expenses` table as the readable ELT target table.
- Shows the SQLite `expense_stage` table so raw ELT loads are visible before transformation.

## Files

- `main.py` - Flet expense tracker UI and dashboard interactions.
- `expense_store.py` - SQLite tables, ETL/ELT save logic, and analytics queries.

Runtime SQLite data is written to `data/expenses.sqlite3`.
