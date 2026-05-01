from __future__ import annotations

from datetime import date, datetime, timezone

import flet as ft

from expense_store import (
    CATEGORIES,
    PAYMENT_METHODS,
    PIPELINE_MODES,
    Expense,
    ExpenseStage,
    delete_expense,
    expense_summary,
    init_db,
    list_expense_stage,
    pipeline_sql_preview,
    save_expense_pipeline,
)


BG = "#F5F7F2"
SURFACE = "#FFFFFF"
INK = "#172025"
MUTED = "#5C6B73"
BORDER = "#D9E2E7"
TEAL = "#006C67"
TEAL_SOFT = "#E2F3F1"
GREEN = "#2E7D46"
GREEN_SOFT = "#E8F4EA"
AMBER = "#A85B00"
AMBER_SOFT = "#FFF1DA"
RED = "#B42318"
RED_SOFT = "#FCE8E6"
BLUE = "#2F5F98"
BLUE_SOFT = "#E7F0FB"
VIOLET = "#6E4DBA"
VIOLET_SOFT = "#EFE9FF"

CATEGORY_COLORS = {
    "Food": TEAL,
    "Transport": BLUE,
    "Housing": VIOLET,
    "Utilities": AMBER,
    "Health": RED,
    "Education": "#3A7D44",
    "Shopping": "#8A5A00",
    "Entertainment": "#6D5799",
    "Savings": GREEN,
    "Other": MUTED,
}

CENTER = ft.Alignment(0, 0)


