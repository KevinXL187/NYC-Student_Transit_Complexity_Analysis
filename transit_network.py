# %%
# pyright: basic

import os
import osmnx as ox
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt

from shapely.geometry import Point, LineString
# %%

# coord_sys = (lon, lat)
# time in seconds

# create graph
os.chdir(os.path.dirname(os.path.abspath(__file__)))
walk_graph = ox.graph_from_place("New York City, New York", network_type='walk')
walk_graph = ox.utils_graph.get_undirected(walk_graph)
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson")
nxG = nx.Graph()
crs_code = "EPSG:4326" # TO DO : update to distance instead of decimal degrees

# %%
# add transit stops and travel time as weighted edges to Graph
## bus stops and edges
bus_stops_df = pd.read_csv("data/spatial/bus_stops.csv")
bus_edges_df = pd.read_csv("data/spatial/bus_stop_times.csv")

for idx, rw in bus_stops_df.iterrows():
    nxG.add_node(
        f"bus_{rw['stop_id']}", 
        y= rw['stop_lat'], x= rw['stop_lon'], 
        pos = (rw['stop_lon'], rw['stop_lat']),

        type='bus_transit'
        )
for idx, rw in bus_edges_df.iterrows():
    nxG.add_edge(
        rw['source_stop_id'], 
        rw['target_stop_id'], 
        weight= rw['travel_time'],

        relation ='bus_transit'
        )

## subways stops and edges
sw_stops_df = pd.read_csv("data/spatial/sw_stops.csv")
sw_edges_df = pd.read_csv("data/spatial/sw_stop_times.csv")

for idx, rw in sw_stops_df.iterrows():
    nxG.add_node(
        f"sw_{rw['stop_id']}",
        y = rw['stop_lat'], x = rw['stop_lon'],
        pos = (rw['stop_lon'], rw['stop_lat']),

        type='subway_transit'
    )

for idx, rw in sw_edges_df.iterrows():
    nxG.add_edge(
        rw['source_stop_id'], 
        rw['target_stop_id'], 
        weight= rw['travel_time'],

        relation ='subway_transit'
    )

# %%
# combine the walking graph and nxG 
nxG_final = nx.compose(walk_graph, nxG)
for node, data in nxG_final.nodes(data=True):
    if data.get('type') == 'transit':
        nearest_street_node = ox.distance.nearest_nodes(walk_graph, X=data['x'], Y=data['y'])

        ## connects the transit stop to the nearest street node
        nxG_final.add_edge(node, nearest_street_node, weight=60, relation='walking')

# %%
# add school nodes and walking edge to Graph
school_gdf = gpd.read_file("./data/spatial/SchoolPoints.shp")
for idx, rw in school_gdf.iterrows():
    nxG_final.add_node(
        f"school_{idx}", 
        x = rw.geometry.x,
        y = rw.geometry.y,
        pos= (rw.geometry.x, rw.geometry.y), 
        name= rw.get('Name', idx), 
        type='school')

# connect school nodes to nearest street node
for node, data in nxG_final(data=True):
    if data.get('type') == 'school':
        nearest_street_node = ox.distance.nearest_nodes(walk_graph, X=data['pos'][0], Y=data['pos'][1])

        ## connects the school node to the nearest street node
        nxG_final.add_edge(node, nearest_street_node, weight=60, relation="walking")

# %%
# add nta nodes and walking edge to Graph
nta_gdf = gpd.read_file()
for idx, rw in nta_gdf.iterrows():
    centeroids = 

    nxG_final.add_node(
        f"nta_{row.get('ntacode', idx)}",
        x = rw.geometry.centroid.x,
        y = rw.geometry.centroid.y,
        pos = (rw.geometry.centroid.x, rw.geometry.centroid.y),
        name=row.get('ntaname', 'Unknown'),
        type='origin'
    )
# connect nta nodes to nearest street
for node, data in nxG_final(data=True):
    if data.get('type') == 'origin':
        nearest_street_node = ox.distance.nearest_nodes(walk_graph, X=data['pos'][0], Y=data['pos'][1])

        ## connects the nta node to the nearest street node
        nxG_final.add_edge(node, nearest_street_node, weight=60, relation="walking")

# %%
# building nodes and edge geometry list

## Filter the nodes into the different types so they can be represented differently on the visual
## school, nta, bus, subway
nodes_data = []
for node, data in nxG_final.nodes(data=True):
    nodes_data.append({
        'stop_id': node, 
        'geometry': Point(data['x'], data['y']),
        'node_type': data.get('type', 'unknown')
        })

gdf_nodes = gpd.GeoDataFrame(nodes_data, crs=crs_code)

gdf_nodes = gpd.sjoin(gdf_nodes, boroughs[['geometry']], predicate='within')
valid_stops = set(gdf_nodes['stop_id'])

# Filter the edges into different types so they can be represented differently on the visual
# walking, bus_transit, subway_transit
edges_data = []
for u, v, data in nxG_final.edges(data=True):
    if u in valid_stops and v in valid_stops:
        u_pos = (nxG_final.nodes[u]['x'], nxG_final.nodes[u]['y'])
        v_pos = (nxG_final.nodes[v]['x'], nxG_final.nodes[v]['y'])
        edges_data.append({
            'geometry' : LineString(u_pos, v_pos),
            'travel_time' : data.get('weight', 0),
            'edge_type' : data.get('type', 'unknown')
            })
gdf_edges = gpd.GeoDataFrame(edges_data, crs=crs_code)

min_tk = gdf_edges['travel_time'].min()
max_tk = gdf_edges['travel_time'].max()

# %% 
# plotting
plt.ion()
fig, ax = plt.subplots(figsize=(12, 12))
boroughs.plot(ax=ax, color='#f2f2f2', edgecolor='black', linewidth=0.5)

## plot points
markers = {'school' : 's', 'bus_transit': 'bt', "subway_transit": 'st', 'nta' : 'n'}
color_nodes = {'school' : 'red', 'bus_transit': 'blue', "subway_transit": 'light_blue' 'nta' : 'green'}
for n_type, df in gdf_nodes.groupby('node_type'):
    df.plot(
        ax=ax, 
        marker=markers.get(n_type, 'o'), 
        color=color_nodes.get(n_type, 'black'), 
        markersize=0.5,
        alpha=0.2,
        label=n_type
        )

## plot edges
for e_type, df in gdf_edges.groupby('edge_type'):
    cmap_options = ["magma_r",'cividis_r']
    if e_type == "bus_transit" or e_type =="subway_transit":
        cmap = cmap_options[1],
        label = "Transit Travel Time (seconds)",
        zorder = 2
    if e_type == "transfer":
        camp= = cmap_options[0],
        label = "Transfer Travel Time (seconds)"
        zorder = 3,
    df.plot(
        ax = ax,
        column="travel_time",
        cmap = cmap,
        zorder = zorder,
        linewidth = 0.5,
        alpha = 0.5,
        legend=True,
        legend_kwds = {
            'label' : label,
            'orientation' : 'horizontal',
            'pad' : 0.05,
            'shrink' : 0.5
        }
    )