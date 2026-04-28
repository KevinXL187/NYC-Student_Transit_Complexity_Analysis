# pyright: basic
import numpy as np
import pandas as pd
import pyproj

def convert_coords(row):
    transformer = pyproj.Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    try:   # transform() expects (X, Y)
        lon, lat = transformer.transform(row['X_COORDINATE'], row['Y_COORDINATE'])
        return pd.Series({'lon': lon, 'lat': lat})
    except:
        return pd.Series({'lon': None, 'lat': None})

def process_schools(input_paths, output_path):
    print("Processing school csvs")
    sch_df = pd.read_csv(input_paths[0])
    
    coords = sch_df.apply(convert_coords, axis=1)
    sch_df = pd.concat([sch_df, coords], axis=1)
    sch_df = sch_df.dropna(subset=['lon', 'lat'])

    output_cols = [
        'LOCATION_CODE', 'LOCATION_NAME', 'lon', 'lat', 
        'LOCATION_TYPE_DESCRIPTION', 'NTA_NAME', 'LOCATION_CATEGORY_DESCRIPTION'
    ]
    clean_df = sch_df[output_cols].copy()
    #print(clean_df['LOCATION_CATEGORY_DESCRIPTION'].value_counts())

    # filter for High schools and K-12
    clean_df = clean_df[(clean_df['LOCATION_CATEGORY_DESCRIPTION']  == 'High school') | 
                        (clean_df['LOCATION_CATEGORY_DESCRIPTION']  == 'K-12 all grades')]
    clean_df = clean_df.drop(columns=['LOCATION_CATEGORY_DESCRIPTION'])
    clean_df['NTA_NAME'] = clean_df['NTA_NAME'].str.strip()
    print("after HS filter", str(clean_df.notna().all(axis=1).sum()))

    clean_df_key = 'LOCATION_CODE'

    # process school funding
    sch_fund = pd.read_csv(input_paths[2])
    sch_fund[clean_df_key] = sch_fund['Location']
    sch_fund['budget'] = (
        sch_fund['S4: Label d: FY14 FSF Initial']
        .replace(r'[$,]', '', regex=True)
        .astype(float)
    )
    fund_subset = sch_fund[[clean_df_key, 'budget']].copy()
    clean_df = pd.merge(
        fund_subset, clean_df, on=clean_df_key, how="outer")
    print("after funding addition" , str(clean_df.notna().all(axis=1).sum()))

    # process school population
    sch_pop = pd.read_csv(input_paths[1])
    sch_pop[clean_df_key] = sch_pop['dbn'].astype(str).str[-4:]
    sch_pop['total_students'] = pd.to_numeric(
        sch_pop['total_students'].str.replace(r'[^\d-]', '', regex=True),
        errors='coerce'
    )
    pop_subset = sch_pop[[clean_df_key, 'total_students']].copy()
    pop_subset.rename(columns={'total_students': 'size'}, inplace=True)
    clean_df = pd.merge(
        pop_subset, clean_df, on=clean_df_key, how="outer")
    print("after population addition" , str(clean_df.notna().all(axis=1).sum()))

    # process school grad_results
    grad_df = pd.read_csv(input_paths[3], low_memory=False)
    grad_df = grad_df[
        (grad_df['Report Category'].isin(['School', 'Charter School'])) &
        (grad_df['Category'] == 'All Students') &
        (grad_df['Cohort Year'] == 2011) &
        (grad_df['Cohort'] == '4 year June')
    ]
    grad_df[clean_df_key] = grad_df['Geographic Subdivision'].astype(str).str[-4:]
    grad_df['% Grads'] = pd.to_numeric(grad_df['% Grads'], errors='coerce')
    grad_df['% Advanced Regents of Cohort'] = pd.to_numeric(grad_df['% Advanced Regents of Cohort'], errors='coerce')
    grad_subset = grad_df[[clean_df_key, '% Grads', '% Advanced Regents of Cohort']].copy()
    grad_subset.rename(columns={'% Grads': 'grad_rate', '% Advanced Regents of Cohort': 'adv_regents_rate'}, inplace=True)
    clean_df = pd.merge(
        clean_df, grad_subset, on=clean_df_key, how="outer"
    )
    print('after grad results', clean_df.notna().all(axis=1).sum())

    # drop cols based on shape_point df
    clean_df.dropna(subset=['LOCATION_NAME'], inplace=True)
    print('after dropping on location_name', clean_df.notna().all(axis=1).sum())

    # look at missing data
    print('number of nan rows', clean_df.isna().any(axis=1).sum())
    missing_schools = clean_df[clean_df.isna().any(axis=1)]['LOCATION_CODE']
    missing_schools = pd.merge(clean_df, missing_schools, on=clean_df_key, how="right")
    missing_schools.to_csv('missing_school_15.csv', index=False)
    # mostly full of k-12 and charter school
    print(clean_df.shape)

    # fill in missing data
    med_pop = clean_df['size'].median()
    clean_df['size'] = clean_df['size'].fillna(med_pop)
    med_fund = clean_df['budget'].median()
    clean_df['budget'] = clean_df['budget'].fillna(med_fund)
    med_grad = clean_df['grad_rate'].median()
    clean_df['grad_rate'] = clean_df['grad_rate'].fillna(med_grad)
    med_agrad = clean_df['adv_regents_rate'].median()
    clean_df['adv_regents_rate'] = clean_df['adv_regents_rate'].fillna(med_agrad)

    print('number of nan rows', clean_df.isna().any(axis=1).sum())

    # normalize/weight and fill in missing data
    clean_df['funding_per_student'] = clean_df['budget']/clean_df['size']
    clean_df['weighted_accessibility'] = clean_df['funding_per_student']*clean_df['grad_rate']
    clean_df['weighted_accessibility_adv'] = clean_df['funding_per_student']*clean_df['adv_regents_rate']

    clean_df.to_csv(output_path, index=False)