def main(page: ft.Page) -> None:
    init_db()
    page.title = "Expense Tracker"
    page.bgcolor = BG
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    today_date = date.today()
    today = today_date.isoformat()

    date_input = ft.TextField(
        label="Date",
        value=today,
        read_only=True,
        dense=True,
        border_radius=8,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
    )
    date_picker = ft.DatePicker(
        value=picker_value(today),
        first_date=date(2020, 1, 1),
        last_date=date(2050, 12, 31),
        entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY,
        help_text="Expense date",
        confirm_text="Use date",
    )
    amount_input = ft.TextField(label="Amount", hint_text="0.00", dense=True, border_radius=8)
    merchant_input = ft.TextField(label="Merchant / description", hint_text="e.g. lunch, bus fare", dense=True, border_radius=8)
    category_input = ft.Dropdown(
        label="Category",
        value=CATEGORIES[0],
        options=[ft.DropdownOption(category, category) for category in CATEGORIES],
        leading_icon=ft.Icons.CATEGORY,
        dense=True,
        border_radius=8,
    )
    payment_input = ft.Dropdown(
        label="Payment",
        value=PAYMENT_METHODS[0],
        options=[ft.DropdownOption(method, method) for method in PAYMENT_METHODS],
        leading_icon=ft.Icons.CREDIT_CARD,
        dense=True,
        border_radius=8,
    )
    note_input = ft.TextField(label="Note", multiline=True, min_lines=2, max_lines=3, dense=True, border_radius=8)
    pipeline_mode = ft.SegmentedButton(
        segments=[
            ft.Segment(value="ETL", icon=ft.Icons.PLAYLIST_ADD_CHECK, label=ft.Text("ETL")),
            ft.Segment(value="ELT", icon=ft.Icons.SCHEMA, label=ft.Text("ELT")),
        ],
        selected=["ETL"],
        allow_empty_selection=False,
    )

    selected_month = {"value": "All"}
    month_filter = ft.TextField(
        label="Month",
        value="All months",
        read_only=True,
        dense=True,
        border_radius=8,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        width=190,
    )
    month_picker = ft.DatePicker(
        value=picker_value(today),
        first_date=date(2020, 1, 1),
        last_date=date(2050, 12, 31),
        entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY,
        help_text="Pick any date in the month",
        confirm_text="Use month",
    )
    category_filter = ft.Dropdown(
        label="Category",
        value="All",
        options=[ft.DropdownOption("All", "All")] + [ft.DropdownOption(category, category) for category in CATEGORIES],
        dense=True,
        border_radius=8,
        leading_icon=ft.Icons.FILTER_ALT,
        width=210,
    )
    status_text = ft.Text("", size=12, color=MUTED)
    sql_text = ft.Text(
        pipeline_sql_preview("ETL"),
        size=12,
        color=INK,
        font_family="Consolas",
        selectable=True,
    )

    kpi_grid = ft.ResponsiveRow(spacing=12, run_spacing=12)
    category_bars = ft.Column(spacing=10)
    month_bars = ft.Column(spacing=10)
    expenses_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("id", weight=ft.FontWeight.W_700), numeric=True),
            ft.DataColumn(ft.Text("expense_date", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("category", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("merchant", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("amount", weight=ft.FontWeight.W_700), numeric=True),
            ft.DataColumn(ft.Text("payment_method", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("pipeline_mode", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("note", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("created_at", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("", weight=ft.FontWeight.W_700)),
        ],
        rows=[],
        heading_row_color="#EEF3F4",
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        column_spacing=22,
        horizontal_margin=16,
        col=12,
    )
    stage_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("id", weight=ft.FontWeight.W_700), numeric=True),
            ft.DataColumn(ft.Text("raw_expense_date", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("raw_category", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("raw_merchant", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("raw_amount", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("raw_payment_method", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("raw_note", weight=ft.FontWeight.W_700)),
            ft.DataColumn(ft.Text("loaded_at", weight=ft.FontWeight.W_700)),
        ],
        rows=[],
        heading_row_color="#EEF3F4",
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        column_spacing=22,
        horizontal_margin=16,
    )

    def refresh() -> None:
        summary = expense_summary(month=selected_month["value"], category=category_filter.value)
        expenses = summary["expenses"]
        stage_rows = list_expense_stage(month=selected_month["value"], category=category_filter.value)
        biggest = summary["biggest"]

        kpi_grid.controls = [
            kpi_tile("Total spent", money(summary["total"]), "Filtered expenses", ft.Icons.PAID, TEAL_SOFT, TEAL),
            kpi_tile("Transactions", str(summary["count"]), "Saved in SQLite", ft.Icons.RECEIPT_LONG, BLUE_SOFT, BLUE),
            kpi_tile("Average spend", money(summary["average"]), "Per transaction", ft.Icons.QUERY_STATS, GREEN_SOFT, GREEN),
            kpi_tile(
                "Largest expense",
                money(biggest.amount) if biggest else money(0),
                biggest.merchant if biggest else "No expenses yet",
                ft.Icons.WARNING_AMBER,
                AMBER_SOFT,
                AMBER,
            ),
        ]
        category_bars.controls = bar_chart(
            summary["by_category"],
            total=summary["total"],
            empty_text="No category data yet.",
        )
        month_bars.controls = bar_chart(
            summary["by_month"],
            total=max((value for _, value in summary["by_month"]), default=0),
            empty_text="No monthly trend yet.",
        )
        expenses_table.rows = [expense_row(expense) for expense in expenses]
        if not expenses:
            expenses_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("No rows", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("Add an expense to populate the expenses table.", color=MUTED)),
                        ft.DataCell(ft.Text(money(0), color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("")),
                    ]
                )
            ]
        stage_table.rows = [stage_row(row) for row in stage_rows]
        if not stage_rows:
            stage_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("No rows", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("Run the ELT pipeline to load raw rows here.", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                        ft.DataCell(ft.Text("-", color=MUTED)),
                    ]
                )
            ]
        page.update()

    def selected_pipeline() -> str:
        selected = pipeline_mode.selected or ["ETL"]
        return selected[0] if selected[0] in PIPELINE_MODES else "ETL"

    def update_sql_preview(mode: str | None = None) -> None:
        sql_text.value = pipeline_sql_preview(mode or selected_pipeline())

    def open_date_picker(event=None) -> None:
        date_picker.value = picker_value(date_input.value)
        page.show_dialog(date_picker)

    def date_picker_changed(event=None) -> None:
        picked = picker_date_iso(event, date_input.value)
        date_input.value = picked
        date_picker.value = picker_value(picked)
        page.update()

    def open_month_picker(event=None) -> None:
        month_picker.value = picker_value(
            f"{selected_month['value']}-01" if selected_month["value"] != "All" else date.today().isoformat()
        )
        page.show_dialog(month_picker)

    def month_picker_changed(event=None) -> None:
        picked = picker_date_iso(event, date.today().isoformat())
        selected_month["value"] = picked[:7]
        month_filter.value = selected_month["value"]
        refresh()

    def clear_month_filter(event=None) -> None:
        selected_month["value"] = "All"
        month_filter.value = "All months"
        refresh()

    def pipeline_changed(event=None) -> None:
        update_sql_preview()
        status_text.value = f"{selected_pipeline()} pipeline selected."
        status_text.color = MUTED
        page.update()

    def save_expense(event=None) -> None:
        try:
            datetime.strptime(date_input.value.strip(), "%Y-%m-%d")
        except ValueError:
            status_text.value = "Use YYYY-MM-DD for the date."
            status_text.color = RED
            page.update()
            return

        try:
            amount = float((amount_input.value or "").replace(",", "").strip())
        except ValueError:
            status_text.value = "Enter a valid amount."
            status_text.color = RED
            page.update()
            return

        if amount <= 0:
            status_text.value = "Amount must be greater than zero."
            status_text.color = RED
            page.update()
            return

        result = save_expense_pipeline(
            expense_date=date_input.value.strip(),
            category=category_input.value,
            merchant=merchant_input.value or "Unspecified",
            amount=amount,
            payment_method=payment_input.value,
            note=note_input.value or "",
            pipeline_mode=selected_pipeline(),
        )
        amount_input.value = ""
        merchant_input.value = ""
        note_input.value = ""
        update_sql_preview(result["mode"])
        status_text.value = f"Expense saved to SQLite through {result['mode']}."
        status_text.color = GREEN
        refresh()

    def clear_form(event=None) -> None:
        today = date.today()
        date_input.value = today.isoformat()
        date_picker.value = picker_value(date_input.value)
        amount_input.value = ""
        merchant_input.value = ""
        category_input.value = CATEGORIES[0]
        payment_input.value = PAYMENT_METHODS[0]
        note_input.value = ""
        status_text.value = "Form cleared."
        status_text.color = MUTED
        page.update()

    def apply_filters(event=None) -> None:
        refresh()

    def remove_expense(expense_id: int) -> None:
        delete_expense(expense_id)
        status_text.value = "Expense deleted."
        status_text.color = RED
        refresh()

    def open_add_expense(event=None) -> None:
        status_text.value = ""
        page.show_dialog(add_expense_dialog)

    def close_add_expense(event=None) -> None:
        page.pop_dialog()

    def expense_row(expense: Expense) -> ft.DataRow:
        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(str(expense.id), color=MUTED)),
                ft.DataCell(ft.Text(expense.expense_date, color=INK)),
                ft.DataCell(category_pill(expense.category)),
                ft.DataCell(ft.Text(expense.merchant, color=INK, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ft.DataCell(ft.Text(money(expense.amount), color=INK, weight=ft.FontWeight.W_700)),
                ft.DataCell(ft.Text(expense.payment_method, color=MUTED)),
                ft.DataCell(pipeline_pill(expense.pipeline_mode)),
                ft.DataCell(ft.Text(expense.note or "-", color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ft.DataCell(ft.Text(expense.created_at, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ft.DataCell(
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=RED,
                        tooltip="Delete expense",
                        on_click=lambda event, expense_id=expense.id: remove_expense(expense_id),
                    )
                ),
            ]
        )

    def stage_row(row: ExpenseStage) -> ft.DataRow:
        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(str(row.id), color=MUTED)),
                ft.DataCell(ft.Text(row.raw_expense_date, color=INK)),
                ft.DataCell(ft.Text(row.raw_category, color=INK)),
                ft.DataCell(ft.Text(row.raw_merchant, color=INK, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ft.DataCell(ft.Text(row.raw_amount, color=INK, weight=ft.FontWeight.W_700)),
                ft.DataCell(ft.Text(row.raw_payment_method, color=MUTED)),
                ft.DataCell(ft.Text(row.raw_note or "-", color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ft.DataCell(ft.Text(row.loaded_at, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
            ]
        )

    add_expense_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        title=ft.Container(
            width=450,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.ADD, color=TEAL, size=22),
                            ft.Text("Add Expense", color=INK, weight=ft.FontWeight.W_700),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=MUTED,
                        tooltip="Close",
                        on_click=close_add_expense,
                    ),
                ],
            ),
        ),
        content=input_panel(
            date_input,
            amount_input,
            merchant_input,
            category_input,
            payment_input,
            note_input,
            pipeline_mode,
            status_text,
            save_expense,
            clear_form,
        ),
        title_padding=ft.Padding.only(left=24, top=18, right=10, bottom=0),
        content_padding=ft.Padding.only(left=24, top=12, right=24, bottom=20),
        inset_padding=24,
        actions=[
            ft.OutlinedButton("Clear", icon=ft.Icons.REFRESH, icon_color=TEAL, on_click=clear_form),
            ft.FilledButton("Save expense", icon=ft.Icons.ADD, bgcolor=TEAL, color="#FFFFFF", on_click=save_expense),
        ]
    )

    date_input.on_click = open_date_picker
    date_picker.on_change = date_picker_changed
    month_filter.on_click = open_month_picker
    month_picker.on_change = month_picker_changed
    pipeline_mode.on_change = pipeline_changed
    category_filter.on_select = apply_filters

    page.add(
        ft.Container(
            bgcolor=BG,
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    app_header(month_filter, category_filter, clear_month_filter, open_add_expense),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=24, vertical=18),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            spacing=16,
                            controls=[
                                analytics_panel(kpi_grid),
                                ft.ResponsiveRow(
                                    spacing=16,
                                    run_spacing=16,
                                    controls=[
                                        chart_panel("Category Analytics", "Spending grouped by category.", category_bars, ft.Icons.CATEGORY, {"xs": 12, "lg": 6}),
                                        chart_panel("Monthly Trend", "Spending totals by month.", month_bars, ft.Icons.CALENDAR_MONTH, {"xs": 12, "lg": 6}),
                                    ],
                                ),
                                ft.ResponsiveRow(
                                    columns=1,
                                    spacing=16,
                                    run_spacing=16,
                                    controls=[
                                        table_panel(
                                            "expenses",
                                            "SQLite ELT target table with transformed expense rows.",
                                            expenses_table,
                                            {"xs": 12, "xl": 6},
                                        ),
                                    ],
                                ),
                                ft.ResponsiveRow(
                                    columns=1,
                                    spacing=16,
                                    run_spacing=16,
                                    controls=[
                                        table_panel(
                                            "expense_stage",
                                            "SQLite raw staging table loaded before ELT transform.",
                                            stage_table,
                                            {"xs": 12, "xl": 6},
                                        ),
                                    ],
                                ),
                                sql_panel(sql_text),
                            ],
                        ),
                    ),
                ],
            ),
        )
    )
    refresh()


