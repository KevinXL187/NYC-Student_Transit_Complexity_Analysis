# %%
# pyright: basic
import pickle
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import datashader as ds
import datashader.transfer_functions as tf
import spatialpandas as spd
import colorcet as cc
import matplotlib.colors as mcolors
import networkx as nx
import seaborn as sns

from matplotlib.lines import Line2D

def get_color(cmap_attr, index=0.5):
    if isinstance(cmap_attr, list):
        idx = int(index * (len(cmap_attr) - 1))
        return cmap_attr[idx]
    else:
        return mcolors.to_hex(cmap_attr(index))

# %%
# Load Transit Data
projected_crs = 'EPSG:2263'
gdf_edges = gpd.read_file('data/network_data.gpkg', layer='edges').to_crs(projected_crs)
gdf_nodes = gpd.read_file('data/network_data.gpkg', layer='nodes').to_crs(projected_crs)
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson").to_crs(projected_crs)

minX, minY, maxX, maxY = boroughs.total_bounds
PLOT_H, PLOT_W = 4500, 4500

num_edges = len(gdf_edges)
num_nodes = len(gdf_nodes)

print(f"Nodes: {num_nodes}")
print(f"Edges: {num_edges}")
# %%
# Create Transit Graph
spf_edges = spd.GeoDataFrame(gdf_edges)
edge_configs = {
    'transit_travel': {'cmap': cc.cm.bjy, 'agg_func': 'mean', 'max_px' : 3},
    'sub_transfer': {'cmap': cc.cm.coolwarm, 'agg_func': 'count', 'max_px' : 3},
    'walking': {'cmap': cc.gray, 'agg_func': 'mean', 'max_px' : 1},
    'walk_transit': {'cmap': cc.fire, 'agg_func': 'mean', 'max_px' : 2},
    'walk_school': {'cmap': cc.fire, 'agg_func': 'mean', 'max_px' : 2},
    'walk_nta': {'cmap': cc.fire, 'agg_func': 'mean', 'max_px' : 2}
}
order_configs = [
    'walking', 'transit_travel', 'sub_transfer',
    'walk_transit', 'walk_school', 'walk_nta'
]
node_configs = {
    'school': {'marker': 'D', 'color': 'red', 'size': 2.8},
    'origin': {'marker': 'o', 'color': 'green', 'size': 2.8},
    'subway_transit': {'marker': '^', 'color': 'navy', 'size': 1.5},
    'bus_transit': {'marker': 'v', 'color': 'blue', 'size': 1.5},
}

fig, ax = plt.subplots(figsize=(25, 25))
fig.patch.set_facecolor('#1a1a1a')
ax.set_aspect('equal')
boroughs.plot(ax=ax, color='#1a1a1a', edgecolor='#878787', linewidth=0.75, zorder=0)

x_range = (minX, maxX)
y_range = (minY, maxY)

map_cvs = ds.Canvas(plot_height=PLOT_H, plot_width=PLOT_W, x_range=x_range, y_range=y_range)
images = []

# edges
for e_type in order_configs:
    config = edge_configs[e_type]
    subset = spf_edges[spf_edges['edge_type'] == e_type]
    
    agg = map_cvs.line(subset, geometry='geometry', agg=ds.count())
    img = tf.shade(agg, cmap=config['cmap'], how='eq_hist')

    # blue -> bus, gray -> between bus/sub, yellow -> transit
    # on bjy colormap

    if e_type == 'transit_travel':
        img = tf.spread(img, px=2)
    elif 'walk' in e_type:
        img = tf.spread(img, px=1)
    
    img_array = img.to_pil().convert('RGBA')
    images.append(img_array)


borders = [minX, maxX, minY, maxY]
for img in images:
    ax.imshow(img, extent=borders, zorder=1, aspect='equal')

# nodes
for n_type, df in gdf_nodes.groupby('node_type'):
    if n_type == 'walk': continue # Skip invisible walk nodes
    if 'transit' in str(n_type) :
        alpha = 0.25
    else:  alpha=1
    config = node_configs.get(n_type)

    df.plot(
        ax=ax,
        marker=config['marker'],
        color=config['color'],
        markersize=config['size'],
        alpha=alpha,
        zorder=5
    )

    ax.axis('off')

transit_color  = get_color(edge_configs['transit_travel']['cmap'], 0.7)
walking_color  = get_color(edge_configs['walking']['cmap'], 0.5)
transfer_color = get_color(edge_configs['sub_transfer']['cmap'], 0.6)
link_color     = get_color(edge_configs['walk_transit']['cmap'], 0.5)

