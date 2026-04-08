# %%
# pyright: basic
import os
import networkx as nx

# %%
# calculate Commute Complexity Index formula function

def calculate_CCI(G, origin, dest):

    path = nx.shortest_path(G, source=origin, target=dest, weight='weight')
    total_travel_time = nx.shortest_path_length(G, origin, dest, weight='weight')
        
    transfer_count = 0
    edge_types = []
        
    for i in range(len(path) - 1):
        u, v = path[i], path[i+1]
        edge_data = G.get_edge_data(u, v)

        rel = edge_data.get('relation')
        if rel == 'transfer':
            transfer_count += 1
            
        edge_types.append(rel)
    
    # CCI = (Total Time / Constant) * (1 + (Transfer Penalty * Num Transfers))
    transfer_penalty = 1.5
    cci = (total_travel_time / 60) * (1 + (transfer_count * transfer_penalty))
        
    return round(cci, 2)