def app_header(month_filter, category_filter, clear_month_filter, open_add_expense) -> ft.Control:
    return ft.Container(
        bgcolor=SURFACE,
        padding=ft.Padding.symmetric(horizontal=24, vertical=18),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        content=ft.ResponsiveRow(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            run_spacing=12,
            controls=[
                ft.Container(
                    col={"xs": 12, "lg": 4},
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                spacing=8,
                                wrap=True,
                                controls=[
                                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=TEAL, size=28),
                                    ft.Text("Expense Tracker", size=26, color=INK, weight=ft.FontWeight.W_800),
                                ],
                            ),
                            ft.Text("Track daily spending, store it locally in SQLite, and review expense analytics.", size=13, color=MUTED),
                        ],
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "lg": 8},
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        wrap=True,
                        spacing=10,
                        controls=[
                            month_filter,
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=MUTED,
                                tooltip="Show all months",
                                on_click=clear_month_filter,
                            ),
                            category_filter,
                            ft.FilledButton(
                                "Add Expenses",
                                icon=ft.Icons.ADD,
                                bgcolor=TEAL,
                                color="#FFFFFF",
                                on_click=open_add_expense,
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


def input_panel(
    date_input,
    amount_input,
    merchant_input,
    category_input,
    payment_input,
    note_input,
    pipeline_mode,
    status_text,
    save_expense,
    clear_form,
) -> ft.Control:
    return ft.Container(
        width=450,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Text("Save a transaction to the local SQLite database.", size=13, color=MUTED),
                ft.ResponsiveRow(
                    columns=1,
                    spacing=10,
                    run_spacing=10,
                    controls=[
                        ft.Container(amount_input, col={"xs": 12, "md": 4}),
                        ft.Container(merchant_input, col={"xs": 12, "md": 6}),
                        ft.Container(date_input, col={"xs": 12, "md": 4}),
                        ft.Row(
                            wrap=True,
                            spacing=10,
                            controls=[
                                ft.Container(category_input,),
                                ft.Container(payment_input,),
                            ],
                            col={"xs": 12, "md": 4},
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(
                            ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text("Pipeline type", size=12, color=MUTED, weight=ft.FontWeight.W_700),
                                    pipeline_mode,
                                ],
                            ),
                            col={"xs": 12},
                        ),
                        ft.Container(note_input, col={"xs": 12}),
                    ],
                ),
                status_text,
            ],
        ),
    )


