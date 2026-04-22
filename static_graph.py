# %%
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
PLOT_H, PLOT_W = 1500, 1500

# %%
# Create Transit Graph
spf_edges = spd.GeoDataFrame(gdf_edges)
edge_configs = {
    'transit_travel': {'cmap': cc.cm.bjy, 'agg_func': 'mean'},
    'transfer': {'cmap': cc.cm.coolwarm, 'agg_func': 'count'},
    'walking': {'cmap': cc.gray, 'agg_func': 'mean'},
    'walk_transfer': {'cmap': cc.fire, 'agg_func': 'mean'},
    'walking_school': {'cmap': cc.fire, 'agg_func': 'mean'},
    'walking_nta': {'cmap': cc.fire, 'agg_func': 'mean'}
}
order_configs = [
    'walking', 'transit_travel', 'transfer',
    'walk_transfer', 'walking_school', 'walking_nta'
]
node_configs = {
    'school': {'marker': 'D', 'color': 'red', 'size': 2.8},
    'nta': {'marker': 'o', 'color': 'green', 'size': 2.8},
    'subway_transit': {'marker': '^', 'color': 'navy', 'size': 1.5},
    'bus_transit': {'marker': 'v', 'color': 'blue', 'size': 1.5},
}

fig, ax = plt.subplots(figsize=(12, 12))
fig.patch.set_facecolor('#1a1a1a')
ax.set_aspect('equal')
boroughs.plot(ax=ax, color='#1a1a1a', edgecolor='#333333', linewidth=0.75, zorder=0)

x_range = (minX, maxX)
y_range = (minY, maxY)

map_cvs = ds.Canvas(plot_height=PLOT_H, plot_width=PLOT_W, x_range=x_range, y_range=y_range)
images = []

for e_type in order_configs:
    config = edge_configs[e_type]
    if config['agg_func'] == 'mean':
        agg = map_cvs.line(spf_edges[spf_edges['edge_type'] == e_type], geometry='geometry', agg=ds.mean('travel_time'))
    else:
        agg = map_cvs.line(spf_edges[spf_edges['edge_type'] == e_type], geometry='geometry', agg=ds.count())

    img = tf.shade(agg, cmap=config['cmap'])
    
    if e_type == 'walking':
        continue
        img = tf.dynspread(img, threshold=0.5, max_px=1)
    else :
        img = tf.dynspread(img, threshold=0.5, max_px=3)
    

    img_array = img.to_pil().convert('RGBA')
    images.append(img_array)

borders = [minX, maxX, minY, maxY]
for img in images:
    ax.imshow(img, extent=borders, zorder=1, aspect='equal')

for n_type, df in gdf_nodes.groupby('node_type'):
    if n_type == 'walk': continue # Skip invisible walk nodes
    config = node_configs.get(n_type, {'marker': 'o', 'color': 'grey', 'size': 0.1})

    df.plot(
        ax=ax,
        marker=config['marker'],
        color=config['color'],
        markersize=config['size'],
        alpha=1,
        zorder=5
    )

    ax.axis('off')

legend_config = [
    Line2D([0], [0], marker='D', color='w', label='School', markerfacecolor='red', markersize=5),
    Line2D([0], [0], marker='o', color='w', label='NTA Center', markerfacecolor='green', markersize=5),
    Line2D([0], [0], color=cc.bjy[0], lw=2, label='Transit Line'),
    Line2D([0], [0], color=cc.fire[len(cc.fire)//2], lw=2, label='Walking Path')
]
ax.legend(handles=legend_config, loc='upper left')
plt.tight_layout()
plt.show()

# %%
# Load CCI Data
cci_edges = pickle.load('cci_result_graph_pkl')
cci_nodes = gpd_nodes.copy()
sch_df = pd.read_csv('processed_schools_2015.csv')

funding_mp = sch_df.set_index('LOCATION_CODE')['funding_per_student'].to_dict()
funding_mp = {'school_' + key: value for key, value in funding_mp.items()}

base_size = 10
scale = 0.05
color_map_config = {
    'school': '#ff4d4d',          
    'nta': '#2ecc71',             
    'subway_transit': '#3498db',  
    'bus_transit': '#f1c40f',    
    'walk': '#95a5a6'             
}

cci_graph = nx.Graph()

for idx, row in gdf_nodes.iterrows():
    G.add_node(idx, pos=(row.geometry.x, row.geometry.y), node_type=row['node_type'])
for u, v, weight in cci_edges:
    G.add_edge(u, v, weight=weight)
pos = nx.get_node_attributes(cci_graph, 'pos')

node_sizes = []
node_colors = []
for n, data in cci_graph.nodes(data=True):
    n_type = data.get('node_type', 'unknown')
    node_colors.append(color_map_config.get(ntype, '#ffffff'))

    funding = funding_mp.get(n, 0)
    if funding > 0: size = funding*scale
    else:   size = base_size
    node_sizes.append(size)
# %%
# Create direct CCI Graph
fig, ax = plt.subplots(figsize=(12, 12))
fig.patch.set_facecolor('#1a1a1a')
ax.set_facecolor('#1a1a1a')
boroughs.plot(ax=ax, color='#252525', edgecolor='#444444', linewidth=0.8, zorder=0)

## draw nodes and edges
nx.draw_networkx_nodes(
    G, pos, ax=ax,
    node_size=node_sizes,
    node_color=node_colors,
    alpha=0.6,
    zorder=3
)
weights = [G[u][v]['weight'] for u, v in G.edges()]
nx.draw_networkx_edges(
    G, pos, ax=ax,
    width=1.5,
    edgecolors='white',
    edge_color=weights,
    edge_cmap=plt.cm.plasma,
    alpha=0.5,
    zorder=2
)

## create legend
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='School (Size = Funding)',
           markerfacecolor=color_map_config['school'], markersize=10),
    Line2D([0], [0], marker='o', color='w', label='NTA Center',
           markerfacecolor=color_map_config['nta'], markersize=8),
    Line2D([0], [0], marker='o', color='w', label='Subway',
           markerfacecolor=color_map_config['subway_transit'], markersize=6),
    Line2D([0], [0], marker='o', color='w', label='Bus',
           markerfacecolor=color_map_config['bus_transit'], markersize=6)
]
ax.legend(handles=legend_elements, loc='upper left', frameon=False, 
          labelcolor='white', fontsize=10)

plt.title("NYC CCI Network", color='white')
plt.axis('off')
plt.tight_layout()
plt.show()