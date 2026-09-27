import geopandas as gpd
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shapely
from shapely import Point, LineString, Polygon
from matplotlib.colors import LogNorm
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D


PATH = r'/users/samlerner/Desktop/DataViz/GeoTherm'

# =============================================================================
#Setting up Geothermal Favorability Map (Base)
mappath = os.path.join(PATH, 'Favorability/FavorabilitySurface.shp')
geomap = gpd.read_file(mappath)

#alreade a gdf so checking crs
geomap.crs
#PROJCS["NAD_1983_Albers",GEOGCS["NAD83"]
geomap = geomap.to_crs("EPSG:4326") #universal crs for my map

#Putting values in order for vizualization so it is on the correct scale
value_order = [ 
    '< 0.1', '0.1 - 0.5', '0.5 - 1', '1 - 2', '2 - 3',
    '3 - 4', '4 - 5', '5 - 10', '10 - 15', '> 15'
]
geomap['index'] = pd.Categorical(
    geomap['Descript'],
    categories=value_order,
    ordered=True
)

n_bins = len(value_order)
cmap = plt.get_cmap("viridis")
norm = mcolors.Normalize(vmin=0, vmax=n_bins - 1)
geomap["index_code"] = geomap["index"].cat.codes
# =============================================================================
#Loading map data
#Reading in cleaned data
geothermpath = os.path.join(PATH, 'geoplant_cleaned.csv')
geotherm = pd.read_csv(geothermpath)

nuclearpath = os.path.join(PATH, 'nuclear_cleaned.csv')
nuclear = pd.read_csv(nuclearpath)

translpath = os.path.join(PATH, 'Transmission/transline_cleaned.shp')
lines = gpd.read_file(translpath)

poppath = os.path.join(PATH, 'citycoords.csv')
cities = pd.read_csv(poppath)

statespath = os.path.join(PATH, 'States/states_cleaned.shp')
states = gpd.read_file(statespath)

#converting point data to geodataframes
nuclear = gpd.GeoDataFrame(
    nuclear, 
    geometry=gpd.points_from_xy(nuclear["Longitude"], nuclear["Latitude"]),
    crs="EPSG:4326"
)

geotherm = gpd.GeoDataFrame(
    geotherm, 
    geometry=gpd.points_from_xy(geotherm["Longitude"], geotherm["Latitude"]),
    crs="EPSG:4326"
)

cities = gpd.GeoDataFrame(
    cities, 
    geometry=gpd.points_from_xy(cities["lon"], cities["lat"]),
    crs="EPSG:4326"
)

#setting custom widths on transmission lines to match voltage for visualization
line_width = {
    '220-287' : 0.5,
    '345' : 0.75,
    '500' : 1.0,
    '735 AND ABOVE' : 1.25
}
widths = lines['VOLT_CLASS'].map(line_width)

# cropping data to state boundaries
boundary = states.dissolve()
geomap_west = gpd.clip(geomap, boundary)
lines_west = gpd.clip(lines, boundary)

# =============================================================================
#MAP 1 (main): GEOTHERMAL FAVORABILITY AND INFRASTRUCTURE
fig, ax = plt.subplots(figsize=(10, 12))
geomap_west.plot(
    column="index",        
    cmap=cmap,
    edgecolor="none",
    norm=norm,
    ax=ax,
    legend=False,
    zorder=1
)
states.plot(
    ax=ax,
    facecolor='none',
    edgecolor='white',
    linewidth=1.0,
    zorder=2
)
lines_west.plot(
    ax = ax,
    linewidth = widths,
    color='lightblue',
    alpha=0.7,
    zorder=3,
    label='Major (≤300 kV) Transmission Lines'
)
geotherm.plot(
    ax=ax,
    color="red",
    marker='*',
    markersize=150,
    edgecolor="black",
    linewidth=0.5,
    zorder=4,
    label='Active Geothermal Generating Sites'
)
nuclear.plot(
    ax=ax,
    color="yellow",
    marker='^',
    markersize=100,
    edgecolor="black",
    linewidth=0.5,
    zorder=5,
    label='Active Nuclear Generating Sites'
)