def analytics_panel(kpi_grid: ft.ResponsiveRow) -> ft.Control:
    return panel(
        "Overview",
        "Key spending numbers for the active filters.",
        kpi_grid,
        ft.Icons.QUERY_STATS,
        {"xs": 12},
    )


def sql_panel(sql_text: ft.Text) -> ft.Control:
    return panel(
        "Pipeline SQL",
        "Shows the SQL used by the selected expense pipeline.",
        ft.Container(
            bgcolor="#F8FAF8",
            border=ft.Border.all(1, BORDER),
            border_radius=8,
            padding=14,
            content=ft.Row(
                width=float('inf'),
                scroll=ft.ScrollMode.AUTO,
                controls=[sql_text],
            ),
        ),
        ft.Icons.TABLE_CHART,
        {"xs": 12},
    )


def chart_panel(title: str, subtitle: str, body: ft.Control, icon, col: dict) -> ft.Control:
    return panel(title, subtitle, body, icon, col)


def table_panel(title: str, subtitle: str, data_table: ft.DataTable, col: dict) -> ft.Control:
    return panel(
        title,
        subtitle,
        ft.Row([data_table], scroll=ft.ScrollMode.AUTO),
        ft.Icons.TABLE_ROWS if hasattr(ft.Icons, "TABLE_ROWS") else ft.Icons.RECEIPT_LONG,
        col,
    )


