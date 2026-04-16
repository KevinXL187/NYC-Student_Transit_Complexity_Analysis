# pyright: basic
import os, pickle
import networkx as nx
import geopandas as gpd
import numpy as np


def calculate_CCI(nx_graph, origin, dest):
    transfer_penalty = 300
    results = []
    nta_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'origin']
    school_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'school']

    # checks if graph is connected
    if not nx.is_connected(nx_graph.to_undirected()):
        print("Warning - graph has isolated islands and some schools will be unreachable")

    for start_node in nta_nodes:
        distances, paths = nx.single_source_dijkstra_path_length(nx_graph, start_node, weight='weight')
        nta_cci_score = 0
        reachable_qualities = []

        for target in school_nodes:
            if target in paths:

                path = paths[target]
                time = distances[target]
                num_transfers = 0
                prev_relation = None
                
                # Step through the path edges to count mode switches
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    edge_data = nx_graph.get_edge_data(u, v)
                    rel = edge_data[0].get('relation') if isinstance(edge_data, dict) and 0 in edge_data else edge_data.get('relation')
                    
                    if prev_relation and rel != prev_relation:
                        if 'walking' in prev_relation and 'transit' in rel:
                            num_transfers += 1 # Walk -> Bus/Subway
                        elif 'transit' in prev_relation and 'transit' in rel:
                            num_transfers += 1 # Bus -> Subway transfer
                    
                    prev_relation = rel

            travel_times = distances.get(target, np.nan)

            sch_

if __name__ == "__main__":

    # loading data
    with open('my_graph.pkl', 'rb') as f:
        nx_graph = pickle.load(f)

    gdf_edges = gpd.read_file('network_data.gpkg', layers='edges')
    gdf_nodes = gpd.read_file('network_data.gpkg', layers='nodes')