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

crs_code = 'EPSG:2263'
walk_spd = 4.5567 # feets/sec
ft_per_meter = 3.2808 # feet
max_dist =  985 # feet
min_weight = 10 # second
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def euclidean_distance(x1, y1, x2, y2):
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
# %%

# create graph
walk_graph = ox.graph_from_place("New York City, New York", network_type='walk', simplify=True, retain_all=True)
walk_graph = ox.project_graph(walk_graph, to_crs=crs_code)
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson").to_crs(crs_code)
nxG = nx.MultiDiGraph()

# rename nodes and add type to match rest of network
mapping = {n: f'walk_{n}' for n in walk_graph.nodes()}
walk_graph = nx.relabel_nodes(walk_graph, mapping, copy=False)
nx.set_node_attributes(walk_graph, "walk", name='type')

# convert edge weights to seconds
for u, v, k, data in walk_graph.edges(keys=True, data=True):
    len_meter = data.get('length', 0)
    len_feet = len_meter * ft_per_meter
    data['weight'] = max(len_feet / walk_spd, min_weight / 2)
    data['relation'] = 'walking'

# %%

transit_edges_df = pd.read_csv("data/processed_edges_2015.csv")
transit_stops_df = pd.read_csv("data/processed_stops_2015.csv")
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
        relation=rw['type'] # 'transit_travel', 'sub_transfer'
    )

# %%
# connect walking network and transit network
nxG_final = nx.compose(walk_graph, nxG)

#tranit graph
transit_nodes = [n for n, d in nxG_final.nodes(data=True) if 'transit' in str(d.get('type'))]
t_x = np.array([nxG_final.nodes[n]['x'] for n in transit_nodes])
t_y = np.array([nxG_final.nodes[n]['y'] for n in transit_nodes])

new_edges = []
nearest_street_nodes = ox.distance.nearest_nodes(walk_graph, X=t_x, Y=t_y)

for i, t_node in enumerate(transit_nodes):
    s_node = nearest_street_nodes[i]
    
    # find distance
    x1, y1 = t_x[i], t_y[i]
    x2, y2 = walk_graph.nodes[s_node]['x'], walk_graph.nodes[s_node]['y']
    dist = euclidean_distance(x1, y1, x2, y2)

    if dist > max_dist: 
        print(f"Skipping stop {t_node} is {dist:.1f}ft from nearest street")
        continue

    weight = max(dist / walk_spd, min_weight)
    

    new_edges.append((t_node, s_node, {'weight': weight, 'relation': 'walk_transit'}))
    new_edges.append((s_node, t_node, {'weight': weight, 'relation': 'walk_transit'}))

nxG_final.add_edges_from(new_edges)

# %%
# check for unconnected transit stops
unconnected = [n for n in transit_nodes if nxG_final.degree(n) == 0]
print(f"Number of unconnected transit stops: {len(unconnected)}")

# check weights for walk_transit
weights = [d['weight'] for u, v, d in nxG_final.edges(data=True) if d['relation'] == 'walk_transit']
print(f"Min weight: {min(weights)}, Max weight: {max(weights)}")

# find specific edge with large weight
max_edge = max(nxG_final.edges(data=True), key=lambda x: x[2].get('weight', 0))
print(f"The longest edge is between {max_edge[0]} and {max_edge[1]}")
print(f"Relation: {max_edge[2].get('relation')}, Weight: {max_edge[2]['weight']}")

bad_node = nxG_final.nodes['bus_si_203833']
print(f"Coordinates of stop: {bad_node['y']}, {bad_node['x']}")

# %%
# add school nodes and walking edge to Graph
school_df = pd.read_csv("data/processed_schools_2015.csv")
school_gdf = gpd.GeoDataFrame(
    school_df,
    geometry=gpd.points_from_xy(school_df['lon'], school_df['lat']),
    crs="EPSG:4326"
).to_crs(crs_code)

sch_ids = [f"school_{code}" for code in school_df['LOCATION_CODE']]
sch_x = school_gdf.geometry.x.values
sch_y = school_gdf.geometry.y.values