def panel(title: str, subtitle: str, body: ft.Control, icon, col: dict) -> ft.Control:
    return ft.Container(
        col=col,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        padding=18,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    wrap=True,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(icon, color=TEAL, size=22),
                                ft.Text(title, size=18, color=INK, weight=ft.FontWeight.W_700),
                            ],
                        ),
                        ft.Text(subtitle, size=12, color=MUTED),
                    ],
                ),
                body,
            ],
        ),
    )


def kpi_tile(label: str, value: str, note: str, icon, soft: str, strong: str) -> ft.Control:
    return ft.Container(
        col={"xs": 12, "sm": 6},
        bgcolor="#FCFDFB",
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    alignment=CENTER,
                    border_radius=8,
                    bgcolor=soft,
                    content=ft.Icon(icon, color=strong, size=22),
                ),
                ft.Column(
                    expand=True,
                    spacing=3,
                    controls=[
                        ft.Text(label, size=12, color=MUTED, weight=ft.FontWeight.W_600),
                        ft.Text(value, size=24, color=INK, weight=ft.FontWeight.W_800),
                        ft.Text(note, size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                ),
            ],
        ),
    )


def bar_chart(items: list[tuple[str, float]], total: float, empty_text: str) -> list[ft.Control]:
    if not items:
        return [
            ft.Container(
                bgcolor="#F8FAF8",
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=14,
                content=ft.Text(empty_text, color=MUTED, size=13),
            )
        ]

    max_value = max((value for _, value in items), default=1) or 1
    chart_height = 148
    bars = []
    for index, (label, value) in enumerate(items[:8]):
        color = CATEGORY_COLORS.get(label, [TEAL, BLUE, GREEN, AMBER, VIOLET, RED][index % 6])
        bar_height = max(10, round(chart_height * (value / max_value)))
        share = f" ({value / total:.0%})" if total and total > max_value else ""
        bars.append(
            ft.Container(
                width=94,
                height=226,
                content=ft.Column(
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(money(value), size=11, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(
                            height=chart_height,
                            alignment=ft.Alignment(0, 1),
                            content=ft.Container(
                                width=34,
                                height=bar_height,
                                bgcolor=color,
                                border_radius=6,
                                tooltip=f"{label}: {money(value)}{share}",
                            ),
                        ),
                        ft.Container(height=1, bgcolor=BORDER),
                        ft.Text(short_label(label), size=11, color=INK, text_align=ft.TextAlign.CENTER, max_lines=2, width=88),
                    ],
                ),
            )
        )

    return [
        ft.Container(
            bgcolor="#F8FAF8",
            border=ft.Border.all(1, BORDER),
            border_radius=8,
            padding=ft.Padding.only(left=10, top=14, right=10, bottom=8),
            content=ft.Row(
                height=236,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.END,
                scroll=ft.ScrollMode.AUTO,
                controls=bars,
            ),
        )
    ]


