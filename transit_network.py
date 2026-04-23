# %%
# pyright: basic

import os, pickle
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

crs_code = 'EPSG:2263'
walk_spd = 1.3889 # meters/sec ≈ 5 km/h
max_dist =  300
min_weight = 1.0
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ox.settings.bidirectional_network_types =  ['walk']
# %%

# create graph
walk_graph = ox.graph_from_place("New York City, New York", network_type='walk', simplify=True)
walk_graph = ox.project_graph(walk_graph, to_crs=crs_code)
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson").to_crs(crs_code)
nxG = nx.MultiDiGraph()

# rename nodes and add type to match rest of network
mapping = {n: f'walk_{n}' for n in walk_graph.nodes()}
walk_graph = nx.relabel_nodes(walk_graph, mapping, copy=False)
nx.set_node_attributes(walk_graph, "walk", name='type')

# convert edge weights to seconds
for u, v, k, data in walk_graph.edges(keys=True, data=True):
    len_m = data.get('length', 0)
    data['weight'] = max(len_m/ walk_spd, min_weight/10)
    data['relation'] = 'walking'

# %%

transit_edges_df = pd.read_csv("processed_edges_2015.csv")
transit_stops_df = pd.read_csv("processed_stops_2015.csv")
transit_gdf = gpd.GeoDataFrame(
    transit_stops_df,
    geometry = gpd.points_from_xy(transit_stops_df['stop_lon'], transit_stops_df['stop_lat']),
    crs="EPSG:4326"
)
transit_gdf.to_crs(crs_code, inplace=True)

for idx, rw in transit_gdf.iterrows():
    nxG.add_node(
        rw['stop_id'], 
        x=rw.geometry.x,
        y=rw.geometry.y, 
        pos=(rw.geometry.x, rw.geometry.y),
        type=f"{rw['mode']}_transit"
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
    x1, y1 = stop_coords[i, 0], stop_coords[i, 1]
    x2, y2 = walk_graph.nodes[s_node]['x'], walk_graph.nodes[s_node]['y']
    dist = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
    if dist > max_dist: 
        print(f"Skipping stop {t_node} is {dist:.1f}m from nearest street")
        continue
    weight = max(dist / walk_spd, min_weight)
    

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
        sch_weight = rw['funding_per_student'], # (total funding/total students)
        type='school')

# vector operation
sch_ids = [f"school_{code}" for code in school_df['LOCATION_CODE']]
sch_x = school_df['lon'].values
sch_y = school_df['lat'].values

nearest_street_nodes = ox.distance.nearest_nodes(walk_graph, X=sch_x, Y=sch_y)

new_school_edges = []
for i, sch_node in enumerate(sch_ids):
    s_node = nearest_street_nodes[i]
    
    # Calculate Euclidean distance
    x1, y1 = sch_x[i], sch_y[i]
    x2, y2 = walk_graph.nodes[s_node]['x'], walk_graph.nodes[s_node]['y']
    dist = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    w = max(dist / walk_spd, min_weight)

    new_school_edges.append((sch_node, s_node, {'weight': w, 'relation': 'walking_school'}))
    new_school_edges.append((s_node, sch_node, {'weight': w, 'relation': 'walking_school'}))

nxG_final.add_edges_from(new_school_edges)
sch_weights = [d['weight'] for u, v, d in nxG_final.edges(data=True) if d['relation'] == 'walking_school']
print(f"Added {len(sch_ids)} schools and {len(new_school_edges)} connecting edges.")
print(f"Min weight: {min(sch_weights)}, Max weight: {max(sch_weights)}")
# %%
# add nta nodes and walking edge to Graph
nta_gdf = gpd.read_file("./data/spatial/nta_2010/nynta2010.shp").to_crs(crs_code)

#print("nta_shapefile cols:", nta_gdf.columns.tolist())

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

    # Calculate Euclidean distance
    dist = np.sqrt((curr_x - walk_graph.nodes[s_node]['x'])**2 + 
                   (curr_y - walk_graph.nodes[s_node]['y'])**2)

    weight = max(dist / walk_spd, min_weight) 
    new_nta_edges.append((nta_node, s_node, {'weight': weight, 'relation': 'walking_nta'}))
    new_nta_edges.append((s_node, nta_node, {'weight': weight, 'relation': 'walking_nta'}))

nxG_final.add_edges_from(new_nta_edges)
nta_weights = [d['weight'] for u, v, d in nxG_final.edges(data=True) if d['relation'] == 'walking_nta']
print(f"Added {len(nta_codes)} NTAs and {len(new_nta_edges)} connecting edges")
print(f"Min weight: {min(nta_weights)}, Max weight: {max(nta_weights)}")

# %%
# building nodes and edge geometry list

