# pyright: basic
# %%
import numpy as np
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

from matplotlib.lines import Line2D
from adjustText import adjust_text
# %%
# grad results analysis
base_path = "data/"
grad_path = os.path.join(base_path,"raw/grad_results_1-15.csv")
grad_results = pd.read_csv(grad_path)
print(grad_results.columns)

# data cleaning
numeric_cols = [
    '# Total Cohort',              # size
    '% Grads',                     # success metric
    '% Advanced Regents of Cohort',# high 
    '% Total Regents of Cohort',   # standard
    '% Local of Cohort',           # safety-net
    '% Still Enrolled',            # potential future grads
    '% Dropout',                   # failure metric
    '% TASC (GED) of Cohort'       # alternative success
]

for cols in numeric_cols:
    grad_results[cols] = pd.to_numeric(grad_results[cols], errors='coerce')
    # s values are for suppressed data for student privacy 

    col_med = grad_results[cols].median()
    grad_results[cols] = grad_results[cols].fillna(col_med)

grad_results['advanced_gap'] = grad_results['% Grads'] - grad_results['% Advanced Regents of Cohort']

school_subgraph = grad_results[
    (grad_results['Report Category'] == "School") 
    | (grad_results['Report Category'] == "Charter School")
]

district_subgraph = grad_results[
    grad_results['Report Category'] == "District"
]
    
borough_subgraph = grad_results[
    grad_results['Report Category'] == 'Borough'
]

citywide_subgraph = grad_results[
    grad_results['Report Category'] == 'Citywide'
]

borough_map = {
    'K': 'Brooklyn',
    'X': 'Bronx',
    'M': 'Manhattan',
    'Q': 'Queens',
    'R': 'Staten Island'
}
borough = school_subgraph['Geographic Subdivision'].str[2].map(borough_map)
focused_schools = school_subgraph[school_subgraph['Cohort'] == '4 year August']
focused_schools = focused_schools[focused_schools['Cohort Year'] == 2011]
foc_borough = focused_schools['Geographic Subdivision'].str[2].map(borough_map)

# Dropout vs. Grad 
plt.figure(figsize=(10, 7))
sns.scatterplot(
    data=focused_schools, 
    x='% Still Enrolled', 
    y='% Dropout',
    hue=borough,
    alpha=0.6
)
plt.title('Persistence vs. Attrition : 2001-2015 Grad Results')
plt.savefig('assets/grad_result_sch_RvsA.png')

# Quantity vs Quality Graph
plt.figure(figsize=(10, 8))
sns.scatterplot(
    data=school_subgraph, 
    x='% Grads', 
    y='% Advanced Regents of Cohort',
    #size= '# Total Cohort',
    alpha=0.5,
    hue=borough, # Color by Borough
)
plt.plot([0, 100], [0, 100], color='red', linestyle='--') 
plt.title('Quantity vs. Quality: 2001-2015 Grad Results')
plt.savefig('assets/grad_result_sch_QvsQ.png')

# Grad vs Adv_Grad Box Plot Graph
fig, axes = plt.subplots(1, 2, figsize=(16, 6))


sns.boxplot(ax=axes[0], data=focused_schools, x=foc_borough, y='% Grads')
axes[0].set_title('Distribution of Graduation Rate of 2011 Cohort by Borough')
axes[0].set_ylim(0, 100)

sns.boxplot(ax=axes[1], data=focused_schools, x=foc_borough, y='% Advanced Regents of Cohort')
axes[1].set_title('Distribution of Advanced Regents Rate of 2011 Cohort by Borough')
axes[1].set_ylim(0, 100)

plt.tight_layout()
plt.savefig('bxplot_sch_bh.png')

# Advanced Gap Violin
plt.figure(figsize=(12, 6))
sns.violinplot(
    x=foc_borough, 
    y=focused_schools['advanced_gap'], 
    inner="quartile",
    hue=foc_borough,
    legend=False
)
plt.title('Quality Gap Distribution by Borough of 2011 Cohort')
plt.ylabel('Difference between Grad % and Advanced %')
plt.savefig('assets/sch_advanced_gap_violin.png')

# School Type  Comparison
plt.figure(figsize=(12, 6))
sns.boxplot(
    data=school_subgraph, 
    x='Report Category', 
    y='% Grads', 
    hue='Report Category',
    legend=False
)
plt.title('Graduation Rates by School Type: 2001-2015 Grad Results')
plt.ylabel('% Graduates')
plt.savefig('assets/sch_type_comp.png')

