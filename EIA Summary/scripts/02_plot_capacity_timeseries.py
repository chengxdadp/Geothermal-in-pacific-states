"""Create English Altair charts with one line per reported energy source.

Run 01_prepare_data.py first. Outputs: standalone HTML, PNG, SVG, Vega-Lite JSON.
"""

from pathlib import Path
import sys

import altair as alt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
# Optional project-local renderer; a normal pip installation works as well.
LOCAL_DEPS = ROOT / ".dependencies"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
OUT = ROOT / "figures"
STATES = ["California", "Washington", "Oregon"]
COLORS = {
    "Geothermal": "#D55E00",
    "Nuclear": "#0072B2",
    "Coal": "#586978",
    "Hydroelectric": "#528F82",
    "Natural gas": "#899DB7",
    "Other": "#B5ADB5",
    "Other biomass": "#A9BA84",
    "Other gases": "#BCC6D4",
    "Petroleum": "#7B859F",
    "Pumped storage": "#8D8D8D",
    "Solar": "#C4B567",
    "Wind": "#7BB29D",
    "Wood-derived fuels": "#71865D",
}
ENERGY_GROUPS = {
    "Renewable": ["Geothermal", "Solar", "Wind", "Hydroelectric", "Wood-derived fuels", "Other biomass"],
    "Non-renewable": ["Nuclear", "Natural gas", "Coal", "Petroleum", "Other gases"],
    "Storage / unclassified": ["Pumped storage", "Other"],
}
GROUP_ORDER = [fuel for fuels in ENERGY_GROUPS.values() for fuel in fuels]
FUEL_GROUP = {fuel: group for group, fuels in ENERGY_GROUPS.items() for fuel in fuels}
NOTE = [
    "Source: existcapacity_annual.csv | Total Electric Power Industry | 1990-2024.",
    "Logarithmic y-axis: zero and unlisted values are omitted; capacity is not electricity generation.",
]


def read_data():
    path = ROOT / "data" / "capacity_timeseries_ca_wa_or.csv"
    if not path.exists():
        raise FileNotFoundError("Run scripts/01_prepare_data.py first.")
    data = pd.read_csv(path)
    data["Energy_group"] = data.Energy_source.map(FUEL_GROUP)
    if data.Energy_group.isna().any():
        raise ValueError("Unclassified energy source: update ENERGY_GROUPS explicitly.")
    return data


def panel(data, state, focus=False):
    subset = data.loc[data.State.eq(state)].copy()
    sources = ["Geothermal", "Nuclear"] if focus else GROUP_ORDER
    if focus:
        subset = subset.loc[subset.Energy_source.isin(sources)]
    # Keep null rows so lines break at zeros/unlisted years instead of bridging them.
    # Preserve the original capacity fields for tooltips and data auditing.
    subset["Plot_capacity_GW"] = subset.Capacity_GW.where(subset.Capacity_GW > 0)
    color = alt.Color(
        "Energy_source:N",
        title="Energy source",
        scale=alt.Scale(domain=sources, range=[COLORS[s] for s in sources]),
        legend=alt.Legend(orient="bottom", columns=2 if focus else 4,
                          labelLimit=180, symbolStrokeWidth=3),
    )
    base = alt.Chart(subset).encode(
        x=alt.X("Year:Q", title="Year", scale=alt.Scale(domain=[1990, 2024], nice=False),
                axis=alt.Axis(values=[1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024],
                              format="d", grid=False, labelAngle=0)),
        y=alt.Y("Plot_capacity_GW:Q", title="Net summer capacity (GW, log scale)",
                scale=alt.Scale(type="log", base=10, zero=False, nice=True),
                axis=alt.Axis(tickCount=5, format="~g")),
        color=color,
        detail="Energy_source:N",
        order="Year:Q",
        tooltip=[alt.Tooltip("State:N", title="State"),
                 alt.Tooltip("Year:Q", title="Year", format="d"),
                 alt.Tooltip("Energy_source:N", title="Energy source"),
                 alt.Tooltip("Energy_group:N", title="Energy group"),
                 alt.Tooltip("Capacity_GW:Q", title="Capacity (GW)", format=".4f"),
                 alt.Tooltip("Capacity_MW:Q", title="Capacity (MW)", format=",.1f"),
                 alt.Tooltip("Source_status:N", title="Source status")],
    )
    # Muted context lines are drawn first; the two focus series stay in front.
    background = base.transform_filter(
        "datum.Energy_source !== 'Geothermal' && datum.Energy_source !== 'Nuclear'"
    ).mark_line(strokeWidth=1.7, opacity=0.8, clip=True, invalid="break-paths-show-domains")
    geothermal = base.transform_filter(
        alt.datum.Energy_source == "Geothermal"
    ).mark_line(strokeWidth=3.5, clip=True, invalid="break-paths-show-domains")
    nuclear = base.transform_filter(
        alt.datum.Energy_source == "Nuclear"
    ).mark_line(strokeWidth=3.5, strokeDash=[8, 4], clip=True, invalid="break-paths-show-domains")
    chart = alt.layer(geothermal, nuclear) if focus else alt.layer(background, geothermal, nuclear)
    subtitles = {
        "California": "Geothermal and nuclear remain visible beneath the larger capacity sources.",
        "Washington": "Geothermal is not listed in the source for any year (not plotted).",
        "Oregon": "Nuclear is unlisted after 1992; geothermal first appears in 2012.",
    }
    if focus:
        subtitles["California"] = "A closer look at geothermal and nuclear capacity."
    return chart.properties(
        width=850, height=280 if focus else 320,
        title=alt.Title(state, subtitle=[subtitles[state]], anchor="start", fontSize=21,
                        subtitleFontSize=12, offset=14),
    )


