# pyright: basic
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

def verify_graph_results(stops_file, edges_file):
    print("\n--- Starting Validation ---")
    stops = pd.read_csv(stops_file)
    edges = pd.read_csv(edges_file)

    # check count of each weights
    """
        300 == spatial_transfer
        180 == subway transit_transfer

    """
    top_weights = edges['weight'].value_counts().head(5)
    print("counts of top weights")
    print(top_weights)
    print()

    # check stop mode and stop_id matches
    mismatch = (stops['mode'].str[:3] != stops['stop_id'].str[:3]).sum()
    print(f"number of mistach {mismatch}")

    # check if any source == target
    self_loop = (edges['source'] == edges['target']).sum()
    print(f"number of self_loop {self_loop}")
    
    # check number of 0 weights
    zero = (edges['weight'] == 0.0).sum()
    print(f"number of 0 weight edges {zero}")

    # check for duplicates
    duplicates = edges.duplicated(subset=['source', 'target', 'type']).sum()
    print(f"number of duplicates {duplicates}")

    # check for negtaive weight error
    neg_weights = (edges['weight'] < 0).sum()
    print(f"number of negative weight {neg_weights}")

    # check for degree outlier
    max_degree = edges['source'].value_counts().max()
    print(f"highest stop degree is {max_degree} outgoing connections")
    if max_degree > 50: print("some stops have very high connectivity (check KDTree radius)")

    # check connectivity between modes
    spatial = edges[edges['type'] == 'spatial_transfer']
    print(f"found {len(spatial)} spatial transfer (walking) links.")
    
    # check for islands (stops with no edges)
    connected_stops = set(edges['source']).union(set(edges['target']))
    missing_stops = stops[~stops['stop_id'].isin(connected_stops)]
    print(f"number of islands {len(missing_stops)}")

    # 19 stops are isolated, could be because stops are used outside of my filters or retired stops, negligible

    print("--- Validation Complete ---\n")

def visual_representation(stops_file, edges_file):  
    boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson")
    stops = pd.read_csv(stops_file)

    stops_gdf = gpd.GeoDataFrame(
        stops, 
        geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat),
        crs="EPSG:4326"
    )

    fig, ax = plt.subplots(figsize=(15, 15))
    boroughs.to_crs("EPSG:4326").plot(
        ax=ax, color='#f0f0f0', edgecolor='#666666', linewidth=0.8, zorder=1
    )

    for mode, df in stops_gdf.groupby('mode'):
        color = 'red' if mode == 'subway' else 'royalblue'
        label = 'Subway Stations' if mode == 'subway' else 'Bus Stops'
        df.plot(
            ax=ax, 
            color=color, 
            markersize=2, 
            alpha=0.3,
            label=label,
            zorder=2 if mode == 'bus' else 3
        )

    plt.title("NYC Transit Network Coverage Verification (2015)", fontsize=18)
    plt.legend(markerscale=10)
    ax.set_axis_off()
    
    output_file = "assets/transit_coverage_verification.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')

if __name__ == '__main__':
    verify_graph_results("data/processed_stops_2015.csv", "data/processed_edges_2015.csv")
    visual_representation("data/processed_stops_2015.csv", "data/processed_edges_2015.csv")