# pyright: basic
import os, pickle
import networkx as nx
import geopandas as gpd
import numpy as np


def calculate_CCI_with_Tpenalty(nx_graph):
    transfer_penalty = 300  # Penalty in seconds/units
    results = {}
    
    nta_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'origin']
    school_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'school']

    if not nx.is_connected(nx_graph.to_undirected()):
        print("Warning - graph has isolated islands and some schools will be unreachable")

    for start_node in nta_nodes:
        # Get both distances (weights) and the actual paths to calculate transfers
        distances, paths = nx.single_source_dijkstra(nx_graph, start_node, weight='weight')
        school_scores = {}

        for target in school_nodes:
            if target in paths:
                path = paths[target]
                base_time = distances[target]
                num_transfers = 0
                prev_relation = None
                
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    
                    # For MultiDiGraph, get the edge with the minimum weight or first available
                    edge_data = nx_graph.get_edge_data(u, v)
                    if isinstance(edge_data, dict): data = edge_data[0] 
                    else:   data = edge_data
                    
                    rel = data.get('relation', '')
                    
                    if prev_relation and rel != prev_relation:
                        # Logic: Transfer occurs when switching modes or transit lines
                        if ('walking' in prev_relation and 'transit' in rel) or \
                           ('transit' in prev_relation and 'transit' in rel):
                            num_transfers += 1
                    
                    prev_relation = rel
                
                # CCI = Time + (Transfers * Penalty)
                school_scores[target] = base_time + (num_transfers * transfer_penalty)
            else:   school_scores[target] = np.nan
        
        results[start_node] = school_scores
    
    return results

def calculate_CCI_no_Tpenalty(nx_graph):
    if not nx.is_connected(nx_graph.to_undirected()):
        print("Warning - graph has isolated islands and some schools will be unreachable")

    nta_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'origin']
    school_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'school']

    results = {}

    for start_node in nta_nodes:
        distances = nx.single_source_dijkstra_path_length(nx_graph, start_node, weight='weight')
        school_score = {}
        for target_node in school_nodes:
            travel_time = distances.get(target_node, np.nan)
            school_score[target_node] = travel_time
        results[start_node] = school_score
    
    return results
        

if __name__ == "__main__":

    # loading data
    with open('my_graph.pkl', 'rb') as f:
        nx_graph = pickle.load(f)

    gdf_edges = gpd.read_file('network_data.gpkg', layers='edges')
    gdf_nodes = gpd.read_file('network_data.gpkg', layers='nodes')