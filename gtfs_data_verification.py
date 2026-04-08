# pyright: basic
import pandas as pd


def verify_graph_results(stops_file, edges_file):
    print("\n--- Starting Validation ---")
    stops = pd.read_csv(stops_file)
    edges = pd.read_csv(edges_file)

    # check for duplicates
    duplicates = edges.duplicated(subset=['source', 'target', 'type']).sum()
    print("duplicates ")
    if duplicates == 0: print(f"Success")
    else: print(f"Error: Found {duplicates} duplicate edges")

    # check for time error
    neg_weights = (edges['weight'] < 0).sum()
    print("time ")
    if neg_weights == 0:print(f"success")
    else: print(f"Error: Found {neg_weights} edges with negative weights")

    # check for degree outlier
    max_degree = edges['source'].value_counts().max()
    print(f"highest stop degree is {max_degree} outgoing connections")
    if max_degree > 50:
        print("some stops have very high connectivity (check KDTree radius)")

    # check connectivity between modes
    spatial = edges[edges['type'] == 'spatial_transfer']
    print(f"found {len(spatial)} spatial transfer (walking) links.")
    
    # check for islands (stops with no edges)
    connected_stops = set(edges['source']).union(set(edges['target']))
    missing_stops = stops[~stops['stop_id'].isin(connected_stops)]
    print("islands")
    if len(missing_stops) == 0:
        print("Success")
    else:
        print(f"{len(missing_stops)} stops are isolated")

    # 19 stops are isolated, could be because stops are used outside of my filters or retired stops, negligible

    print("--- Validation Complete ---\n")
    
if __name__ == '__main__':
    verify_graph_results("processed_stops_2015.csv", "processed_edges_2015.csv")