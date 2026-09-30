"""Strict normalized statement parser. Unsupported layouts require review."""
import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from ml.documents.checks import result


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
            raise ValueError("Expected date, description, debit, credit, balance columns.")
        date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                date = datetime.strptime(str(row[0]).strip(), fmt).date().isoformat()
                break
            except ValueError:
                continue
        if not date:
            raise ValueError("Unsupported transaction date.")
        debit, credit, balance = (money(v) for v in row[2:])
        if min(debit, credit) < 0 or (debit and credit):
            raise ValueError("A transaction must have nonnegative debit/credit, not both.")
        output.append({"date": date, "description": str(row[1]).strip()[:500],
                       "debit": debit, "credit": credit, "balance": balance})
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
        index = next((i for i, line in enumerate(lines) if line.lower().strip() == ",".join(header)), None)
        if index is None:
            raise ValueError("CSV requires date,description,debit,credit,balance header.")
        return normalize(list(csv.reader(io.StringIO("\n".join(lines[index:]))))[1:])
    for table in tables or []:
        if table and [str(v or "").lower().strip() for v in table[0]] == header:
            return normalize(table[1:])
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
        return result("bank_arithmetic", "WARN", "At least two transactions are required to check running balances.")
    bad = [i + 2 for i, (a, b) in enumerate(zip(rows, rows[1:]))
           if abs(a["balance"] - b["debit"] + b["credit"] - b["balance"]) > tolerance]
    return result("bank_arithmetic", "FAIL" if bad else "PASS",
                  "Running balances do not reconcile." if bad else "Running balances reconcile; opening balance is not independently verified.", {"inconsistent_rows": bad})
