# pyright: basic
import pandas as pd
import pyproj
import os
def convert_coords(row):
    transformer = pyproj.Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    try:   # transform() expects (X, Y)
        lon, lat = transformer.transform(row['X_COORDINATE'], row['Y_COORDINATE'])
        return pd.Series({'lon': lon, 'lat': lat})
    except:
        return pd.Series({'lon': None, 'lat': None})

def process_schools(input_paths, output_path):
    sch_df = pd.read_csv(input_paths[0])
    
    coords = sch_df.apply(convert_coords, axis=1)
    sch_df = pd.concat([sch_df, coords], axis=1)
    sch_df = sch_df.dropna(subset=['lon', 'lat'])

    output_cols = [
        'LOCATION_CODE', 'LOCATION_NAME', 'lon', 'lat', 
        'LOCATION_TYPE_DESCRIPTION', 'NTA_NAME', 'LOCATION_CATEGORY_DESCRIPTION'
    ]
    clean_df = sch_df[output_cols].copy()
    clean_df['NTA_NAME'] = clean_df['NTA_NAME'].str.strip()
    #print(clean_df['LOCATION_CATEGORY_DESCRIPTION'].value_counts())
    clean_df = clean_df[(clean_df['LOCATION_CATEGORY_DESCRIPTION']  == 'High school') | 
                        (clean_df['LOCATION_CATEGORY_DESCRIPTION']  == 'K-12 all grades')]
    clean_df = clean_df.drop(columns=['LOCATION_CATEGORY_DESCRIPTION'])

    sch_pop = pd.read_csv(input_paths[1])
    clean_df['size'] = if sch_pop[''] == sch_pop['total_students']

    sch_fund = pd.read_csv(input_paths[2])

    # process funding .csv to a normailization weighted value
    # fsf + 
    clean_df['LOCATION_CODE'] == sch_fund['Location']
    clean_df['funding'] = sch_fund["S4: Label d: FY14 FSF Initial"]

    #clean_df.to_csv(output_path, index=False)

if __name__ == "__main__":
    raw_csv = 
    processed_csv = "processed_schools_2015.csv"

    raw_csvs = ["./data/spatial/school_points_15.csv", ]
    process_schools(raw_csvs, processed_csv)