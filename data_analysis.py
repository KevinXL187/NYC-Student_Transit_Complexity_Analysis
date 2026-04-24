# pyright: basic
import os, pickle, json
import networkx as nx
import geopandas as gpd
from numpy._core.numeric import False_
import pandas as pd
import numpy as np


def calculate_CCI(nx_graph, apply_penalty=True):
    transfer_penalty = 180

    for u, v, k, data in nx_graph.edges(keys=True, data=True):
        base_time = data.get('weight', 0)
        penalty = 0
        
        if apply_penalty:
            rel = data.get('relation', '')
            if rel == 'walk_transit':
                penalty = transfer_penalty * 1.75
            elif rel == 'sub_transfer':
                penalty = transfer_penalty * 1.25
        
        data['tmp_w'] = base_time + penalty

    nta_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'origin']
    school_nodes = {n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'school'}

    results = {}
    for start_node in nta_nodes:
        if start_node not in nx_graph:
            results[start_node] = {s: np.nan for s in school_nodes}
            continue
        lengths = nx.single_source_dijkstra_path_length(nx_graph, start_node, weight='tmp_w')

        results[start_node] = {s: lengths.get(s, np.nan) for s in school_nodes}
        
    return results
        
def CCI_graph(results, prefix):
    flattened_data = []
    for origin, schools in results.items():
        for school, cost in schools.items():
            flattened_data.append({
                'origin_id': origin,
                'school_id': school,
                'cci_cost': cost
            })
    
    cci_df = pd.DataFrame(flattened_data)
    cci_df.to_csv(f"cci_result.csv", index=False)
    print(f"Results saved to cci_result.csv")

    cci_nx = nx.DiGraph()
    
    for entry in flattened_data:
        if not np.isnan(entry['cci_cost']):
            cci_nx.add_edge(
                entry['origin_id'], 
                entry['school_id'], 
                weight=entry['cci_cost']
            )
            
    with open(f"{prefix}_cci_result_graph.pkl", 'wb') as f:
        pickle.dump(cci_nx, f)
        
    return cci_nx

if __name__ == "__main__":

    # loading data
    with open('transit_graph.pkl', 'rb') as f:
        nx_graph = pickle.load(f)

    gdf_edges = gpd.read_file('network_data.gpkg', layer='edges')
    gdf_nodes = gpd.read_file('network_data.gpkg', layer='nodes')

    raw_travel_time_results = calculate_CCI(nx_graph, False)
    penalty_adjusted_results = calculate_CCI(nx_graph)
    
    CCI_graph(raw_travel_time_results, 'raw')
    CCI_graph(penalty_adjusted_results, 'adjusted')