## Dataset
```
gtfs: 2015
    subway - [https://mobilitydatabase.org/feeds/gtfs/mdb-516]
    bus - [https://mobilittabase.org/feeds/gtfs/mdb-510]
    subway_supplemented - [https://mobilitydatabase.org/feeds/gtfs/mdb-511] (much more complex)
graudation_results: 2001-2011
    https://data.cityofnewyork.us/Education/Graduation-results-for-Cohorts-2001-to-2011-Classe/9vpe-8zuf/about_data
school funding : 2014-2015
    [https://data.cityofnewyork.us/Education/2014-2015-School-Budget-Overview/ven4-h25u/about_data]
school population : 2014-2015
    [https://data.cityofnewyork.us/Education/2014-2015-DOE-High-School-Directory/n3p6-zve2/about_data]
school_indicators : not relevant
school_points : 2014-2015
    [https://data.cityofnewyork.us/Education/2014-2015-School-Locations/fxs2-faah/about_data]
borough_boundaries : current, should be close enough
walk_graph : current, should be close enough
nta data :  2010 NTA 
    [https://www.nyc.gov/content/planning/pages/resources/datasets/neighborhood-tabulation]
acs nta data : 2012 to 2016 based on 2010 NTA data 
    [https://data.cityofnewyork.us/City-Government/Demographic-Profiles-of-ACS-5-Year-Estimates-at-th/8cwr-7pqn/about_data]
```

## Folder Structure
```
├── assets
│   ├── *.png files
├── data 
    ├── adjusted_cci_result.csv
    ├── adjusted_cci_result_graph.pkl
    ├── data_range.txt
    ├── missing_ntas_15.csv
    ├── missing_school_15.csv
    ├── network_data.gpkg
    ├── nta_SE_indicators_2015.csv
    ├── other
    │   ├── acs_nta
    │   │   ├── demo_2016acs5yr_nta.csv
    │   │   ├── demo_2016acs5yr_nta.xlsx
    │   │   ├── econ_2016acs5yr_nta.csv
    │   │   ├── econ_2016acs5yr_nta.xlsx
    │   │   ├── hous_2016acs5yr_nta.csv
    │   │   ├── hous_2016acs5yr_nta.xlsx
    │   │   ├── soc_2016acs5yr_nta.csv
    │   │   └── soc_2016acs5yr_nta.xlsx
    │   ├── school_budget_15.csv
    │   └── school_info_15.csv
    ├── processed_edges_2015.csv
    ├── processed_schools_2015.csv
    ├── processed_shapes_2015.csv
    ├── processed_stops_2015.csv
    ├── raw
    │   ├── grad_results_1-15.csv
    │   └── gtfs_data
    │       ├── bus_gtfs
    │       │   ├── bronx_bus_gtfs
    │       │   │   ├── agency.txt
    │       │   │   ├── calendar_dates.txt
    │       │   │   ├── calendar.txt
    │       │   │   ├── routes.txt
    │       │   │   ├── shapes.txt
    │       │   │   ├── stops.txt
    │       │   │   ├── stop_times.txt
    │       │   │   └── trips.txt
    │       │   ├── brooklyn_bus_gtfs
    │       │   │   ├── agency.txt
    │       │   │   ├── calendar_dates.txt
    │       │   │   ├── calendar.txt
    │       │   │   ├── routes.txt
    │       │   │   ├── shapes.txt
    │       │   │   ├── stops.txt
    │       │   │   ├── stop_times.txt
    │       │   │   └── trips.txt
    │       │   ├── manhattan_bus_gtfs
    │       │   │   ├── agency.txt
    │       │   │   ├── calendar_dates.txt
    │       │   │   ├── calendar.txt
    │       │   │   ├── routes.txt
    │       │   │   ├── shapes.txt
    │       │   │   ├── stops.txt
    │       │   │   ├── stop_times.txt
    │       │   │   └── trips.txt
    │       │   ├── mtabc_bus_gtfs
    │       │   │   ├── agency.txt
    │       │   │   ├── calendar_dates.txt
    │       │   │   ├── calendar.txt
    │       │   │   ├── routes.txt
    │       │   │   ├── shapes.txt
    │       │   │   ├── stops.txt
    │       │   │   ├── stop_times.txt
    │       │   │   └── trips.txt
    │       │   ├── queens_bus_gtfs
    │       │   │   ├── agency.txt
    │       │   │   ├── calendar_dates.txt
    │       │   │   ├── calendar.txt
    │       │   │   ├── routes.txt
    │       │   │   ├── shapes.txt
    │       │   │   ├── stops.txt
    │       │   │   ├── stop_times.txt
    │       │   │   └── trips.txt
    │       │   └── staten_island_bus_gtfs
    │       │       ├── agency.txt
    │       │       ├── calendar_dates.txt
    │       │       ├── calendar.txt
    │       │       ├── routes.txt
    │       │       ├── shapes.txt
    │       │       ├── stops.txt
    │       │       ├── stop_times.txt
    │       │       └── trips.txt
    │       └── subway_gtfs
    │           ├── agency.txt
    │           ├── calendar_dates.txt
    │           ├── calendar.txt
    │           ├── routes.txt
    │           ├── shapes.txt
    │           ├── stops.txt
    │           ├── stop_times.txt
    │           ├── transfers.txt
    │           └── trips.txt
    ├── raw_cci_result.csv
    ├── raw_cci_result_graph.pkl
    ├── spatial
    │   ├── Borough_Boundaries.geojson
    │   ├── gtfs
    │   ├── nta_2010
    │   │   ├── nynta2010.dbf
    │   │   ├── nynta2010.prj
    │   │   ├── nynta2010.shp
    │   │   ├── nynta2010.shp.xml
    │   │   └── nynta2010.shx
    │   └── school_points_15.csv
    └── transit_graph.pkl
├── data_analysis.py
├── exploratory_ds.py
├── gtfs_data_verification.py
├── gtfs_preprocessing.py
├── interactive_graph.py
├── modeing.py
├── nyc_transit_complexity.html
├── nyc_transit_complexity.pdf
├── nyc_transit_complexity.qmd
├── preprocessing.py
├── README.md
├── requirements.txt
├── static_graph.py
└── transit_network.py
```