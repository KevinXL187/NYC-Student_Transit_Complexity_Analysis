# %%
# pyright: basic
import pickle
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import datashader as ds
import datashader.transfer_functions as tf
import spatialpandas as spd
import colorcet as cc
import networkx as nx

from matplotlib.lines import Line2D
# %%
# Load Transit Data
projected_crs = 'EPSG:2263'
gdf_edges = gpd.read_file('network_data.gpkg', layer='edges').to_crs(projected_crs)
gdf_nodes = gpd.read_file('network_data.gpkg', layer='nodes').to_crs(projected_crs)
boroughs = gpd.read_file("./data/spatial/Borough_Boundaries.geojson").to_crs(projected_crs)

minX, minY, maxX, maxY = boroughs.total_bounds
PLOT_H, PLOT_W = 4500, 4500

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
    if config['agg_func'] == 'mean':
        agg = map_cvs.line(spf_edges[spf_edges['edge_type'] == e_type], geometry='geometry', agg=ds.mean('travel_time'))
    else:
        agg = map_cvs.line(spf_edges[spf_edges['edge_type'] == e_type], geometry='geometry', agg=ds.count())

    img = tf.shade(agg, cmap=config['cmap'])
    
    if e_type == 'walking': continue
    if e_type == 'transit_travel': continue
    if e_type == 'sub_transfer': continue #all transfer appears as points instead of edges
    # TODO walk_type edges bearly show up
    #if e_type == 'walk_transit': continue
    #if e_type == 'walk_school': continue
    #if e_type == 'walk_nta' : continue
        
    img = tf.dynspread(
        img, 
        threshold=0.95, 
        max_px=edge_configs[e_type]['max_px']
        )
    

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

transit_color = cc.cm.bjy(0.7)
walk_color = "#555555"
transfer_color = cc.fire[150]

legend_config = [
    # nodes 
    Line2D([0], [0], marker='D', color='w', label='School', 
           markerfacecolor='red', markersize=6, linestyle='None'),
    Line2D([0], [0], marker='o', color='w', label='NTA Center', 
           markerfacecolor='green', markersize=6, linestyle='None'),
    Line2D([0], [0], marker='^', color='w', label='Subway Station', 
           markerfacecolor='navy', markersize=6, linestyle='None'),
    Line2D([0], [0], marker='v', color='w', label='Bus Stop', 
           markerfacecolor='blue', markersize=6, linestyle='None'),
    
    # edges
    Line2D([0], [0], color=transit_color, lw=2, label='Transit Line'),
    Line2D([0], [0], color=walk_color, lw=1.5, label='Walking Path'),
    Line2D([0], [0], color=transfer_color, lw=1.5, ls='--', label='Transfer/Link'),
]

leg = ax.legend(
    handles=legend_config, 
    loc='upper left', 
    frameon=True, 
    fontsize='small',
    title="NYC Transit Accessibility"
)
plt.tight_layout()
plt.show()

# %%
# Load CCI Data
prefix=['adjusted_', 'raw_']
with open (f"{prefix[0]}cci_result_graph.pkl", "rb") as f:
    cci_graph = pickle.load(f)

## visualization configs
# TODO : look at distribution to find a better max_dist
max_dist = 1500 
base_size = 10

# TODO : need better scaling methods than flat scaling
# min-max normalization, logarithmic scaling, square root scaling
# check distribution and variance
scale = 0.005
color_map_config = {
    'school': '#ff4d4d',          
    'origin': '#2ecc71',             
    'subway_transit': '#3498db',  
    'bus_transit': '#f1c40f',    
    'walk': '#95a5a6'             
}

sch_df = pd.read_csv('processed_schools_2015.csv')
funding_mp = sch_df.set_index('LOCATION_CODE')['funding_per_student'].to_dict()
funding_mp = {'school_' + key: value for key, value in funding_mp.items()}

gdf_indexed = gdf_nodes.set_index('stop_id')
for node_id, data in cci_graph.nodes(data=True):
    if node_id in gdf_indexed.index:
        rw = gdf_indexed.loc[node_id]
        n_type = attr.get('node_type')
        funding = funding_mp.get(node_id, 0)
        size = (funding*scale) if funding > 0 else base_size
        
        data.update({
            'pos': (row['geometry'].x, row['geometry'].y),
            'node_type': n_type,
            'color': color_map_config.get(n_type, '#ffffff'),
            'size': (funding * scale) if funding > 0 else base_size
        })

pos = nx.get_node_attributes(cci_graph, 'pos')
valid_edges = []
for u, v in cci_graph.edges():
    if u in pos and v in pas:
        dist = dist = np.linalg.norm(np.array(pos[u]) - np.array(pos[v]))
        if dist <= max_dist: valid_edges.append((u, v))

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
plt.show()
# %%
# Create masked version of CCI Graph
# Create direct CCI Graph
fig, ax = plt.subplots(figsize=(12, 12))
fig.patch.set_facecolor('#1a1a1a')
ax.set_facecolor('#1a1a1a')
boroughs.plot(ax=ax, color='#252525', edgecolor='#444444', linewidth=0.8, zorder=0)

pos = nx.get_node_attributes(masked_cci_graph, 'pos')
node_colors = [data.get('color') for n, data in masked_cci_graph.nodes(data=True)]
node_sizes = [data.get('size') for n, data in masked_cci_graphh.nodes(data=True)]
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
plt.show()