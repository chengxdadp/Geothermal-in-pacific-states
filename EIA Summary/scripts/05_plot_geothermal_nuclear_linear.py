"""Add a linear-scale geothermal/nuclear time series; preserve existing figures."""

from pathlib import Path
import runpy

import altair as alt


def main():
    shared = runpy.run_path(str(Path(__file__).with_name("02_plot_capacity_timeseries.py")))
    data = shared["read_data"]()
    data = data.loc[data.Energy_source.isin(["Geothermal", "Nuclear"])].copy()
    panels = []
    for state in shared["STATES"]:
        subset = data.loc[data.State.eq(state)]
        latest = subset.loc[subset.Year.eq(2024)].set_index("Energy_source")
        notes = []
        for fuel in ["Geothermal", "Nuclear"]:
            row = latest.loc[fuel]
            value = f"{row.Capacity_MW:,.1f} MW" if row.Source_status == "Reported" else "unlisted (shown as 0)"
            notes.append(f"2024 {fuel.lower()}: {value}")
        chart = alt.Chart(subset).mark_line(strokeWidth=3, clip=True).encode(
            x=alt.X("Year:Q", title="Year", scale=alt.Scale(domain=[1990, 2024], nice=False),
                    axis=alt.Axis(values=[1990, 2000, 2010, 2024], format="d", grid=False)),
            y=alt.Y("Capacity_GW:Q", title="Net summer capacity (GW)",
                    scale=alt.Scale(type="linear", zero=True), axis=alt.Axis(tickCount=5)),
            color=alt.Color("Energy_source:N", title="Energy source",
                            scale=alt.Scale(domain=["Geothermal", "Nuclear"], range=["#D55E00", "#0072B2"]),
                            legend=alt.Legend(orient="bottom", columns=2)),
            strokeDash=alt.StrokeDash("Energy_source:N", title="Energy source",
                                     scale=alt.Scale(domain=["Geothermal", "Nuclear"], range=[[1, 0], [8, 4]])),
            order="Year:Q",
            tooltip=[alt.Tooltip("State:N", title="State"),
                     alt.Tooltip("Year:Q", title="Year", format="d"),
                     alt.Tooltip("Energy_source:N", title="Energy source"),
                     alt.Tooltip("Energy_group:N", title="Energy group"),
                     alt.Tooltip("Capacity_GW:Q", title="Capacity (GW)", format=".4f"),
                     alt.Tooltip("Capacity_MW:Q", title="Capacity (MW)", format=",.1f"),
                     alt.Tooltip("Source_status:N", title="Source status")],
        ).properties(width=330, height=300, title=alt.Title(
            state, subtitle=notes, anchor="start", fontSize=21, subtitleFontSize=12, offset=16,
        ))
        panels.append(chart)
    chart = alt.hconcat(*panels, spacing=35).resolve_scale(
        y="independent", color="shared", strokeDash="shared"
    ).properties(title=alt.Title(
        "Geothermal and Nuclear Capacity, 1990-2024",
        subtitle=["California, Washington, and Oregon | Geothermal: orange, solid. Nuclear: blue, dashed.",
                  "Linear y-axes start at zero; each panel uses its own y-axis range.",
                  "Source: existcapacity_annual.csv | Total Electric Power Industry | Net summer capacity.",
                  "Unlisted state-year fuel categories are shown as 0; capacity is not electricity generation."],
        anchor="start", fontSize=24, subtitleFontSize=12, offset=24,
    ))
    shared["save"](shared["style"](chart), "geothermal_nuclear_linear_timeseries")


if __name__ == "__main__":
    main()