#plotting cities and labelling names
cities.plot(
    ax=ax,
    color='black',
    edgecolor='white',
    marker='o',
    markersize=75,
    zorder=6
)
for x, y, label in zip(cities.geometry.x, cities.geometry.y, cities["name_label"]):
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(-5, -5),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        color="black",
        ha="right",
        va="top",
        bbox=dict(
            facecolor="white",
            edgecolor="none",
            alpha=0.7,
            pad=1.5,
        ),
    )

#legend and scale
leg = ax.legend(loc='upper right',
    bbox_to_anchor=(1.4, 0.95),
    markerscale=0.7,
    handlelength=1.5,
    labelspacing=0.3,
    borderpad=0.4,
    handletextpad=0.5
)
#Manually creating color scale for favorability
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm._A = []
cbar = fig.colorbar(sm, 
    ax=ax, 
    shrink=0.5, 
    pad=0.02,
    location='right',
    anchor=(-0.8, 0.6)
)
cbar.set_ticks(np.arange(n_bins))
cbar.set_ticklabels(value_order)
cbar.set_label("Geothermal Favorability")

ax.set_title(
    'Geothermal Potential and Infrastructure along Pacific States', 
    fontsize=15, loc='left'
)
ax.set_axis_off()
plt.savefig(
    r'/users/samlerner/Desktop/DataViz/GeoTherm/geomap.png',
    dpi=300,
    bbox_inches="tight",
    pad_inches=0.1,
)
plt.show()

# =============================================================================
#MAP 1.5: FOCUSED ON CITY BUFFERS
#mapping the buffers uses a shapefile I created in my analysis code
buffers = gpd.read_file(os.path.join(PATH, 'buffer_map.shp'))
buffers = buffers.to_crs('EPSG:4326')
plants_buffer = gpd.read_file(os.path.join(PATH, 'buffer_map_plants.shp'))
plants_buffer = plants_buffer.to_crs('EPSG:4326')

buffers['index'] = pd.Categorical(
    buffers['Descript'],
    categories=value_order,
    ordered=True
)
cmap = plt.get_cmap("viridis")
norm = mcolors.Normalize(vmin=0, vmax=n_bins - 1)
buffers["index_code"] = buffers["index"].cat.codes

fig, ax = plt.subplots(figsize=(10, 12))
geomap_west.plot(
    column="index",        
    cmap=cmap,
    edgecolor="none",
    norm=norm,
    ax=ax,
    legend=False,
    zorder=1,
    alpha=0.2
)
states.plot(
    ax=ax,
    facecolor='none',
    edgecolor='white',
    linewidth=1.0,
    zorder=2
)
geotherm.plot(
    ax=ax,
    color="red",
    marker='*',
    markersize=150,
    edgecolor="black",
    linewidth=0.1,
    zorder=3,
    alpha=0.2,
    label=None
)
nuclear.plot(
    ax=ax,
    color="yellow",
    marker='^',
    markersize=100,
    edgecolor="black",
    linewidth=0.5,
    zorder=4,
    alpha=0.2,
    label='Active Nuclear Generating Sites'
)

#plotting city buffer zones
buffers.plot(
    column="index",
    ax=ax,
    cmap=cmap,
    norm=norm,
    legend=False,
    zorder=5
)
#plotting plants in buffer zones
plants_buffer.plot(
    ax=ax,
    color="red",
    marker='*',
    markersize=150,
    edgecolor="black",
    linewidth=0.5,
    zorder=7,
    label='Active Geothermal Generating Sites'
)

#plotting cities and labelling names
cities.plot(
    ax=ax,
    color='black',
    edgecolor='white',
    marker='o',
    markersize=75,
    zorder=6
)
for x, y, label in zip(cities.geometry.x, cities.geometry.y, cities["name_label"]):
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(-5, -5),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        color="black",
        ha="right",
        va="top",
        bbox=dict(
            facecolor="white",
            edgecolor="none",
            alpha=0.7,
            pad=1.5,
        ),
        zorder=7
    )

