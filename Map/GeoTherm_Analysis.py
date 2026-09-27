import geopandas as gpd
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shapely
from shapely import Point, LineString, Polygon
from matplotlib.colors import LogNorm
import matplotlib.colors as mcolors
import altair as alt
from matplotlib.lines import Line2D


PATH = r'/users/samlerner/Desktop/DataViz/GeoTherm'

# =============================================================================
#SETTING UP DATA
#Favorability map
mappath = os.path.join(PATH, 'Favorability/FavorabilitySurface.shp')
geomap = gpd.read_file(mappath)

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

# ==============================
#cleaned datasets
translpath = os.path.join(PATH, 'Transmission/transline_cleaned.shp')
lines = gpd.read_file(translpath)

poppath = os.path.join(PATH, 'citycoords.csv')
cities = pd.read_csv(poppath)
cities = gpd.GeoDataFrame(
    cities, 
    geometry=gpd.points_from_xy(cities["lon"], cities["lat"]),
    crs="EPSG:4326"
)

statespath = os.path.join(PATH, 'States/states_cleaned.shp')
states = gpd.read_file(statespath)

geothermpath = os.path.join(PATH, 'geoplant_cleaned.csv')
geotherm = pd.read_csv(geothermpath)
geotherm = gpd.GeoDataFrame(
    geotherm, 
    geometry=gpd.points_from_xy(geotherm["Longitude"], geotherm["Latitude"]),
    crs="EPSG:4326"
)

# ==============================
# cropping data to state boundaries
boundary = states.dissolve()
geomap_west = gpd.clip(geomap, boundary)
lines_west = gpd.clip(lines, boundary)

# =============================================================================
# DISTANCE ANALYSIS
#changing crs so I can do distance calculations
geomap_proj = geomap.to_crs("EPSG:5070")
cities_proj = cities.to_crs("EPSG:5070")
states_proj = states.to_crs("EPSG:5070")
geotherm_proj = geotherm.to_crs("EPSG:5070")

threshold_bin = '2 - 3' #Moderate favorability for goethermal systems
threshold_idx = value_order.index(threshold_bin)
above_categories = value_order[threshold_idx:]

#function to find share of area that is above a moderate geothermal favorability
def share_above_threshold(polygons, boundary, crs):
    #Clip polygons to boundary and return share of area in above_categories
    boundary_gdf = gpd.GeoDataFrame(geometry=[boundary], crs=crs)
    clipped = gpd.clip(polygons, boundary_gdf)
    
    if clipped.empty:
        return None
    
    clipped = clipped.copy()
    clipped["area"] = clipped.geometry.area
    total_area = clipped["area"].sum()
    above_area = clipped.loc[clipped["index"].isin(above_categories), "area"].sum()
    
    return above_area / total_area if total_area > 0 else None

#state level share 
state_shares = []
for _, state_row in states_proj.iterrows():
    share = share_above_threshold(geomap_proj, state_row.geometry, geomap_proj.crs)
    share = round(float(share), 3)
    state_shares.append({"STUSPS": state_row["STUSPS"], "state_share": share})

state_shares_df = pd.DataFrame(state_shares)

#combining cities within states
cities_with_state = gpd.sjoin(
    cities_proj,
    states_proj[["STUSPS", "geometry"]],
    predicate="within",
    how="left"
).drop(columns="index_right")

#city share and number of active plants in buffer
buffer_dist_m = 150 * 1000
city_shares = []

for _, city in cities_with_state.iterrows():
    buffer_geom = city.geometry.buffer(buffer_dist_m)
    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_geom], crs=geomap_proj.crs)
    plants_in_buffer = gpd.sjoin(geotherm_proj, buffer_gdf, predicate="within")
    share = share_above_threshold(geomap_proj, buffer_geom, geomap_proj.crs)
    share = round(float(share), 3)
    city_shares.append({
        "city": city["name"],
        "STUSPS": city["STUSPS"],
        "city_share": share,
        "plants_in_buffer": len(plants_in_buffer)
    })

city_shares_df = pd.DataFrame(city_shares)

#getting total number of plants per state
geotherm_state = (
    geotherm[geotherm["Plant_State"].isin(["CA", "WA", "OR"])]
    .groupby("Plant_State")
    .size()
    .reindex(["CA", "WA", "OR"], fill_value=0)
    .reset_index(name="total_state_plants")
)

