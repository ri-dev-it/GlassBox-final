"""Strict normalized statement parser. Unsupported layouts require review."""

import csv
import io
import re
from datetime import datetime
from datetime import date, timedelta
from collections import defaultdict
from statistics import mean, pstdev
from decimal import Decimal, InvalidOperation
from .checks import result
from .identity import mask_identifiers

BANK_FEATURES = [
    "avg_monthly_credits",
    "salary_regularity",
    "avg_monthly_balance",
    "min_monthly_balance",
    "emi_debit_count",
    "emi_debit_share",
    "fixed_obligation_to_income_ratio",
    "bounced_payment_count",
    "cash_withdrawal_share",
    "negative_balance_days",
    "transaction_velocity",
    "income_volatility",
]


def extract_bank_header(text):
    """Read labeled header fields only; never infer a holder from transaction
    names."""
    header = re.split(
        r"(?im)^\s*date\s*[,|\s]+.*(?:debit|credit|balance)", text, maxsplit=1
    )[0]
    labels = {
        "account_holder": (
            r"account\s+holder(?:\s+name)?|account\s+name|customer\s+name|name"
        ),
        "account_number": r"account\s*(?:number|no\.?)|a/c\s*(?:number|no\.?)",
        "bank_name": r"bank\s+name|bank",
        "branch": r"branch(?:\s+name)?",
        "ifsc": r"ifsc(?:\s+code)?",
    }
    fields = {}
    for key, label in labels.items():
        match = re.search(
            r"^[ \t]*(?:" + label + r")[ \t]*[:=\-][ \t]*([^\r\n]+)",
            header,
            re.I | re.M,
        )
        value = match.group(1).strip() if match else None
        if key == "account_number":
            number = re.sub(r"[\s-]", "", value or "")
            fields[key] = (
                "*" * max(4, len(number) - 4) + number[-4:]
                if re.fullmatch(r"[\dXx*]{5,30}", number)
                and number[-4:].isdigit()
                else None
            )
        elif key == "ifsc":
            code = re.search(
                r"\b[A-Z]{4}0[A-Z0-9]{6}\b", (value or "").upper()
            )
            fields[key] = code.group() if code else None
        else:
            fields[key] = mask_identifiers(value)[:150] if value else None
    return fields


def money(value):
    value = str(value or "0").replace(",", "").strip()
    try:
        number = Decimal(value)
        if not number.is_finite() or abs(number) > Decimal("100000000000"):
            raise ValueError("Invalid transaction amount.")
        return float(number)
    except InvalidOperation:
        raise ValueError("Invalid transaction amount.") from None


