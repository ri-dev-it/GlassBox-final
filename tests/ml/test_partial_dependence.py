import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml")))

from explainability import partial_dependence


def test_global_partial_dependence_serializes_numeric_curves(monkeypatch):
    def fake_partial_dependence(*_args, **_kwargs):
        return {"grid_values": [pd.Series([1, 2])], "average": [[0.8, 0.3], [0.2, 0.7]]}

    monkeypatch.setattr("sklearn.inspection.partial_dependence", fake_partial_dependence)
    result = partial_dependence.global_partial_dependence(object(), pd.DataFrame({"duration_months": [1, 2]}), ["duration_months"])
    assert result[0]["feature"] == "duration_months"
    assert result[0]["points"] == [{"value": 1.0, "approval_probability": 0.2}, {"value": 2.0, "approval_probability": 0.7}]