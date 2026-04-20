# pyright: basic
import pandas as pd
import glob, os

from scipy.spatial import KDTree

def to_seconds(t_str):
    h, m, s = map(int, t_str.split(':'))
    return h * 3600 + m * 60 + s

def process_gtfs_data(gtfs_dir, prefix):
    # process stops
    stops_df = pd.read_csv(os.path.join(gtfs_dir, "stops.txt"))
    stops_df = stops_df[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']].copy()
    stops_df['stop_id'] = prefix + "_"+ stops_df['stop_id'].astype(str)
    stops_df['mode'] = 'subway' if 'sub' in prefix else 'bus'

    # process edges (travel time)
    st_df = pd.read_csv(os.path.join(gtfs_dir, "stop_times.txt"))
    edge_cols = ['source', 'target', 'weight', 'type']

    ## filter for weekdays and school time
    st_df = st_df[st_df['trip_id'].str.contains('Weekday|Wkd', case=False, na=False)].copy()
    st_df = st_df[(st_df['arrival_time'] >= "07:00:00") & (st_df['arrival_time'] <= "10:00:00")]
    st_df = st_df.sort_values(by=['trip_id', 'stop_sequence'])

    print(prefix)
    print(st_df.empty)

    edges = []
    for _, group in st_df.groupby('trip_id'):
        rows = group.to_dict('records')
        for i in range(len(rows) - 1):
            u, v = rows[i], rows[i+1]
            weight = to_seconds(v['arrival_time']) - to_seconds(u['departure_time'])
            if weight > 0:
                edges.append({
                    'source': f"{prefix}_{u['stop_id']}",
                    'target': f"{prefix}_{v['stop_id']}",
                    'weight': weight,
                    'type': 'transit_travel'
                })
    
    
    edges_df = pd.DataFrame(edges, columns=edge_cols)
    edges_df = edges_df.groupby(['source', 'target', 'type'], as_index=False)['weight'].mean()

    # process transfers for subway
    transfer_file = os.path.join(gtfs_dir, "transfers.txt")
    avg_transfer_time = 180
    min_transfer_time = 60

    if os.path.exists(transfer_file):
        trans_df = pd.read_csv(transfer_file)
        trans_list = []
        for _, row in trans_df.iterrows():
            time = row.get('min_transfer_time', None)
            if pd.isna(time) : time = avg_transfer_time
            elif time <= 0 : time = min_transfer_time

            trans_list.append({
                'source': f"{prefix}_{row['from_stop_id']}",
                'target': f"{prefix}_{row['to_stop_id']}",
                'weight': time,
                'type': 'transfer'
            })
        trans_df = pd.DataFrame(trans_list)
        edges_df = pd.concat([edges_df, trans_df])

    return stops_df, edges_df
    
if __name__ == '__main__':
    base_dir = "./data/raw/gtfs_data"

    source_map = {
        "sub": "subway_gtfs",
        "bus_bx": "bus_gtfs/bronx_bus_gtfs",
        "bus_bk": "bus_gtfs/brooklyn_bus_gtfs",
        "bus_mn": "bus_gtfs/manhattan_bus_gtfs",
        "bus_abc": "bus_gtfs/mtabc_bus_gtfs",
        "bus_qn": "bus_gtfs/queens_bus_gtfs",
        "bus_si": "bus_gtfs/staten_island_bus_gtfs"
    }

    all_stops = []
    all_edges = []

    for prefix, rel_path in source_map.items():
        full_path = os.path.join(base_dir, rel_path)
        s, e = process_gtfs_data(full_path, prefix)
        all_stops.append(s)
        all_edges.append(e)

    final_stops = pd.concat(all_stops)
    final_edges = pd.concat(all_edges)
    
    # Save the master files
    final_stops.to_csv("processed_stops_2015.csv", index=False)
    final_edges.to_csv("processed_edges_2015.csv", index=False)