def normalize(rows):
    output = []
    for row in rows:
        if not row or not any(str(v or "").strip() for v in row):
            continue
        if len(row) != 5:
            raise ValueError(
                "Expected date, description, debit, credit, balance columns."
            )
        date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                date = (
                    datetime.strptime(str(row[0]).strip(), fmt)
                    .date()
                    .isoformat()
                )
                break
            except ValueError:
                continue
        if not date:
            raise ValueError("Unsupported transaction date.")
        debit, credit, balance = (money(v) for v in row[2:])
        if min(debit, credit) < 0 or (debit and credit):
            raise ValueError(
                "A transaction must have nonnegative debit/credit, not both."
            )
        output.append(
            {
                "date": date,
                "description": str(row[1]).strip()[:500],
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
        )
    if len(output) > 10000:
        raise ValueError("Statement exceeds 10000 transactions.")
    if any(a["date"] > b["date"] for a, b in zip(output, output[1:])):
        if all(a["date"] >= b["date"] for a, b in zip(output, output[1:])):
            output.reverse()
        else:
            raise ValueError("Transactions must be in chronological order.")
    return output


def parse_statement(text, tables=None, csv_mode=False):
    header = ["date", "description", "debit", "credit", "balance"]
    if csv_mode:
        lines = text.splitlines()
        index = next(
            (
                i
                for i, line in enumerate(lines)
                if line.lower().strip() == ",".join(header)
            ),
            None,
        )
        if index is None:
            raise ValueError(
                "CSV requires date,description,debit,credit,balance header."
            )
        return normalize(
            list(csv.reader(io.StringIO("\n".join(lines[index:]))))[1:]
        )
    table_rows = []
    for table in tables or []:
        if (
            table
            and [str(v or "").lower().strip() for v in table[0]] == header
        ):
            table_rows.extend(table[1:])
    if table_rows:
        return normalize(table_rows)
    rows = []
    for line in text.splitlines():
        if re.match(r"^\d{4}-\d{2}-\d{2}\b|^\d{2}/\d{2}/\d{4}\b", line):
            parts = line.split()
            if len(parts) < 5:
                raise ValueError("Incomplete transaction row.")
            rows.append([parts[0], " ".join(parts[1:-3]), *parts[-3:]])
    return normalize(rows)


def balance_check(rows, tolerance=0.02):
    if len(rows) < 2:
        return result(
            "bank_arithmetic",
            "WARN",
            "At least two transactions are required to check running"
            " balances.",
        )
    bad = [
        i + 2
        for i, (a, b) in enumerate(zip(rows, rows[1:]))
        if abs(a["balance"] - b["debit"] + b["credit"] - b["balance"])
        > tolerance
    ]
    return result(
        "bank_arithmetic",
        "FAIL" if bad else "PASS",
        (
            "Running balances do not reconcile."
            if bad
            else (
                "Running balances reconcile; opening balance is not"
                " independently verified."
            )
        ),
        {"inconsistent_rows": bad},
    )


def bank_features(rows):
    """Observed-window daily balances; zero-activity months remain in
    denominators."""
    if not rows:
        return {key: None for key in BANK_FEATURES}
    first, last = date.fromisoformat(rows[0]["date"]), date.fromisoformat(
        rows[-1]["date"]
    )
    if (last - first).days > 3660:
        raise ValueError("Statement spans more than ten years.")
    credits, daily, closing = defaultdict(float), defaultdict(list), {}
    for row in rows:
        credits[row["date"][:7]] += row["credit"]
        closing[row["date"]] = row["balance"]
    day, balance, negative = first, rows[0]["balance"], 0
    while day <= last:
        balance = closing.get(day.isoformat(), balance)
        daily[day.strftime("%Y-%m")].append(balance)
        negative += balance < 0
        day += timedelta(days=1)
    monthly_credits = [credits[month] for month in daily]
    monthly_balances = [mean(values) for values in daily.values()]
    debits = [r for r in rows if r["debit"] > 0]
    obligations = [
        r
        for r in debits
        if re.search(r"\bemi\b|\bloan\b|installment", r["description"], re.I)
    ]
    cash = sum(
        r["debit"]
        for r in debits
        if re.search(r"\batm\b|cash withdrawal", r["description"], re.I)
    )
    total_credit, total_debit = sum(monthly_credits), sum(
        r["debit"] for r in debits
    )
    recurring = [
        r
        for r in rows
        if r["credit"] > 0
        and re.search(r"salary|payroll", r["description"], re.I)
    ]
    regularity = max(
        (
            len(
                {
                    r["date"][:7]
                    for r in recurring
                    if abs(r["credit"] - candidate["credit"])
                    <= candidate["credit"] * 0.1
                }
            )
            for candidate in recurring
        ),
        default=0,
    )
    values = [
        mean(monthly_credits),
        regularity,
        mean(monthly_balances),
        min(min(v) for v in daily.values()),
        len(obligations),
        len(obligations) / len(debits) if debits else 0,
        (
            sum(r["debit"] for r in obligations) / total_credit
            if total_credit
            else None
        ),
        sum(
            bool(
                re.search(
                    r"bounce|bounced|returned|dishonou?r|\bnsf\b",
                    r["description"],
                    re.I,
                )
            )
            for r in rows
        ),
        cash / total_debit if total_debit else 0,
        negative,
        sum(bool(r["debit"] or r["credit"]) for r in rows)
        / ((last - first).days + 1),
        (
            pstdev(monthly_credits) / mean(monthly_credits)
            if total_credit
            else None
        ),
    ]
    return {
        key: round(float(value), 6) if value is not None else None
        for key, value in zip(BANK_FEATURES, values)
    }