def style(chart):
    return (chart.configure(font="Arial")
            .configure_view(stroke=None)
            .configure_axis(labelFontSize=12, titleFontSize=13, titlePadding=12,
                            gridColor="#E5E7EB", domainColor="#A5ABB2", tickColor="#A5ABB2")
            .configure_legend(labelFontSize=12, titleFontSize=13, padding=12,
                              rowPadding=7, columnPadding=22)
            .configure_title(color="#172B3A", subtitleColor="#52616B")
            .properties(background="white", padding=22))


def grouped_legend(chart, palette=None, legend_position="bottom"):
    """Replace flat legends with explicit energy-group columns for every export."""
    palette = COLORS if palette is None else palette
    spec = chart.to_dict()
    sources = {row["Energy_source"] for rows in spec.get("datasets", {}).values()
               for row in rows if "Energy_source" in row}

    def hide_legends(node):
        if isinstance(node, dict):
            for channel in ("color", "strokeDash", "shape", "size", "opacity"):
                encoding = node.get("encoding", {}).get(channel)
                if isinstance(encoding, dict) and "field" in encoding:
                    encoding["legend"] = None
            for value in node.values():
                hide_legends(value)
        elif isinstance(node, list):
            for value in node:
                hide_legends(value)

    hide_legends(spec)
    columns = []
    for group, fuels in ENERGY_GROUPS.items():
        fuels = [fuel for fuel in fuels if fuel in sources]
        if not fuels:
            continue
        rows = pd.DataFrame({"Fuel": fuels, "Row": range(len(fuels)),
                             "Color": [palette[fuel] for fuel in fuels]})
        base = alt.Chart(rows).encode(y=alt.Y("Row:O", axis=None, sort="ascending"))
        swatch = base.mark_square(size=100, opacity=1).encode(
            x=alt.value(7), color=alt.Color("Color:N", scale=None, legend=None))
        labels = base.mark_text(align="left", fontSize=12, color="#263746").encode(
            x=alt.value(23), text="Fuel:N")
        columns.append(alt.layer(swatch, labels).properties(
            width=255, height=alt.Step(22),
            title=alt.Title(group, anchor="start", fontSize=14, offset=10)))
    if legend_position == "right":
        legend = alt.vconcat(*columns, spacing=12)
    elif legend_position == "bottom":
        legend = alt.hconcat(*columns, spacing=25)
    else:
        raise ValueError(f"Unsupported legend position: {legend_position}")
    # Move top-level configuration outside the concatenation, retaining titles.
    outer = {key: spec.pop(key) for key in ("config", "title", "padding", "background", "datasets")
             if key in spec}
    spec.pop("$schema", None)
    legend_spec = legend.to_dict()
    outer.setdefault("datasets", {}).update(legend_spec.pop("datasets", {}))
    legend_spec.pop("$schema", None)
    legend_spec.pop("config", None)
    if legend_position == "right":
        combined = {"hconcat": [spec, legend_spec], "spacing": 24,
                    "resolve": {"scale": {"color": "independent"}}, **outer}
        return alt.HConcatChart.from_dict(combined)
    combined = {"vconcat": [spec, legend_spec], "spacing": 28,
                "resolve": {"scale": {"color": "independent"}}, **outer}
    return alt.VConcatChart.from_dict(combined)


def save(chart, stem, include_legend=True, palette=None, legend_position="bottom"):
    if include_legend:
        chart = grouped_legend(chart, palette=palette, legend_position=legend_position)
    folder = OUT / stem
    folder.mkdir(parents=True, exist_ok=True)
    # Keep only the current exports; reruns overwrite these files without backups.
    chart.save(folder / f"{stem}.vl.json")
    chart.save(folder / f"{stem}.html", inline=True)
    chart.save(folder / f"{stem}.svg")
    chart.save(folder / f"{stem}.png", scale_factor=2)
    print(f"Saved figures/{stem}/: HTML, SVG, PNG, Vega-Lite JSON")


def main():
    data = read_data()
    for state in STATES:
        chart = panel(data, state).properties(title=alt.Title(
            f"{state}: Electricity Capacity by Energy Source, 1990-2024",
            subtitle=["Geothermal (orange, solid) and nuclear (blue, dashed) are highlighted.", *NOTE],
            anchor="start", fontSize=21, subtitleFontSize=11, offset=18,
        ))
        save(style(chart), f"{state.lower()}_capacity_timeseries")
    combined = alt.vconcat(*(panel(data, state) for state in STATES), spacing=30).resolve_scale(
        y="independent", color="shared"
    ).properties(title=alt.Title(
        "Electricity Capacity in California, Washington, and Oregon",
        subtitle=["1990-2024 | One line per energy source | Independent logarithmic y-axis scales.",
                  "Geothermal: orange, solid. Nuclear: blue, dashed.", *NOTE],
        anchor="start", fontSize=23, subtitleFontSize=12, offset=24,
    ))
    save(style(combined), "three_states_capacity_timeseries")


if __name__ == "__main__":
    main()
