# %%
# pyright: basic

import os
from unittest import skip
import osmnx as ox
import pandas as pd
import geopandas as gpd
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

from sklearn.neighbors import BallTree
from shapely.geometry import Point, LineString

# coord_sys = (lon, lat)
# time in seconds

crs_code = "EPSG:4326"
walk_spd = 1.3889 # meters/sec ≈ 5 km/h
max_dist =  500
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ox.settings.bidirectional_network_types =  ['walk']
# %%

# create graph
walk_graph = ox.graph_from_place("New York City, New York", network_type='walk', simplify=True)
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson")
nxG = nx.MultiDiGraph()

# rename nodes to match rest of network
mapping = {n: f'walk_{n}' for n in walk_graph.nodes()}
walk_graph = nx.relabel_nodes(walk_graph, mapping, copy=False)

# convert edge weights to seconds
for u, v, k, data in walk_graph.edges(keys=True, data=True):
    len_m = data.get('length', 0)
    data['weight'] = max(len_m/ walk_spd, 0.1)
    data['relation'] = 'walking'

# %%

transit_stops_df = pd.read_csv("processed_stops_2015.csv")
transit_edges_df = pd.read_csv("processed_edges_2015.csv")

for idx, rw in transit_stops_df.iterrows():
    nxG.add_node(
        rw['stop_id'], 
        y=rw['stop_lat'], x=rw['stop_lon'], 
        pos=(rw['stop_lon'], rw['stop_lat']),
        type=f"{rw['mode']}_transit" # 'subway' or 'bus'
    )

for idx, rw in transit_edges_df.iterrows():
    nxG.add_edge(
        rw['source'], 
        rw['target'], 
        weight=rw['weight'],
        relation=rw['type'] # 'transit_travel', 'transfer'
    )

# %%
# connect walking network and transit network
nxG_final = nx.compose(walk_graph, nxG)

transit_nodes = [n for n, d in nxG_final.nodes(data=True) if 'transit' in str(d.get('type'))]
stop_coords = np.array([[nxG_final.nodes[n]['y'], nxG_final.nodes[n]['x']] for n in transit_nodes])

street_nodes = [n for n, d in walk_graph.nodes(data=True)]
street_coords = np.array([[walk_graph.nodes[n]['y'], walk_graph.nodes[n]['x']] for n in street_nodes])

nearest_indices = ox.distance.nearest_nodes(walk_graph, X=stop_coords[:, 1], Y=stop_coords[:, 0])

new_edges = []
for i, t_node in enumerate(transit_nodes):
    s_node = nearest_indices[i]
    
    # find distance
    dist = ox.distance.great_circle(lat1=stop_coords[i, 0], lon1=stop_coords[i, 1],
                                        lat2=walk_graph.nodes[s_node]['y'], 
                                        lon2=walk_graph.nodes[s_node]['x'])
    if dist > max_dist: 
        print(f"Skipping stop {t_node} is {dist:.1f}m from nearest street")
        continue
    weight = max(dist / walk_spd, 1.0)
    

    new_edges.append((t_node, s_node, {'weight': weight, 'relation': 'walk_transfer'}))
    new_edges.append((s_node, t_node, {'weight': weight, 'relation': 'walk_transfer'}))

nxG_final.add_edges_from(new_edges)

# %%
# check for unconnected transit stops
unconnected = [n for n in transit_nodes if nxG_final.degree(n) == 0]
print(f"Number of unconnected transit stops: {len(unconnected)}")

# check weights for walk_transfer
weights = [d['weight'] for u, v, d in nxG_final.edges(data=True) if d['relation'] == 'walk_transfer']
print(f"Min weight: {min(weights)}, Max weight: {max(weights)}")

# find specific edge with large weight
max_edge = max(nxG_final.edges(data=True), key=lambda x: x[2].get('weight', 0))
print(f"The longest edge is between {max_edge[0]} and {max_edge[1]}")
print(f"Relation: {max_edge[2].get('relation')}, Weight: {max_edge[2]['weight']}")