#legend and scale
leg = ax.legend(loc='upper right',
    bbox_to_anchor=(1.4, 0.95),
    markerscale=0.7,
    handlelength=1.5,
    labelspacing=0.3,
    borderpad=0.4,
    handletextpad=0.5
)
#Manually creating color scale for favorability
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm._A = []
cbar = fig.colorbar(sm, 
    ax=ax, 
    shrink=0.5, 
    pad=0.02,
    location='right',
    anchor=(-0.8, 0.6)
)
cbar.set_ticks(np.arange(n_bins))
cbar.set_ticklabels(value_order)
cbar.set_label("Geothermal Favorability")

ax.set_title(
    'Geothermal Potential and Infrastructure along Pacific States', 
    fontsize=15, loc='left'
)
ax.set_axis_off()
plt.savefig(
    r'/users/samlerner/Desktop/DataViz/GeoTherm/geomap_zones.png',
    dpi=300,
    bbox_inches="tight",
    pad_inches=0.1,
)
plt.show()

# ============================================================================
#MAP 2: INDIVIDUAL BUFFER ZONES

cities_proj = cities.to_crs('EPSG:5070')
buffers_proj = buffers.to_crs('EPSG:5070')
plants_buffer_proj = plants_buffer.to_crs('EPSG:5070')

n_cities = len(cities_proj)
n_cols = 5
n_rows = -(-n_cities // n_cols)

fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 4))
axes = axes.flatten()

# Continuous colormap based on bin rank
cmap = plt.get_cmap("viridis")
norm = mcolors.Normalize(vmin=0, vmax=n_bins - 1)

# Make sure the clipped data has a numeric rank column to color by
buffers_proj["value_rank"] = buffers_proj["index"].map(
    {v: i for i, v in enumerate(value_order)}
)

# Looping through each city and plotting its buffer
for i, (_, city) in enumerate(cities_proj.iterrows()):
    ax = axes[i]
    city_name = city["name"]
    city_polys = buffers_proj[buffers_proj["city"] == city_name]
    city_pts = plants_buffer_proj[plants_buffer_proj["city"] == city_name]
    
    city_polys.plot(
        column="value_rank",
        cmap=cmap,
        norm=norm,
        edgecolor="none",
        ax=ax,
        legend=False
    )
    if not city_pts.empty:
        city_pts.plot(
            ax=ax, 
            color="red", 
            marker="*", 
            markersize=100, 
            edgecolor="black", 
            linewidth=0.5, 
            zorder=5,
            label='Active Geothermal Generating Sites'
        )
    # ax.scatter(city.geometry.x, city.geometry.y, color="white", marker="o", s=40, edgecolor="black", zorder=6)
    ax.set_title(city_name.replace("_", " "), fontsize=12)
    ax.set_axis_off()

# Hide unused subplot axes
for j in range(n_cities, len(axes)):
    axes[j].axis("off")

sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
cbar = fig.colorbar(
    sm,
    ax=axes[:n_cities],
    orientation="horizontal",
    shrink=0.5,
    pad=0.05,
    location="bottom",
)
cbar.set_ticks(np.arange(n_bins))
cbar.set_ticklabels(value_order)
cbar.set_label("Favorability")

plant_handle = Line2D(
    [0], [0],
    marker="*", color="w", markerfacecolor="red", markeredgecolor="black",
    markersize=15, linestyle="None",
    label="Active Geothermal Generating Sites"
)
fig.legend(
    handles=[plant_handle],
    loc="lower center",
    bbox_to_anchor=(0.81, 0.09),
    frameon=False,
    fontsize=12,
)
fig.suptitle("Geothermal Favorability and Active Plants by City 150km Buffer Zone", fontsize=16, y=1.02)

plt.savefig(
    r'/users/samlerner/Desktop/DataViz/GeoTherm/citybuffermap.png',
    dpi=500,
    bbox_inches="tight",
    pad_inches=0.1,
)
plt.show()