results_df = city_shares_df.merge(state_shares_df, on="STUSPS", how="left")
results_df = results_df.rename(columns={"STUSPS": "state"})[
    ["state", "city", "state_share", "city_share", "plants_in_buffer"]
]
results_df = results_df.merge(
    geotherm_state,
    left_on='state',
    right_on='Plant_State',
    how='left'
)
results_df = results_df.drop(columns='Plant_State')

results_df
results_df.to_csv(os.path.join(PATH, 'final_data.csv'))

# =============================================================================
#VISUALIZATION
# ==================
#Option1: Bar Plot for each city + state with counts

#converting to long-form
city_rows = results_df[["state", "city", "city_share", "plants_in_buffer"]].rename(
    columns={"city": "category", "city_share": "share", "plants_in_buffer": "n_plants"}
)
city_rows["type"] = "City"

state_rows = (
    results_df[["state", "state_share", "total_state_plants"]]
    .drop_duplicates()
    .rename(columns={"state_share": "share", "total_state_plants": "n_plants"})
)
state_rows["category"] = "State Total"
state_rows["type"] = "State"

plot_df = pd.concat([city_rows, state_rows[["state", "category", "share", "n_plants", "type"]]])

#making the labels nicer for viz
plot_df['category'] = plot_df['category'].str.replace('_', ' ', regex=True)
state_name_full = {
    'WA' : 'Washington',
    'OR' : 'Oregon',
    'CA' : 'California'
}
plot_df['state'] = plot_df['state'].map(state_name_full)

#so states are always on the left
plot_df["sort_key"] = plot_df["type"].map({"State": 0, "City": 1})

#plotting
x_enc = alt.X(
    "category:N",
    title=None,
    axis=alt.Axis(labelAngle=-45),
    sort=alt.EncodingSortField(field="sort_key", order="ascending"),
    scale=alt.Scale(paddingInner=0.1, paddingOuter=0.1),
)

base = alt.Chart(plot_df).mark_bar().encode(
    x=x_enc,
    y=alt.Y(
        "share:Q", 
        title="Share of Area With Geothermal Potential", 
        axis=alt.Axis(format="%")),
    color=alt.Color("type:N", title="Geography", scale=alt.Scale(
        domain=["City", "State"], range=["#7991B2", "#118348"]
    )),
    tooltip=["share", "n_plants"],
)

# numbers = alt.Chart(plot_df).mark_text(baseline="bottom").encode(
#     x=x_enc,
#     y=alt.value(20),
#     text="n_plants:Q",
# )
text = base.mark_text(dy=-5).encode(text="n_plants:Q")

chart = (base + text).properties(
    width=alt.Step(50),
    height=300,
).facet(
    column=alt.Column("state:N", title=None),
    spacing=5,
).resolve_scale(x="independent").properties(
    title=alt.TitleParams(
        text="Geothermal Potential Along Pacific States and Proximal to their Major Cities",
        subtitle=["Share of land area with at least a moderate favorability within states, within 150km of each city, and",
            "number of active plants in each zone."
        ],
        subtitleFontSize=12,
        fontSize=16,
        offset=10,
        anchor="start"
    )
)

chart
chart.save(os.path.join(PATH, 'favorability.png'), ppi=300)

# =========================================================================
#GEODATAFRAME OF BUFFER ZONES

clipped_list = []
plants_list = []

for _, city in cities_proj.iterrows():
    buffer_geom = city.geometry.buffer(buffer_dist_m)
    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_geom], crs=geomap_proj.crs)
    
    # clipping favorability to buffer
    clipped = gpd.clip(geomap_proj, buffer_gdf)
    if not clipped.empty:
        clipped = clipped.copy()
        clipped["city"] = city["name"]
        clipped_list.append(clipped)
    
    # plants in buffer
    plants_in_buffer = gpd.sjoin(geotherm_proj, buffer_gdf, predicate="within")
    if not plants_in_buffer.empty:
        plants_in_buffer = plants_in_buffer.drop(columns="index_right").copy()
        plants_in_buffer["city"] = city["name"]
        plants_list.append(plants_in_buffer)

city_clips_gdf = gpd.GeoDataFrame(
    pd.concat(clipped_list, ignore_index=True),
    crs=geomap_proj.crs
)
city_plants_gdf = gpd.GeoDataFrame(
    pd.concat(plants_list, ignore_index=True),
    crs=geotherm_proj.crs
)

city_clips_gdf.to_file(os.path.join(PATH, 'buffer_map.shp'))
city_plants_gdf.to_file(os.path.join(PATH, 'buffer_map_plants.shp'))

# ==========================================================================
