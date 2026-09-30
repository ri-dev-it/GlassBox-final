from ml.documents.consistency import cross_checks


def test_cross_document_pass_and_fail():
    salary = {"gross": 50000, "net_pay": 45000, "pay_period": "2026-01", "employer": "Example Labs"}
    income = {"annual_income": 600000}
    transactions = [{"date": "2026-01-05", "credit": 45000, "description": "Salary Example Labs"}]
    assert all(c['status'] == 'PASS' for c in cross_checks(salary, income, transactions))
    income['annual_income'] = 100000
    transactions[0]['credit'] = 30000
    checks = cross_checks(salary, income, transactions)
    assert sum(c['status'] == 'FAIL' for c in checks) == 2


def test_missing_coverage_and_tolerances():
    salary = {"gross": 50000, "net_pay": 45000, "pay_period": "2026-01"}
    income = {"annual_income": 650000}
    transactions = [{"date": "2026-02-05", "credit": 45000, "description": "Salary"}]
    assert cross_checks(salary, income, transactions)[0]['status'] == 'WARN'
    transactions[0]['date'] = '2026-01-05'
    transactions[0]['credit'] = 44500
    assert cross_checks(salary, income, transactions, 0.02, 0.20)[0]['status'] == 'PASS'
    assert cross_checks(salary, income, transactions, 0.001, 0.01)[0]['status'] == 'FAIL'
    assert all(c['status'] == 'WARN' for c in cross_checks({}, {}, []))