## Filter the nodes into the different types so they can be represented differently on the visual
## subway_transit, bus_transit, walk, school, nta
nodes_data = []
for node, data in nxG_final.nodes(data=True):
    nodes_data.append({
        'stop_id': node, 
        'geometry': Point(data['x'], data['y']),
        'node_type': data.get('type')
        })

gdf_nodes = gpd.GeoDataFrame(nodes_data, crs=crs_code)

gdf_nodes = gpd.sjoin(gdf_nodes, boroughs[['geometry']], predicate='within')
valid_stops = set(gdf_nodes['stop_id'])

# Filter the edges into different types so they can be represented differently on the visual
# transit_travel, transfer, walking, walk_transfer, walking_school, walking_nta
shapes_df = pd.read_csv("processed_shapes_2015.csv")
shape_lookup = {name: group for name, group in shapes_df.groupby('shape_id')}

edges_data = []
for u, v, data in nxG_final.edges(data=True):
    if u in valid_stops and v in valid_stops:
        shape_id = data.get('shape_id')

        if shape_id and shape_id in shape_lookup:
            pts = shape_lookup[shape_id].sort_values('shape_pt_sequence')
            geom_4326 = LineString(zip(pts.shape_pt_lon, pts.shape_pt_lat))
            geom = gpd.GeoSeries([geom_4326], crs="EPSG:4326").to_crs(crs_code).iloc[0]
        else:
            u_pos = (nxG_final.nodes[u]['x'], nxG_final.nodes[u]['y'])
            v_pos = (nxG_final.nodes[v]['x'], nxG_final.nodes[v]['y'])
            geom = LineString([u_pos, v_pos])
        edges_data.append({
            'geometry' : geom,
            'travel_time' : data.get('weight'),
            'edge_type' : data.get('relation')
            })
gdf_edges = gpd.GeoDataFrame(edges_data, crs=crs_code)

min_tk = gdf_edges['travel_time'].min()
max_tk = gdf_edges['travel_time'].max()

print(f"Minimum Travel Time : {min_tk} and Maximum Travel Time : {max_tk}")

# %%
# save data structure to file
with open('transit_graph.pkl', 'wb') as f: pickle.dump(nxG_final, f)

gdf_edges.to_file("network_data.gpkg", layer='edges', driver="GPKG")
gdf_nodes.to_file("network_data.gpkg", layer='nodes', driver="GPKG")

# %% 
# plotting

plt.ion()
fig, ax = plt.subplots(figsize=(12, 12))
boroughs.plot(ax=ax, color='#fffafa', edgecolor='black', linewidth=1)

## plot points
markers = {
    'school' : 'D', 
    'bus_transit': 'o',
    "subway_transit": 'o', 
    'nta' : 'D', 
    # 'walk' : 'w' leave invisible
    }
color_nodes = {
    'school' : 'red',
    'nta' : 'green', 
    'bus_transit': 'blue', 
    'subway_transit': 'navy', 
    # 'walk' : 'white' leave invisible
    }
size_nodes = {
    'school': 0.5,
    'nta' : 0.5,
    'bus_transit' : 0.25,
    'subway_transit' : 0.25,
    # 'walk' : 0 leave invisible
}

for n_type, df in gdf_nodes.groupby('node_type'):
    if n_type == 'walk' : continue
    df.plot(
        ax=ax, 
        marker=markers.get(n_type), 
        color=color_nodes.get(n_type), 
        markersize=size_nodes.get(n_type),
        alpha=0.2,
        label=n_type
        )

## plot edges
edge_colors = {
    'transit_travel' : 'cividis_r', 
    'transfer': 'magma_r', 
    #'walking': 'black', 
    'walk_transfer' : 'inferno', 
    'walking_school' : 'inferno', 
    'walking_nta' : 'inferno'
}
z_orders = {
    'transit_travel' : 4,
    'transfer' : 3,
    'walking' : 1,
    'walk_transfer' : 3,
    'walking_school' : 3,
    'walking_nta' : 3
}
line_widths = {
    'transit_travel' : 0.5,
    'transfer' : 0.3,
    'walking' : 0.1,
    'walk_transfer' : 0.3,
    'walking_school' : 0.3,
    'walking_nta' : 0.3,
}
for e_type, df in gdf_edges.groupby('edge_type'):
    style_config = {
        'ax' : ax,
        'zorder' : z_orders.get(e_type),
        'linewidth' : line_widths.get(e_type),
        'column' : 'travel_time',
        'alpha' : 0.5,
        'legend' : True,
        'legend_kwds' : {
                'label' : e_type,
                'orientation' : 'horizontal',
                'pad' : 0.05,
                'shrink' : 0.5
            }
    }

    if e_type == 'walking' :
        pass
        df.plot(**style_config, color='black')
    else :
        df.plot(**style_config, cmap=edge_colors.get(e_type))