bad_node = nxG_final.nodes['bus_si_203833']
print(f"Coordinates of stop: {bad_node['y']}, {bad_node['x']}")

# %%
# add school nodes and walking edge to Graph
school_df = pd.read_csv("processed_schools_2015.csv")

for idx, rw in school_df.iterrows():
    sch_node = f"school_{rw['LOCATION_CODE']}"
    nxG_final.add_node(
        sch_node, 
        x = rw['lon'],
        y = rw['lat'],
        pos= (rw['lon'], rw['lat']), 
        name= rw['LOCATION_NAME'], 
        nta = rw['NTA_NAME'],
        sch_weight = rw['weighted_accessibility'], # (total funding/total students) * graduation rates
        type='school')

# vector operation
sch_ids = [f"school_{code}" for code in school_df['LOCATION_CODE']]
sch_x = school_df['lon'].values
sch_y = school_df['lat'].values

nearest_street_nodes = ox.distance.nearest_nodes(walk_graph, X=sch_x, Y=sch_y)

new_school_edges = []
for i, sch_node in enumerate(sch_ids):
    s_node = nearest_street_nodes[i]
    
    # Calculate distance
    dist = ox.distance.great_circle(
        lat1=sch_y[i], lon1=sch_x[i],
        lat2=walk_graph.nodes[s_node]['y'], 
        lon2=walk_graph.nodes[s_node]['x']
    )
    
    w = max(dist / walk_spd, 1.0)
    new_school_edges.append((sch_node, s_node, {'weight': w, 'relation': 'walking_school'}))
    new_school_edges.append((s_node, sch_node, {'weight': w, 'relation': 'walking_school'}))

nxG_final.add_edges_from(new_school_edges)
print(f"Added {len(sch_ids)} schools and {len(new_school_edges)} connecting edges.")
# %%
# add nta nodes and walking edge to Graph
nta_gdf = gpd.read_file("./data/spatial/nta_2010/nynta2010.shp")

print("nta_shapefile cols:", nta_gdf.columns.tolist())

nta_df = pd.read_csv('nta_SE_indicators_2015.csv')
income_dict = nta_df.set_index('GeoID')['median_income_estimate'].to_dict()

centroids = nta_gdf.geometry.centroid
nta_codes = nta_gdf['NTACode'].values
nta_x = centroids.x.values
nta_y = centroids.y.values

nearest_street_nodes = ox.distance.nearest_nodes(walk_graph, X=nta_x, Y=nta_y)
new_nta_edges = []

for i, rw in nta_gdf.iterrows():
    nta_code = nta_codes[i]
    nta_node = f"nta_{nta_code}"
    s_node = nearest_street_nodes[i]
    
    # Coordinates from our vectorized arrays
    curr_x, curr_y = nta_x[i], nta_y[i]

    # Add the Node
    nxG_final.add_node(
        nta_node,
        x = curr_x,
        y = curr_y,
        pos = (curr_x, curr_y),
        income = income_dict.get(nta_code),
        name = rw.get('NTAName', 'Unknown'),
        type = 'origin'
    )

    # Calculate distance to the street node
    dist = ox.distance.great_circle(
        lat1=curr_y, lon1=curr_x,
        lat2=walk_graph.nodes[s_node]['y'], 
        lon2=walk_graph.nodes[s_node]['x']
    )

    weight = max(dist / walk_spd, 1.0) 
    new_nta_edges.append((nta_node, s_node, {'weight': weight, 'relation': 'walking_nta'}))
    new_nta_edges.append((s_node, nta_node, {'weight': weight, 'relation': 'walking_nta'}))

nxG_final.add_edges_from(new_nta_edges)
print(f"Added {len(nta_codes)} NTAs and {len(new_nta_edges)} connecting edges")

# %%


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
color_nodes = {'school' : 'red', 'bus_transit': 'blue', "subway_transit": 'light_blue', 'nta' : 'green'}
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
        cmap = cmap_options[0],
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