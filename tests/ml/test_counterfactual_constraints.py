import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml")))

from counterfactual.constraints import CONSTRAINT_NOTE, violates_dependency_constraints


def test_dependency_constraints_reject_incompatible_profiles():
    assert violates_dependency_constraints({"credit_amount": 15000, "duration_months": 6})
    assert violates_dependency_constraints({"employment_since": "unemployed", "job": "skilled employee/official"})
    assert violates_dependency_constraints({"housing": "own", "property": "unknown/no property"})
    assert violates_dependency_constraints({"installment_rate_percent": 4, "credit_amount": 15000})
    assert not violates_dependency_constraints({"credit_amount": 15000, "duration_months": 24, "housing": "own", "property": "real estate"})
    assert "dependency checks" in CONSTRAINT_NOTE