for idx, rw in school_df.iterrows():
    sch_node = sch_ids[idx]
    nxG_final.add_node(
        sch_node, 
        x = sch_x[idx],
        y = sch_y[idx],
        pos= (sch_x[idx], sch_y[idx]), 
        name= rw['LOCATION_NAME'], 
        nta = rw['NTA_NAME'],
        sch_weight = rw['funding_per_student'], # (total funding/total students)
        type='school')

nearest_street_nodes = ox.distance.nearest_nodes(walk_graph, X=sch_x, Y=sch_y)

new_school_edges = []
for i, sch_node in enumerate(sch_ids):
    s_node = nearest_street_nodes[i]
    
    # Calculate Euclidean distance
    x1, y1 = sch_x[i], sch_y[i]
    x2, y2 = walk_graph.nodes[s_node]['x'], walk_graph.nodes[s_node]['y']
    dist = euclidean_distance(x1, y1, x2, y2)

    w = max(dist / walk_spd, min_weight)

    new_school_edges.append((sch_node, s_node, {'weight': w, 'relation': 'walk_school'}))
    new_school_edges.append((s_node, sch_node, {'weight': w, 'relation': 'walk_school'}))

nxG_final.add_edges_from(new_school_edges)
sch_weights = [d['weight'] for u, v, d in nxG_final.edges(data=True) if d['relation'] == 'walk_school']
print(f"Added {len(sch_ids)} schools and {len(new_school_edges)} connecting edges.")
print(f"Min weight: {min(sch_weights)}, Max weight: {max(sch_weights)}")
# %%
# add nta nodes and walking edge to Graph
nta_gdf = gpd.read_file("./data/spatial/nta_2010/nynta2010.shp").to_crs(crs_code)

#print("nta_shapefile cols:", nta_gdf.columns.tolist())

nta_df = pd.read_csv('data/nta_SE_indicators_2015.csv')
income_dict = nta_df.set_index('GeoID')['median_income_estimate'].to_dict()

rep_points = nta_gdf.geometry.representative_point()
nta_x = rep_points.x.values
nta_y = rep_points.y.values
nta_codes = nta_gdf['NTACode'].values

nearest_street_nodes = ox.distance.nearest_nodes(walk_graph, X=nta_x, Y=nta_y)
new_nta_edges = []

for i, rw in nta_gdf.iterrows():
    nta_code = nta_codes[i]
    nta_node = f"nta_{nta_code}"
    s_node = nearest_street_nodes[i]
    
    #coordinates & distance 
    x1, y1 = nta_x[i], nta_y[i]
    x2, y2 = walk_graph.nodes[s_node]['x'], walk_graph.nodes[s_node]['y']
    dist = euclidean_distance(x1, y1, x2, y2)

    # Add the Node
    nxG_final.add_node(
        nta_node,
        x = x1,
        y = y1,
        pos = (x1, y1),
        income = income_dict.get(nta_code),
        name = rw.get('NTAName', 'Unknown'),
        type = 'origin'
    )

    weight = max(dist / walk_spd, min_weight) 
    new_nta_edges.append((nta_node, s_node, {'weight': weight, 'relation': 'walk_nta'}))
    new_nta_edges.append((s_node, nta_node, {'weight': weight, 'relation': 'walk_nta'}))

nxG_final.add_edges_from(new_nta_edges)
nta_weights = [d['weight'] for u, v, d in nxG_final.edges(data=True) if d['relation'] == 'walk_nta']
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
# transit_travel, sub_transfer, walking, walk_transit, walk_school, walk_nta
shapes_df = pd.read_csv("data/processed_shapes_2015.csv")
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
with open('data/transit_graph.pkl', 'wb') as f: pickle.dump(nxG_final, f)

gdf_edges.to_file("data/network_data.gpkg", layer='edges', driver="GPKG")
gdf_nodes.to_file("data/network_data.gpkg", layer='nodes', driver="GPKG")