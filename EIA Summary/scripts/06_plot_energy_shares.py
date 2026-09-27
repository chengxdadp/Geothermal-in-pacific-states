"""Add a 100% stacked bar chart of the three states' 2024 capacity mix."""

from pathlib import Path
import runpy

import altair as alt


# Renewable sources use greens, non-renewable sources use yellows and golds.
# The two sources outside those groups use neutral grays.
SHARE_COLORS = {
    "Geothermal": "#005A32", "Solar": "#BAE4B3", "Wind": "#74C476",
    "Hydroelectric": "#238B45", "Wood-derived fuels": "#3E6C42",
    "Other biomass": "#E5F5E0", "Nuclear": "#8B5E00", "Natural gas": "#F5C400",
    "Coal": "#C49A00", "Petroleum": "#FFE17B", "Other gases": "#E6B85C",
    "Pumped storage": "#676767", "Other": "#CCCCCC",
}


def main():
    shared = runpy.run_path(str(Path(__file__).with_name("02_plot_capacity_timeseries.py")))
    data = shared["read_data"]()
    data = data.loc[data.Year.eq(2024)].copy()
    # Normalize by the sum of fuel categories, avoiding source-total rounding drift.
    data["Total_capacity_GW"] = data.groupby("State").Capacity_GW.transform("sum")
    data["Share"] = data.Capacity_GW / data.Total_capacity_GW
    # Keep renewable and non-renewable sources adjacent within the stack.
    order = shared["GROUP_ORDER"]
    data["Stack_order"] = data.Energy_source.map({fuel: i for i, fuel in enumerate(order)})
    data = data.sort_values(["State", "Stack_order"])
    data["Upper"] = data.groupby("State").Share.cumsum()
    data["Lower"] = data.Upper - data.Share
    data["Midpoint"] = (data.Lower + data.Upper) / 2
    data["Share_percent"] = data.Share * 100
    if len(data) != 39 or not data.groupby("State").Share.sum().between(0.999999, 1.000001).all():
        raise ValueError("Expected 13 categories per state with shares totaling 100%.")
    data.to_csv(shared["ROOT"] / "data" / "energy_shares_2024.csv", index=False)
    x = alt.X("State:N", sort=shared["STATES"], title="State",
              scale=alt.Scale(paddingInner=0.42, paddingOuter=0.25),
              axis=alt.Axis(labelAngle=0, labelFontSize=15, labelPadding=10, ticks=False))
    bars = alt.Chart(data).mark_bar().encode(
        x=x,
        y=alt.Y("Share:Q", stack="zero", title="Share of net summer capacity (%)",
                scale=alt.Scale(domain=[0, 1], nice=False),
                axis=alt.Axis(values=[0, 0.2, 0.4, 0.6, 0.8, 1], format=".0%")),
        color=alt.Color("Energy_source:N", title="Energy source",
                        scale=alt.Scale(domain=order, range=[SHARE_COLORS[s] for s in order]),
                        legend=None),
        order=alt.Order("Stack_order:Q", sort="ascending"),
        tooltip=[alt.Tooltip("State:N", title="State"),
                 alt.Tooltip("Energy_source:N", title="Energy source"),
                 alt.Tooltip("Energy_group:N", title="Energy group"),
                 alt.Tooltip("Share:Q", title="Capacity share", format=".2%"),
                 alt.Tooltip("Capacity_GW:Q", title="Capacity (GW)", format=".4f"),
                 alt.Tooltip("Total_capacity_GW:Q", title="Total of fuel categories (GW)", format=".4f"),
                 alt.Tooltip("Source_status:N", title="Source status")],
    )
    boundaries = data.groupby(["State", "Energy_group"], as_index=False).Upper.max()
    boundaries = boundaries.loc[boundaries.Upper < 0.999999]
    separators = alt.Chart(boundaries).mark_tick(
        orient="horizontal", color="white", thickness=2, size=150
    ).encode(x=x, y=alt.Y("Upper:Q"))
    # Geothermal segments are only 1.94% in CA and 0.11% in OR. Place one
    # label close to each segment and connect it to the segment's true top edge.
    geothermal = data.loc[data.Energy_source.eq("Geothermal") & data.Capacity_GW.gt(0)].copy()
    geothermal["Focus_label"] = geothermal.Share.map(lambda value: f"Geothermal {value:.2%}")
    geothermal["Callout_y"] = geothermal.Upper.clip(lower=0.01) + 0.035
    geothermal["Leader_top"] = geothermal.Callout_y - 0.013
    leaders = alt.Chart(geothermal).mark_rule(
        color="#005A32", strokeWidth=1.6,
    ).encode(x=x, y=alt.Y("Upper:Q", scale=alt.Scale(domain=[0, 1], nice=False)),
             y2="Leader_top:Q")
    anchors = alt.Chart(geothermal).mark_point(
        filled=True, color="#005A32", size=42,
    ).encode(x=x, y=alt.Y("Upper:Q", scale=alt.Scale(domain=[0, 1], nice=False)))
    annotations = alt.Chart(geothermal).mark_text(
        fontSize=13, fontWeight="bold", color="#005A32",
    ).encode(x=x, y=alt.Y("Callout_y:Q", scale=alt.Scale(domain=[0, 1], nice=False)),
             text="Focus_label:N")
    chart = alt.layer(bars, separators, leaders, anchors, annotations).properties(
        width=800, height=420,
        title=alt.Title(
        "Electricity Capacity Mix in Three Pacific States, 2024",
        anchor="middle", fontSize=23, offset=22,
        ),
    )
    shared["save"](shared["style"](chart), "three_states_energy_shares_2024",
                   palette=SHARE_COLORS, legend_position="right")


if __name__ == "__main__":
    main()
