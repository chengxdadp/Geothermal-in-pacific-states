import geopandas as gpd
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shapely
from shapely import Point, LineString, Polygon
from matplotlib.colors import LogNorm
import matplotlib.colors as mcolors


PATH = r'/users/samlerner/Desktop/DataViz/GeoTherm'

# =============================================================================
#DATA SOURCES + DESCRIPTIONS
#Geothermal favorability
    #DeAngelo, J., and Williams, C.F., 2010, Geothermal Favorability Map Derived From Logistic Regression Models: 
    #U.S. Geological Survey data release, https://doi.org/10.5066/P137NMXE.
    #It is an average of 12 models that correlates different geological and geophysical factors to 
    #the known presence of moderate (90 - 150° C) to high (> 150° C) temperature geothermal systems.
#State Boundaries
    #US Census Cartographic Shapefiles
    #https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html
    #1:5 million ressolution
#Active Geothermal and Nuclear Plants
    #Preliminary Monthly Electric Generator Inventory
    #(based on Form EIA-860M as a supplement to Form EIA-860)
    #https://www.eia.gov/electricity/data/eia860m/
    #July 2026 Data (most recent)
#Transmission Lines
    #US Fish and Wildlife Service: US Electric Power Transmission Lines
    #Created as a shapefile on fws open data
    #Saved data as a csv for cleaning
    #https://gis-fws.opendata.arcgis.com/datasets/fws::us-electric-power-transmission-lines/about
# =============================================================================

# GEOTHERMAL FAVORABILITY
mappath = os.path.join(PATH, 'Favorability/FavorabilitySurface.shp')
geomap = gpd.read_file(mappath)

geomap.plot()
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

geomap["index_code"] = geomap["index"].cat.codes

geopath = os.path.join(PATH, 'Favorability/geomap_clean.shp')
geomap.to_file(geopath)

# =============================================================================
#POWER PLANTS
powerpath = os.path.join(PATH, 'july_generator2026_operating.csv')
powerplant = pd.read_csv(powerpath)

powerplant.head()
powerplant = powerplant.replace(' ', '_', regex=True)
powerplant = powerplant.replace(',', '', regex=True)
powerplant.columns = powerplant.iloc[1]
powerplant = powerplant.iloc[2:].reset_index()
powerplant.shape

#filtering to only west coast
powerplant = powerplant.loc[
    (powerplant['Plant_State'] == 'CA') | 
    (powerplant['Plant_State'] == 'WA') |
    (powerplant['Plant_State'] == 'OR')]
powerplant.shape

#Creating Geothermal Dataset (filtering)
geotherm = powerplant.loc[powerplant['Technology'] == 'Geothermal'].reset_index()
geotherm.shape

#exporting west coast geotherm to csv with all columns
geotherm.to_csv(r'/users/samlerner/Desktop/DataViz/GeoTherm/west_geotherm_full.csv', index=False)

#Deleting unused values
geotherm.head()
geotherm = geotherm[[
    'Entity_Name',
    'Plant_ID',
    'Plant_Name',
    'Plant_State',
    'Technology',
    'Operating_Year',
    'Latitude',
    'Longitude'
]]

#deleting identical points
len(geotherm)
geotherm = geotherm.drop_duplicates()

#Creating Nuclear Dataset (repeating geothermal filtering)
powerplant['Technology'].value_counts()
nuclear = powerplant.loc[powerplant['Technology'] == 'Nuclear'].reset_index()
nuclear = nuclear[[
    'Entity_Name',
    'Plant_ID',
    'Plant_Name',
    'Plant_State',
    'Technology',
    'Operating_Year',
    'Latitude',
    'Longitude'
]]

#exporting as CSV
nuclearpath = os.path.join(PATH, 'nuclear_cleaned.csv')
geothermpath = os.path.join(PATH, 'geoplant_cleaned.csv')

nuclear.to_csv(nuclearpath)
geotherm.to_csv(geothermpath)

# =============================================================================
# TRANSMISSION LINES
transmpath = os.path.join(PATH, 'Transmission/Electric_Power_Transmission_Lines_A.shp')
transline = gpd.read_file(transmpath)

transline.head()
#deleting data I won't use
lines = transline[['STATUS', 'VOLTAGE', 'VOLT_CLASS', 'Shape__Len', 'geometry']]

lines.crs
lines = lines.to_crs("EPSG:4326")

#filtering to only major lines (Extra High and Ultra High voltage)
lines['VOLT_CLASS'].value_counts()
lines = lines.loc[
    #(lines['VOLT_CLASS'] == '220-287') |
    (lines['VOLT_CLASS'] == '345') |
    (lines['VOLT_CLASS'] == '500') |
    (lines['VOLT_CLASS'] == '735 AND ABOVE')
]

#filtering out inactive lines
lines['STATUS'].value_counts()
lines = lines.loc[(lines['STATUS'] != 'INACTIVE') & (lines['STATUS'] != 'UNDER CONSTRUCTION')]

#exporting as shapefile
trans_cleanpath = os.path.join(PATH, 'Transmission/transline_cleaned.shp')
lines.to_file(trans_cleanpath)

# =============================================================================
# POPULATION CENTERS
cities_list = {
    "Seattle": (47.6062, -122.3321),
    "Portland": (45.5152, -122.6784),
    "San_Francisco": (37.7749, -122.4194),
    "Los_Angeles": (34.0522, -118.2437),
    "San_Diego": (32.7157, -117.1611),
}

cities = pd.DataFrame(
    [(name, lat, lon) for name, (lat, lon) in cities_list.items()],
    columns=["name", "lat", "lon"]
)
cities['name_label'] = cities['name'].str.replace('_', ' ', regex=False)

#exporting
cities.to_csv(os.path.join(PATH, 'citycoords.csv'))

# =========================================
# STATE BOUNDARIES
statepath = os.path.join(PATH, 'States/cb_2018_us_state_5m.shp')
states = gpd.read_file(statepath)
states = states.to_crs("EPSG:4326")

states = states.loc[
    (states['STUSPS'] == 'WA') |
    (states['STUSPS'] == 'CA') | 
    (states['STUSPS'] == 'OR')
].reset_index()

#exporting
states.to_file(os.path.join(PATH, 'States/states_cleaned.shp'))

