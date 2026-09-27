"""Compare absolute capacity changes (2024 minus 2000), not a time series."""

from pathlib import Path
import runpy
import json

import altair as alt
import pandas as pd


def main():
    shared = runpy.run_path(str(Path(__file__).with_name("02_plot_capacity_timeseries.py")))
    data = shared["read_data"]()
    keys = ["State", "Energy_source"]
    start = data.loc[data.Year.eq(2000), keys + ["Capacity_GW", "Source_status"]]
    end = data.loc[data.Year.eq(2024), keys + ["Capacity_GW", "Source_status"]]
    change = start.merge(end, on=keys, suffixes=("_2000", "_2024"), validate="one_to_one")
    if len(change) != 39:
        raise ValueError("Expected 13 energy sources for each of three states.")
    change["Change_GW"] = change.Capacity_GW_2024 - change.Capacity_GW_2000
    change["Energy_group"] = change.Energy_source.map(shared["FUEL_GROUP"])
    change["Label"] = change.Change_GW.map(lambda v: "0.0000" if v == 0 else f"{v:+.4f}")
    change.to_csv(shared["ROOT"] / "data" / "capacity_change_2000_2024.csv", index=False)
    order = shared["GROUP_ORDER"]
    # Extra category rows act as bold group headings directly on the y-axis.
    groups = list(shared["ENERGY_GROUPS"])
    grouped_rows = [item for group, fuels in shared["ENERGY_GROUPS"].items()
                    for item in [group, *fuels]]
    is_heading = f"indexof({json.dumps(groups)}, datum.label) >= 0"
    panels = []
    for i, state in enumerate(shared["STATES"]):
        base = alt.Chart(change.loc[change.State.eq(state)]).encode(
            x=alt.X("Change_GW:Q", title="Capacity change (GW)",
                    scale=alt.Scale(domain=[-9, 27], nice=False),
                    axis=alt.Axis(values=[-5, 0, 5, 10, 15, 20, 25], format="~g")),
            y=alt.Y("Energy_source:N", sort=grouped_rows, title=None,
                    scale=alt.Scale(domain=grouped_rows),
                    axis=alt.Axis(labels=i == 0, ticks=False, domain=False, labelLimit=185,
                                  labelAlign="left",
                                  labelPadding=alt.ExprRef(expr=f"{is_heading} ? 190 : 178"),
                                  labelFontWeight=alt.ExprRef(expr=f"{is_heading} ? 'bold' : 'normal'"),
                                  labelColor=alt.ExprRef(expr=f"{is_heading} ? '#172B3A' : '#3D4B57'"))),
            color=alt.Color("Energy_source:N", title="Energy source",
                            scale=alt.Scale(domain=order, range=[shared["COLORS"][s] for s in order]),
                            legend=None),
            tooltip=[alt.Tooltip("State:N", title="State"),
                     alt.Tooltip("Energy_source:N", title="Energy source"),
                     alt.Tooltip("Energy_group:N", title="Energy group"),
                     alt.Tooltip("Capacity_GW_2000:Q", title="2000 capacity (GW)", format=".4f"),
                     alt.Tooltip("Capacity_GW_2024:Q", title="2024 capacity (GW)", format=".4f"),
                     alt.Tooltip("Change_GW:Q", title="Change (GW)", format="+.4f"),
                     alt.Tooltip("Source_status_2000:N", title="2000 source status"),
                     alt.Tooltip("Source_status_2024:N", title="2024 source status")],
        )
        zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
            color="#55616C", strokeWidth=1
        ).encode(x="zero:Q")
        separators = alt.Chart(pd.DataFrame({"Energy_source": groups})).mark_rule(
            color="#DCE2E7", strokeWidth=1
        ).encode(y=base.encoding.y)
        bars = base.mark_bar(size=16)
        # Endpoint dots keep very small changes and exact zeros visible.
        points = base.mark_point(filled=True, size=22, opacity=1)
        positive = base.transform_filter(alt.datum.Change_GW >= 0).mark_text(
            align="left", dx=7, fontSize=11, color="#263746"
        ).encode(text="Label:N", color=alt.value("#263746"))
        negative = base.transform_filter(alt.datum.Change_GW < 0).mark_text(
            align="right", dx=-7, fontSize=11
        ).encode(text="Label:N", color=alt.value("#263746"))
        panels.append(alt.layer(separators, zero, bars, points, positive, negative).properties(
            width=310, height=alt.Step(30),
            # Align titles to the plot area, excluding the wide grouped y labels.
            title=alt.Title(state, anchor="middle", frame="group", fontSize=21, offset=15),
        ))
    chart = alt.hconcat(*panels, spacing=28).resolve_scale(
        x="shared", y="shared", color="shared"
    ).properties(title=alt.Title(
        "Change in Electricity Capacity, 2000 to 2024",
        anchor="middle", fontSize=24, subtitleFontSize=12, offset=24,
    ))
    shared["save"](shared["style"](chart), "three_states_capacity_change_2000_2024",
                   include_legend=False)


if __name__ == "__main__":
    main()
