"""Export a detailed view of the two highlighted energy sources using Altair."""

from pathlib import Path
import runpy

import altair as alt


def main():
    # Reuse the numbered plotting script without executing its main function.
    shared = runpy.run_path(str(Path(__file__).with_name("02_plot_capacity_timeseries.py")))
    data = shared["read_data"]()
    chart = alt.vconcat(
        *(shared["panel"](data, state, focus=True) for state in shared["STATES"]),
        spacing=30,
    ).resolve_scale(y="independent", color="shared").properties(title=alt.Title(
        "Geothermal and Nuclear Capacity in Three Pacific States",
        subtitle=["1990-2024 | Orange solid: geothermal | Blue dashed: nuclear",
                  "Each panel uses its own logarithmic y-axis scale.",
                  *shared["NOTE"]],
        anchor="start", fontSize=23, subtitleFontSize=12, offset=24,
    ))
    shared["save"](shared["style"](chart), "geothermal_nuclear_focus")


if __name__ == "__main__":
    main()
