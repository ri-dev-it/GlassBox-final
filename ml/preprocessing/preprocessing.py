"""
Reusable preprocessing pipeline.

CRITICAL: the exact same fitted pipeline built here is used at both
training time and prediction time (it's saved *inside* the joblib
artifact alongside the model as one sklearn Pipeline). The prediction
API never reimplements preprocessing separately -- see
ml/prediction/predictor.py, which just calls pipeline.predict() on the
raw applicant dict. This avoids train/serve skew and data leakage.
"""

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

from preprocessing.feature_config import NUMERIC_FEATURES, CATEGORICAL_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """
    Numeric features: median-impute then standard-scale.
    Categorical features: most-frequent-impute then one-hot encode.
    """
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor


def get_feature_names_out(preprocessor: ColumnTransformer) -> list[str]:
    """Readable post-transform feature names, used by SHAP/LIME output."""
    return list(preprocessor.get_feature_names_out())