def process_acs(output_path):
    print("Processing nta_acs csvs")

    files = {
        'dem' : "./data/other/acs_nta/demo_2016acs5yr_nta.csv",
        'econ' : "./data/other/acs_nta/econ_2016acs5yr_nta.csv",
        'hous' : "./data/other/acs_nta/hous_2016acs5yr_nta.csv",
        'soc' : "./data/other/acs_nta/soc_2016acs5yr_nta.csv"
    }

    cols = ['GeoID', 'GeogName', 'Borough']
    mappings = {
        'econ': {
            'PBwPvP': 'poverty_rate_pct',
            'MdHHIncE': 'median_income_estimate',
            'CvLFUEm2P': 'unemployment_rate_pct'
        },
        'dem': {
            'Pop15t19P': 'pop_15_to_19_pct'
        },
        'hous': {
            'GRPI35plP': 'rent_burdened_35plus_pct'
        },
        'soc': {
            'EA_BchDHP': 'bachelors_deg_or_higher_pct',
            'LgOEnLEP1P': 'limited_english_proficiency_pct'
        }
    }

    main_df = pd.read_csv(files['econ'])
    main_df = main_df[cols + list(mappings['econ'].keys())]
    
    main_df = main_df.rename(columns=mappings['econ'])
    for key in ['dem', 'hous', 'soc']:
        df = pd.read_csv(files[key])
        cols_nd = ['GeoID'] + [c for c in mappings[key].keys() if c in df.columns]
        df_subset = df[cols_nd].rename(columns=mappings[key])
        main_df = pd.merge(main_df, df_subset, on="GeoID", how='outer')

    # missing data
    missing_ntas = main_df[main_df.isna().any(axis=1)]['GeoID']
    missing_ntas = pd.merge(missing_ntas, main_df, on='GeoID', how='right')
    missing_ntas.to_csv('missing_ntas_15.csv', index=False)

    # fill in data
    numeric_cols = main_df.select_dtypes(include=np.number).columns
    print(numeric_cols)
    main_df[numeric_cols] = main_df[numeric_cols].fillna(main_df[numeric_cols].median())

    main_df.to_csv(output_path, index=False)
    print('number of nan rows', main_df.isna().any(axis=1).sum())
    print("ACS df shape:", main_df.shape)
    print("cols:", main_df.columns.to_list())

if __name__ == "__main__":
    processed_sch_csv = "data/processed_schools_2015.csv"
    raw_sch_csvs = [
        "./data/spatial/school_points_15.csv", 
        "./data/other/school_info_15.csv", 
        "./data/other/school_budget_15.csv",
        "./data/raw/grad_results_1-15.csv"]

    process_schools(raw_sch_csvs, processed_sch_csv)

    processed_acs_csv = "data/nta_SE_indicators_2015.csv"
    process_acs(processed_acs_csv)
