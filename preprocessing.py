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

def process_schools(input_path, output_path):
    sch_df = pd.read_csv(input_path)
    
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

    clean_df.to_csv(output_path, index=False)

if __name__ == "__main__":
    raw_csv = "./data/spatial/school_points_15.csv"
    processed_csv = "processed_schools_2015.csv"

    process_schools(raw_csv, processed_csv)