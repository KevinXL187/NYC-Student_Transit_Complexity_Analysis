# pyright: basic
import os
import networkx as nx
import geopandas as gpd


def calculate_CCI(nx_graph, origin, dest):
    nta_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'origin']
    school_nodes = [n for n, d in nx_graph.nodes(data=True) if d.get('type') == 'school']

    # checks if graph is connected
    if not nx.is_connected(nx_graph.to_undirected()):
        print("Warning - graph has isolated islands and some schools will be unreachable")

    for start_nodes in nta_nodes:
        distances = nx.single_source_dijkstra_path_length(nxG_final, start_nta, weight='weight')
        
        for target_nodes in school_nodes:
            travel_times = distances.get(target_nodes, np.nan)

            sch_

if __name__ == "__main__":

    # loading data
    with open('my_graph.pkl', 'rb') as f:
        nx_graph = pickle.load(f)

    gdf_edges = gpd.read_file('network_data.gpkg', layers='edges')
    gdf_nodes = gpd.read_file('network_data.gpkg', layers='nodes')