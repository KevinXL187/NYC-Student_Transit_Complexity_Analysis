# %%
# pyright: basic
import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString

# create graph with stops and travel time as edges
os.chdir(os.path.dirname(os.path.abspath(__file__)))
stops_df = pd.read_csv("data/stops.csv")
edges_df = pd.read_csv("data/stop_times.csv")

nxG = nx.Graph()
for idx, rw in stops_df.iterrows():
    nxG.add_node(rw['stop_id'], lat=rw['stop_lat'], lon=rw['stop_lon'])
for idx, rw in edges_df.iterrows():
    nxG.add_edge(rw['source_stop_id'], rw['target_stop_id'], weight=rw['travel_time'])

pos = {node: (data['lon'], data['lat']) for node, data in nxG.nodes(data=True)}

# build node and edge geomtry list
crs_code = "EPSG:4326"
fp = "./data/Borough_Boundaries.geojson"
boroughs = gpd.read_file(fp)

nodes_data = []
for node, data in nxG.nodes(data=True):
    nodes_data.append({'stop_id': node, 'geometry': Point(data['lon'], data['lat'])})
gdf_nodes = gpd.GeoDataFrame(nodes_data, crs=crs_code)

gdf_nodes = gpd.sjoin(gdf_nodes, boroughs[['geometry']], predicate='within')
valid_stops = set(gdf_nodes['stop_id'])

edges_data = []
for u, v, data in nxG.edges(data=True):
    if u in valid_stops and v in valid_stops:
        line = LineString([pos[u],pos[v]])
        edges_data.append({
            'geometry' : LineString([pos[u], pos[v]]),
            'travel_time' : data.get('weight', 0)
            })
gdf_edges = gpd.GeoDataFrame(edges_data, crs=crs_code)

min_tk = gdf_edges['travel_time'].min()
max_tk = gdf_edges['travel_time'].max()
gdf_edges['thickness'] = ((gdf_edges['travel_time'] - min_tk) / (max_tk - min_tk) * 3.8) + 0.2
#print(min_tk, max_tk)
#print(gdf_edges)

# %%
# load and parse school point data files
school_gdf = gpd.read_file("./data/raw/schools/SchoolPoints_APS_2024_08_28.shp")
for idx, rw in school_gdf.iterrows():
    sch_idx = f"school_{idx}"
    pos= (rw.geometry.x, rw.geometry.y)
    nxG.add_node(sch_idx, pos=pos, name=rw.get('Name', idx))
    
# %%


# %%
# plotting
plt.ion()
fig, ax = plt.subplots(figsize=(12, 12))
boroughs.plot(ax=ax, color='#f2f2f2', edgecolor='black', linewidth=0.5)

gdf_edges.plot(
    ax=ax, 
    column='travel_time',
    cmap='magma_r',
    #linewidth=gdf_edges['thickness'], 
    linewidth=0.5,
    alpha=0.5,
    zorder=2, 
    legend=True,
    legend_kwds={
        'label': "Travel Time (seconds)", 
        'orientation': "horizontal",
        'pad': 0.02, 
        'shrink': 0.5}
    )

gdf_nodes.plot(ax=ax, markersize=0.5, color='green', alpha=0.2, label='Transit Stops')

ax.set_xlim([-74.3, -73.65])
ax.set_ylim([40.48, 40.92])
ax.set_axis_off()
plt.title("NYC Transit Network")
plt.legend()
plt.show() 
# %%
def calculate_cci(school_node, zip_nodes):
    total_time = 0
    valid_routes = 0

    for node in zip_nodes :
        try:
            travel_time = nx.shortest_path_length(nxG, source=node, traget=school_node, weight='weight')
            total_time += travel_time
            valid_routes += 1
        except nx.NetworkXNoPath: continue

    if valid_routes > 0 :
        cci = total_time /valid_routes

    return total_time/valid_routes if valid_routes > 0 else None