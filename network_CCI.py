import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import os
from shapely.geometry import Point

# create graph with stops and travel time as edges
os.chdir(os.path.dirname(os.path.abspath(__file__)))
stops_df = pd.read_csv("data/stops.csv")
edges_df = pd.read_csv("data/stop_times.csv")

nxG = nx.Graph()

for idx, rw in stops_df.iterrows():
    nxG.add_node(rw['stop_id'], lat=rw['stop_lat'], lon=rw['stop_lon'])

for idx, rw in edges_df.iterrows():
    nxG.add_edge(rw['source_stop_id'], rw['target_stop_id'], weight=rw['travel_time'])

nodes_data = []
for node, data in nxG.nodes(data=True):
    nodes_data.append({'stop_id': node, 'geometry': Point(data['lon'], data['lat'])})

gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
fp = "/mnt/linux_data/Code/School/STAT 3494/Final Project/data/Borough_Boundaries_20260404.geojson"
boroughs = gpd.read_file(fp)

fig, ax = plt.subplots(figsize=(12, 12))
boroughs.plot(ax=ax, color='#f2f2f2', edgecolor='black', linewidth=0.5)
gdf_nodes.plot(ax=ax, markersize=2, color='blue', alpha=0.6, label='Transit Stops')

ax.set_xlim([-74.3, -73.65])
ax.set_ylim([40.48, 40.92])

plt.title("NYC Transit Network Overlaid on Borough Boundaries")
plt.legend()
plt.show()