legend_config = [
    # nodes 
    Line2D([0], [0], marker='D', color='w', label='School', 
           markerfacecolor='red', markersize=8, linestyle='None'),
    Line2D([0], [0], marker='o', color='w', label='NTA Center', 
           markerfacecolor='green', markersize=8, linestyle='None'),
    Line2D([0], [0], marker='^', color='w', label='Subway Station', 
           markerfacecolor='navy', markersize=6, linestyle='None'),
    Line2D([0], [0], marker='v', color='w', label='Bus Stop', 
           markerfacecolor='blue', markersize=6, linestyle='None'),
    
    # edges
    Line2D([0], [0], color=transit_color, lw=3, label='Transit Line'),
    Line2D([0], [0], color=walking_color, lw=1.5, label='Street Network'),
    Line2D([0], [0], color=link_color, lw=1.5, label='Walk to Transit'),
    Line2D([0], [0], color=transfer_color, lw=2, ls='--', label='Subway Transfer')
]

leg = ax.legend(
    handles=legend_config, 
    loc='upper left', 
    frameon=True, 
    fontsize='small',
    title="NYC Transit Accessibility"
)
plt.tight_layout()
plt.savefig("assets/transit_acc.png")

# %%
# Load CCI and School Data
prefix=['adjusted_', 'raw_']
with open (f"data/{prefix[0]}cci_result_graph.pkl", "rb") as f:
    cci_graph = pickle.load(f)

sch_df = pd.read_csv('data/processed_schools_2015.csv')
funding_mp = sch_df.set_index('LOCATION_CODE')['funding_per_student'].to_dict()
funding_mp = {'school_' + key: value for key, value in funding_mp.items()}
funding_vals = sch_df['funding_per_student']

max_dist = 46527
base_size = 10
scale = 0.05 # sqrt
color_map_config = {
    'school': '#d8e2e6',          
    'origin': '#2ecc71',                      
}

### checking for school size to check scale factors
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
linear_sizes = funding_vals * 0.005
sqrt_sizes = np.sqrt(funding_vals) * 1.5
log_sizes = np.log1p(funding_vals) * 5

sns.histplot(linear_sizes, kde=True, ax=axes[0], color='blue').set_title('Linear Sizes')
sns.histplot(sqrt_sizes, kde=True, ax=axes[1], color='green').set_title('Square Root Sizes')
sns.histplot(log_sizes, kde=True, ax=axes[2], color='red').set_title('Logarithmic Sizes')

print("Size Statistics Comparison:")
print(f"Linear - Mean: {linear_sizes.mean():.2f}, Std: {linear_sizes.std():.2f}")
print(f"Sqrt   - Mean: {sqrt_sizes.mean():.2f}, Std: {sqrt_sizes.std():.2f}")
print(f"Log    - Mean: {log_sizes.mean():.2f}, Std: {log_sizes.std():.2f}")
plt.savefig("assets/sch_size_distr.png")

gdf_indexed = gdf_nodes.set_index('stop_id')
for node_id, data in cci_graph.nodes(data=True):
    if node_id in gdf_indexed.index:
        rw = gdf_indexed.loc[node_id]
        n_type = rw.get('node_type')
        funding = funding_mp.get(node_id, 0)
        size = (np.sqrt(funding) * scale) if funding > 0 else base_size
        
        data.update({
            'pos': (rw['geometry'].x, rw['geometry'].y),
            'node_type': n_type,
            'color': color_map_config.get(n_type, '#ffffff'),
            'size': (funding * scale) if funding > 0 else base_size
        })

pos = nx.get_node_attributes(cci_graph, 'pos')
all_dist = []
valid_edges = []
for u, v in cci_graph.edges():
    if u in pos and v in pos:
        dist = dist = np.linalg.norm(np.array(pos[u]) - np.array(pos[v]))
        all_dist.append(dist)
        if dist < max_dist: valid_edges.append((u,v))

## distribution check for distance
dist_ser = pd.Series(all_dist)
print("Distance Distribution Check")
print(dist_ser.describe(percentiles=[.5, .75, .9, .95, .99]))

plt.figure(figsize=(10, 5))
sns.histplot(dist_ser, kde=True, color='teal')
plt.axvline(dist_ser.quantile(0.75), color='red', linestyle='--', label='75th Percentile')
plt.axvline(dist_ser.quantile(0.95), color='red', linestyle='--', label='95th Percentile')
plt.title("Distribution of Edge Distances in CCI Graph")
plt.xlabel("Distance Units")
plt.legend()
plt.savefig("assets/distr_edg_dist.png")


masked_cci_graph = cci_graph.edge_subgraph(valid_edges).copy()

print("Graph Overview")
print(f"Total Nodes {cci_graph.number_of_nodes()}")
print(f"Total Edges {cci_graph.number_of_edges()}")

attributes = ['pos', 'node_type', 'color', 'size']
attr_stats = {attr: {'nan': 0, 'zero': 0, 'missing': 0} for attr in attributes}

