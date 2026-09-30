"""Cross-document checks; missing evidence never counts as a pass."""
import re
from .checks import result
from .identity import name_score


def cross_checks(salary, income, transactions, salary_tolerance=0.02, annual_tolerance=0.20):
    checks = []
    salary = salary or {}
    income = income or {}
    net, period = salary.get("net_pay"), salary.get("pay_period")
    matching = []
    if not net or not period or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period) or not transactions:
        checks.append(result("salary_bank_credit", "WARN", "Net pay, YYYY-MM pay period and bank transactions are required."))
    else:
        rows = [r for r in transactions if r["date"][:7] == period]
        matching = [r for r in rows if r["credit"] > 0 and abs(r["credit"] - net) <= net * salary_tolerance]
        status = "PASS" if matching else "FAIL" if rows else "WARN"
        checks.append(result("salary_bank_credit", status,
            "Net salary appears as a credit in the pay month." if matching else "No matching salary credit in the observed pay month." if rows else "Bank statement does not cover the salary month.",
            {"pay_period": period, "relative_tolerance": salary_tolerance, "matching_credits": len(matching)}))
    gross, annual = salary.get("gross"), income.get("annual_income")
    if not gross or annual is None:
        checks.append(result("annual_income", "WARN", "Gross salary and certificate annual income are required."))
    else:
        difference = abs(annual - gross * 12) / (gross * 12)
        checks.append(result("annual_income", "PASS" if difference <= annual_tolerance else "FAIL",
                             "Certificate income agrees with annualized gross salary." if difference <= annual_tolerance else "Certificate annual income differs from annualized gross salary.",
                             {"relative_difference": round(difference, 4), "relative_tolerance": annual_tolerance}))
    employer = salary.get("employer")
    if employer and matching:
        tokens = set(re.findall(r"[a-z]+", employer.lower()))
        found = any(tokens <= set(re.findall(r"[a-z]+", row["description"].lower())) for row in matching)
        checks.append(result("employer_bank", "PASS" if found else "WARN",
                             "Employer appears in the matching credit description." if found else "Employer cannot be confirmed from the matching credit description."))
    if employer and income.get("employer"):
        matches = name_score(employer, income["employer"]) >= 88
        checks.append(result("employer_certificate", "PASS" if matches else "FAIL", "Employer labels agree." if matches else "Employer labels differ."))
    return checks