def short_label(label: str) -> str:
    return label if len(label) <= 12 else f"{label[:11]}..."


def pipeline_pill(mode: str) -> ft.Control:
    normalized = str(mode or "ETL").upper()
    color = VIOLET if normalized == "ELT" else TEAL
    return ft.Container(
        bgcolor=soften(color),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        content=ft.Text(normalized, size=12, color=color, weight=ft.FontWeight.W_700),
    )


def category_pill(category: str) -> ft.Control:
    color = CATEGORY_COLORS.get(category, MUTED)
    return ft.Container(
        bgcolor=soften(color),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        content=ft.Text(category, size=12, color=color, weight=ft.FontWeight.W_700),
    )


def badge(icon, text: str, bgcolor: str, icon_color: str) -> ft.Control:
    return ft.Container(
        bgcolor=bgcolor,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        content=ft.Row(
            tight=True,
            spacing=8,
            controls=[
                ft.Icon(icon, color=icon_color, size=18),
                ft.Text(text, size=12, color=INK),
            ],
        ),
    )


def money(value: float) -> str:
    return f"PHP {value:,.2f}"


def picker_value(iso_date: str) -> datetime:
    try:
        picked = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        picked = date.today()
    return datetime(picked.year, picked.month, picked.day, 12, 0)


def picker_date_iso(event, fallback: str) -> str:
    candidates = [
        getattr(event, "data", None),
        getattr(getattr(event, "control", None), "value", None),
        fallback,
    ]
    for candidate in candidates:
        parsed = parse_picker_date(candidate)
        if parsed:
            return parsed
    return date.today().isoformat()


def parse_picker_date(value) -> str | None:
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return parsed.astimezone().date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if "T" not in text and " " not in text:
                return date.fromisoformat(text[:10]).isoformat()
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parse_picker_date(parsed)
        except ValueError:
            try:
                return date.fromisoformat(text[:10]).isoformat()
            except ValueError:
                return None
    return None


def soften(color: str) -> str:
    if color == TEAL:
        return TEAL_SOFT
    if color == BLUE:
        return BLUE_SOFT
    if color == GREEN:
        return GREEN_SOFT
    if color == AMBER:
        return AMBER_SOFT
    if color == RED:
        return RED_SOFT
    if color == VIOLET:
        return VIOLET_SOFT
    return "#EEF3F4"


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