for n, data in cci_graph.nodes(data=True):
        for attr in attributes:
            if attr not in data:
                attr_stats[attr]['missing'] += 1
                continue
            
            val = data[attr]
            try:
                if np.any(pd.isna(val)):
                    attr_stats[attr]['nan'] += 1
            except: pass
            
            if attr == 'size' and val == 10:
                attr_stats[attr]['zero'] += 1

print("--- Attribute Diagnostics ---")
for attr, stats in attr_stats.items():
    print(f"Attribute: [{attr}]")
    print(f"  - Missing: {stats['missing']}")
    print(f"  - NaN values: {stats['nan']}")
    if attr == 'size':
        print(f"  - base values: {stats['zero']}")
    print("-" * 15)

# %%
# Create direct CCI Graph
fig, ax = plt.subplots(figsize=(12, 12))
fig.patch.set_facecolor('#1a1a1a')
ax.set_facecolor('#1a1a1a')
boroughs.plot(ax=ax, color='#252525', edgecolor='#444444', linewidth=0.8, zorder=0)

pos = nx.get_node_attributes(cci_graph, 'pos')
node_colors = [data.get('color') for n, data in cci_graph.nodes(data=True)]
node_sizes = [data.get('size') for n, data in cci_graph.nodes(data=True)]
weights = [data['weight'] for u, v, data in cci_graph.edges(data=True)]


## draw nodes and edges
edges = nx.draw_networkx_edges(
    cci_graph, pos, ax=ax,
    width=1.2,
    edge_color=weights,
    edge_cmap=plt.cm.plasma,
    alpha=0.4,
    arrows=True,
    arrowsize=10
)
nodes = nx.draw_networkx_nodes(
    cci_graph, pos, ax=ax,
    node_size = node_sizes,
    node_color = node_colors,
    alpha=0.7,
)

## create legend
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='School (Size ∝ Funding)',
           markerfacecolor=color_map_config['school'], markersize=10),
    Line2D([0], [0], marker='o', color='w', label='NTA Center',
           markerfacecolor=color_map_config['origin'], markersize=8),
]
ax.legend(handles=legend_elements, loc='upper left', frameon=False, 
          labelcolor='white', fontsize=10)

plt.title("NYC Community Cost Index (CCI) Network", color='white', fontsize=16, pad=20)
ax.set_axis_off()

sm = plt.cm.ScalarMappable(cmap=plt.cm.plasma, norm=plt.Normalize(vmin=min(weights), vmax=max(weights)))
cb = plt.colorbar(sm, ax=ax, shrink=0.5, pad=0.02)
cb.set_label('CCI Cost', color='white')
cb.ax.yaxis.set_tick_params(color='white', labelcolor='white')

plt.tight_layout()
plt.savefig("assets/all_cci_graph.png")
# %%
# Create masked version of CCI Graph
# Create direct CCI Graph
fig, ax = plt.subplots(figsize=(12, 12))
fig.patch.set_facecolor('#1a1a1a')
ax.set_facecolor('#1a1a1a')
boroughs.plot(ax=ax, color='#252525', edgecolor='#444444', linewidth=0.8, zorder=0)

pos = nx.get_node_attributes(masked_cci_graph, 'pos')
node_colors = [data.get('color') for n, data in masked_cci_graph.nodes(data=True)]
node_sizes = [data.get('size') for n, data in masked_cci_graph.nodes(data=True)]
weights = [data['weight'] for u, v, data in masked_cci_graph.edges(data=True)]


## draw nodes and edges
edges = nx.draw_networkx_edges(
    masked_cci_graph, pos, ax=ax,
    width=1.2,
    edge_color=weights,
    edge_cmap=plt.cm.plasma,
    alpha=0.4,
    arrows=True,
    arrowsize=10
)
nodes = nx.draw_networkx_nodes(
    masked_cci_graph, pos, ax=ax,
    node_size = node_sizes,
    node_color = node_colors,
    alpha=0.7,
)

## create legend
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='School (Size ∝ Funding)',
           markerfacecolor=color_map_config['school'], markersize=10),
    Line2D([0], [0], marker='o', color='w', label='NTA Center',
           markerfacecolor=color_map_config['origin'], markersize=8),
]
ax.legend(handles=legend_elements, loc='upper left', frameon=False, 
          labelcolor='white', fontsize=10)

plt.title("NYC Community Cost Index (CCI) Network", color='white', fontsize=16, pad=20)
ax.set_axis_off()

sm = plt.cm.ScalarMappable(cmap=plt.cm.plasma, norm=plt.Normalize(vmin=min(weights), vmax=max(weights)))
cb = plt.colorbar(sm, ax=ax, shrink=0.5, pad=0.02)
cb.set_label('CCI Cost', color='white')
cb.ax.yaxis.set_tick_params(color='white', labelcolor='white')

plt.tight_layout()
plt.savefig("assets/95th_cci_graph.png")
