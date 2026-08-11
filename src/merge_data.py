"""
Merges the wet-season (flood event) and dry-season (control) datasets
exported from Google Earth Engine, and filters out false positives
(permanent water bodies) to produce clean flood-risk labels.

Input:
    data/sponge_city_grid_dataset.csv         (from Earth Engine, flood events)
    data/sponge_city_dry_season_control.csv   (from Earth Engine, dry season)

Output:
    data/merged_flood_dataset.csv
"""

import pandas as pd


def _coverage_flag(df: pd.DataFrame, label_column: str) -> pd.Series:
    coverage_column = f"{label_column}_has_data"
    if coverage_column in df.columns:
        return df[coverage_column].fillna(0).gt(0)
    return df[label_column].fillna(-1).ne(-1)


def load_and_merge(grid_path: str, dry_path: str) -> pd.DataFrame:
    dry = pd.read_csv(dry_path)
    dry = dry.rename(
        columns={
            "mean": "dry_season_water",
            "mean_has_data": "dry_season_water_has_data",
        }
    )
    main = pd.read_csv(grid_path)

    dry_columns = ["system:index", "dry_season_water"]
    if "dry_season_water_has_data" in dry.columns:
        dry_columns.append("dry_season_water_has_data")

    merged = main.merge(
        dry[dry_columns], on="system:index", how="left"
    )
    return merged


def apply_flood_labels(df: pd.DataFrame, flood_threshold: float = 0.3) -> pd.DataFrame:
    """
    A cell counts as 'flooded' if either radar flood event shows a strong signal.
    A cell is a 'false positive' if it's also wet during the dry season
    (i.e. it's a permanent lake/waterbody, not real flood risk).
    """
    event1_has_data = _coverage_flag(df, "flood_event1")
    event2_has_data = _coverage_flag(df, "flood_event2")
    dry_has_data = _coverage_flag(df, "dry_season_water")
    event_has_data = event1_has_data | event2_has_data
    df["usable_for_training"] = (event_has_data & dry_has_data).astype(int)

    flooded = (df["flood_event1"] > flood_threshold) | (
        df["flood_event2"] > flood_threshold
    )
    df["flooded_either"] = flooded.where(df["usable_for_training"].eq(1), pd.NA).astype("Int64")

    false_positive = (
        (df["flooded_either"] == 1) & (df["dry_season_water"] > flood_threshold)
    )
    df["false_positive_suspect"] = false_positive.where(
        df["usable_for_training"].eq(1), pd.NA
    ).astype("Int64")

    confirmed = (
        (df["flooded_either"] == 1) & (df["false_positive_suspect"] == 0)
    )
    df["confirmed_flood_risk"] = confirmed.where(
        df["usable_for_training"].eq(1), pd.NA
    ).astype("Int64")

    return df


def main():
    df = load_and_merge(
        "data/sponge_city_grid_dataset.csv",
        "data/sponge_city_dry_season_control.csv",
    )
    df = apply_flood_labels(df)

    df.to_csv("data/merged_flood_dataset.csv", index=False)

    total = len(df)
    usable = df["usable_for_training"].eq(1)
    flooded = df.loc[usable, "confirmed_flood_risk"].sum()
    event_coverage = _coverage_flag(df, "flood_event1") | _coverage_flag(df, "flood_event2")
    dry_coverage = _coverage_flag(df, "dry_season_water")
    print(f"Total grid cells: {total}")
    print(f"Usable for training: {usable.sum()}")
    print(f"Excluded from training: {(~usable).sum()}")
    print(f"  Excluded for missing event coverage: {(~event_coverage).sum()}")
    print(f"  Excluded for missing dry-season coverage: {(~dry_coverage).sum()}")
    print(f"Confirmed flood-risk cells: {flooded} ({flooded/usable.sum()*100:.1f}%)")
    print("Saved to data/merged_flood_dataset.csv")


if __name__ == "__main__":
    main()
