import pandas as pd
import glob, os

def process_gtfs_edges(file_path):
    school_start="07:00:00"
    school_end="16:00:00"
    df = pd.read_csv(file_path)
    df = df[df['trip_id'].str.contains('Weekday', case=False)].copy()
    df = df[(df['arrival_time'] >= school_start) & (df['arrival_time'] <= school_end)]
    df = df.sort_values(by=['trip_id', 'stop_sequence'])

    # Helper to convert HH:MM:SS to total seconds for weight calculation
    def to_seconds(t_str):
        h, m, s = map(int, t_str.split(':'))
        return h * 3600 + m * 60 + s

    edges = []

    for _, trip_group in df.groupby('trip_id'):
        group = trip_group.to_dict('records')
        
        for i in range(len(group) - 1):
            curr_stop = group[i]
            next_stop = group[i+1]
            
            # Calculate weight (travel time in seconds)
            # travel_time = next_arrival - curr_departure
            try:
                weight = to_seconds(next_stop['arrival_time']) - to_seconds(curr_stop['departure_time'])
                edges.append({
                    'source_stop_id': curr_stop['stop_id'],
                    'target_stop_id': next_stop['stop_id'],
                    'travel_time_seconds': weight
                })
            except (ValueError, TypeError): continue

    edges_df = pd.DataFrame(edges)
    edges_df.to_csv('subway_stop_times_edges.csv', index=False)
    return edges_df

def concate_all_csv(dir_path, out_name):
    csv_files = glob.glob(os.path.join(dir_path, "*.csv"))
    dfs = []
    for file_path in csv_files:
        borough = os.path.basename(file_path)[:4]
        df = pd.read_csv(file_path)
        df['borough'] = borough
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df.to_csv(out_name, index=False)

def process_txt(file_path):
    df = pd.read_csv(os.path.join(file_path, "stops.txt"))
    df_trim = df.iloc[:, [0, 1, 3, 4]]
    df_trim.to_csv("staten_island_stops.csv", index=False)

if __name__ == '__main__':
    fp = "data/archieved/stop"
    process_gtfs_edges(fp)
    concate_all_csv(fp, "stops.csv")
    process_txt(fp)