# Diploma Comparison Bar
composition = focused_schools.groupby(foc_borough)[[
    '% Advanced Regents of Cohort', 
    '% Total Regents of Cohort', 
    '% Local of Cohort'
]].mean()

composition['Standard Regents'] = composition['% Total Regents of Cohort'] - composition['% Advanced Regents of Cohort']
composition_plot = composition[['% Advanced Regents of Cohort', 'Standard Regents', '% Local of Cohort']]

composition_plot.plot(kind='bar', stacked=True, figsize=(12, 7), colormap='viridis')
plt.title('Average Diploma Composition by Borough (2011 Cohort)')
plt.ylabel('Percentage of Total Cohort')
plt.legend(title='Diploma Type', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('assets/diploma_composition_bar.png')
# %%
# processed schools analysis
school_df = pd.read_csv("data/processed_schools_2015.csv")

school_df['Borough'] = school_df['LOCATION_CODE'].str[0].map(borough_map)

## funding vs grad
plt.figure(figsize=(12, 7))
sns.scatterplot(
    data=school_df, 
    x='funding_per_student', 
    y='grad_rate', 
    size='size',        # Bubbles represent school size
    hue='Borough',      # Color by neighborhood to see clusters
    alpha=0.4,
    sizes=(40, 500),
    palette='Set1',
)

top_performers = pd.concat([
    school_df.nlargest(2, 'grad_rate'),
    school_df.nlargest(2, 'funding_per_student')
]).drop_duplicates(subset=['LOCATION_CODE'])

texts = []
top_performers = pd.concat([
    school_df.nlargest(3, 'grad_rate'),
    school_df.nlargest(3, 'funding_per_student')
]).drop_duplicates(subset=['LOCATION_CODE'])

for i, rw in top_performers.iterrows():
    texts.append(plt.text(
        rw['funding_per_student'], 
        rw['grad_rate'], 
        rw['NTA_NAME'], 
        fontsize=10, 
        weight='bold'
    ))

adjust_text(texts, arrowprops=dict(arrowstyle='->', color='black', lw=0.5))
plt.title('NYC Schools: Funding vs. Graduation Rate (2015)', fontsize=15)
plt.xlabel('Funding Per Student ($)', fontsize=12)
plt.ylabel('Graduation Rate (%)', fontsize=12)

plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left',borderaxespad=0)
plt.grid(True, linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig("assets/fund_grad_bor.png")

## spatial performance
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson").to_crs(epsg=4326)
schools_gdf = gpd.GeoDataFrame(
    school_df, 
    geometry=gpd.points_from_xy(school_df['lon'], school_df['lat']),
    crs="EPSG:4326"
)
fig, ax = plt.subplots(figsize=(14, 12))
boroughs.plot(ax=ax, color='#f2f2f2', edgecolor='black', linewidth=0.5, zorder=1)
sns.scatterplot(
    data=school_df,
    x='lon',
    y='lat',
    hue='adv_regents_rate',
    size='grad_rate',
    palette='viridis',
    sizes=(20, 400),
    alpha=0.4,
    edgecolor='white',
    linewidth=0.5,
    ax=ax,
    zorder=2
)

leg = ax.legend(
    bbox_to_anchor=(1.02, 1), 
    loc='upper left', 
    title="School Metrics",
    fontsize='medium',
)

ax.set_title('NYC School Performance Geography (2015)', fontsize=18, pad=20)
ax.set_aspect(1.3)
ax.axis('off')

plt.tight_layout()
plt.savefig("assets/sch_perf.png")

## funding disparity
plt.figure(figsize=(12, 6))
other_categories = [
    'Special Education', 
    'Home School', 
    'Alternative' 
]
labels = [l for l in school_df['LOCATION_TYPE_DESCRIPTION'].unique() if l not in other_categories]
labels.append('Other/Specialized')

sns.violinplot(
    data=school_df, 
    x=school_df['LOCATION_TYPE_DESCRIPTION'].replace(other_categories, 'Other/Specialized'), 
    y=school_df['funding_per_student'], 
    inner="box", 
    hue=school_df['LOCATION_TYPE_DESCRIPTION'].replace(other_categories, 'Other/Specialized'),
    legend=False
)

plt.xticks(rotation=45)
plt.title('Distribution of Funding per Student by School Type')
plt.ylabel('Funding ($)')
plt.savefig("assets/sch_type.png")
# %%
