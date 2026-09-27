"""Prepare 1990-2024 capacity series for California, Washington, and Oregon."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "existcapacity_annual.csv"
OUTPUT = ROOT / "data" / "capacity_timeseries_ca_wa_or.csv"
STATES = {"CA": "California", "WA": "Washington", "OR": "Oregon"}
FUELS = {
    "Geothermal": "Geothermal",
    "Nuclear": "Nuclear",
    "Coal": "Coal",
    "Hydroelectric": "Hydroelectric",
    "Natural Gas": "Natural gas",
    "Other": "Other",
    "Other Biomass": "Other biomass",
    "Other Gases": "Other gases",
    "Petroleum": "Petroleum",
    "Pumped Storage": "Pumped storage",
    "Solar Thermal and Photovoltaic": "Solar",
    "Wind": "Wind",
    "Wood and Wood Derived Fuels": "Wood-derived fuels",
}


def main():
    raw = pd.read_csv(SOURCE, skiprows=1)
    # Use the industry total only: adding producer subcategories would double count.
    selected = raw.loc[
        raw["State Code"].isin(STATES)
        & raw["Producer Type"].eq("Total Electric Power Industry")
    ].copy()
    selected["Capacity_MW"] = pd.to_numeric(
        selected["Summer Capacity (Megawatts)"].str.replace(",", "", regex=False),
        errors="raise",
    )
    keys = ["State Code", "Year", "Fuel Source"]
    if selected.duplicated(keys).any():
        raise ValueError("Duplicate state-year-fuel observations in source data.")
    years = list(range(int(selected.Year.min()), int(selected.Year.max()) + 1))
    totals = selected.loc[selected["Fuel Source"].eq("All Sources")]
    expected = pd.MultiIndex.from_product([STATES, years], names=keys[:2])
    if not totals.set_index(keys[:2]).index.sort_values().equals(expected.sort_values()):
        raise ValueError("A state-year total is missing; do not infer zero capacity.")
    fuels = selected.loc[~selected["Fuel Source"].eq("All Sources")]
    unknown = set(fuels["Fuel Source"]) - set(FUELS)
    if unknown:
        raise ValueError(f"Unmapped source categories: {unknown}")
    # Absent category rows are explicitly flagged before completing the series.
    # Zero is a storage placeholder for unlisted capacity, not an observed value.
    # The plotting scripts omit nonpositive values on logarithmic axes.
    complete = pd.MultiIndex.from_product([STATES, years, FUELS], names=keys)
    result = fuels.set_index(keys)[["Capacity_MW"]].reindex(complete)
    result["Source_status"] = result.Capacity_MW.map(
        lambda value: "Not listed" if pd.isna(value) else "Reported"
    )
    result["Capacity_MW"] = result.Capacity_MW.fillna(0)
    result = result.reset_index().rename(
        columns={"State Code": "State_code", "Fuel Source": "Source_fuel"}
    )
    result["State"] = result.State_code.map(STATES)
    result["Energy_source"] = result.Source_fuel.map(FUELS)
    result["Capacity_GW"] = result.Capacity_MW / 1000
    result["Highlight"] = result.Energy_source.isin(["Geothermal", "Nuclear"])
    # Retain source totals and the discrepancy as an auditable rounding check.
    sums = fuels.groupby(keys[:2]).Capacity_MW.sum()
    discrepancy = (sums - totals.set_index(keys[:2]).Capacity_MW).abs()
    if discrepancy.max() > 5:
        raise ValueError("Fuel subtotals differ from total capacity by more than 5 MW.")
    if (result.Capacity_MW < 0).any():
        raise ValueError("Negative capacity found.")
    result.to_csv(OUTPUT, index=False)
    print(f"Saved {len(result):,} rows to {OUTPUT}")
    print(f"Maximum source subtotal discrepancy: {discrepancy.max():.1f} MW")


if __name__ == "__main__":
    main()
