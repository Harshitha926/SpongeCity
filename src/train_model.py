"""
Trains a Random Forest classifier to predict flood risk for each grid cell,
using satellite-derived features (elevation, imperviousness, distance to water)
and satellite-derived flood labels (radar-based, false-positive filtered).

Input:
    data/merged_flood_dataset.csv

Output:
    outputs/model2_risk_classifier.pkl
    outputs/sponge_city_risk_scored_dataset.csv
"""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

FEATURES = ["elevation", "impervious", "dist_to_water"]
TARGET = "confirmed_flood_risk"


def train_model(df: pd.DataFrame):
    training_df = df[df["usable_for_training"].eq(1)].copy()
    excluded = len(df) - len(training_df)
    print(f"Rows excluded from training: {excluded}")
    print(
        "  Missing event coverage: "
        f"{((df['flood_event1_has_data'].fillna(0) <= 0) & (df['flood_event2_has_data'].fillna(0) <= 0)).sum()}"
    )
    print(
        "  Missing dry-season coverage: "
        f"{(df['dry_season_water_has_data'].fillna(0) <= 0).sum()}"
    )

    X = training_df[FEATURES]
    y = training_df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300, max_depth=6, class_weight="balanced", random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("=== CLASSIFICATION REPORT ===")
    print(classification_report(y_test, y_pred, target_names=["No Risk", "Flood Risk"]))

    print("=== CONFUSION MATRIX ===")
    print(confusion_matrix(y_test, y_pred))

    print(f"\nROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")

    print("\n=== FEATURE IMPORTANCE ===")
    for f, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
        print(f"{f}: {imp:.3f}")

    return model


def risk_category(score: float) -> str:
    if score < 0.25:
        return "Low"
    elif score < 0.5:
        return "Moderate"
    elif score < 0.75:
        return "High"
    return "Critical"


def recommend(row) -> str:
    if row["risk_category"] == "Low":
        return "none"
    if row["impervious"] > 0.6 and row["risk_category"] in ["High", "Critical"]:
        return "permeable_pavement"
    if row["dist_to_water"] > 500 and row["risk_category"] in ["High", "Critical"]:
        return "recharge_well"
    if row["risk_category"] in ["Moderate", "High", "Critical"]:
        return "rain_garden"
    return "none"


def score_all_cells(df: pd.DataFrame, model) -> pd.DataFrame:
    df = df.copy()
    df["risk_score"] = model.predict_proba(df[FEATURES])[:, 1]
    df["risk_category"] = df["risk_score"].apply(risk_category)
    df["recommendation"] = df.apply(recommend, axis=1)
    return df


def main():
    df = pd.read_csv("data/merged_flood_dataset.csv")

    for column in [
        "flood_event1_has_data",
        "flood_event2_has_data",
        "dry_season_water_has_data",
    ]:
        if column not in df.columns:
            label_column = column.replace("_has_data", "")
            df[column] = df[label_column].fillna(-1).ne(-1).astype(int)

    model = train_model(df)
    scored = score_all_cells(df, model)

    print("\n=== RISK CATEGORY DISTRIBUTION ===")
    print(scored["risk_category"].value_counts())

    print("\n=== RECOMMENDATION DISTRIBUTION ===")
    print(scored["recommendation"].value_counts())

    scored.to_csv("outputs/sponge_city_risk_scored_dataset.csv", index=False)
    joblib.dump(model, "outputs/model2_risk_classifier.pkl")
    print("\nSaved scored dataset and trained model to outputs/")


if __name__ == "__main__":
    main()
