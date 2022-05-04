# Calculate connectivity metrics for the time-averaged connectivity lines
# (I may not actually this in the chapter)

import networkx as nx
import arcpy
import numpy as np
import pandas as pd
import os



root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
gdb = os.path.join(root, 'spatial/connectivity.gdb')
conn_lines = 'conn_avg_pld21_noUS'
centroids = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Hakai_chap1\scripts_runs_cluster\seagrass\seagrass_20200228_SS201701\shp_merged\patch_centroids.shp'
arcpy.env.workspace = gdb

# copy centroids to new gdb
out_pts = 'conn_metrics_pld21'
arcpy.CopyFeatures_management(centroids, out_pts)

# to dataframe
arr = arcpy.da.FeatureClassToNumPyArray(conn_lines, ('from_id', 'to_id', 'prob_avg'))
df = pd.DataFrame(arr)

# remove self connections
df = df[df.from_id != df.to_id]

# calc metrics
G = nx.from_pandas_edgelist(df, source='from_id', target='to_id', edge_attr='prob_avg', create_using=nx.DiGraph)

bt = nx.betweenness_centrality(G, k=None, normalized=True, weight='prob_avg', endpoints=False, seed=None)
dca = nx.degree_centrality(G)
dci = nx.in_degree_centrality(G)
dco = nx.out_degree_centrality(G)

# add metrics as node attributes
nx.set_node_attributes(G, bt, 'bt')
nx.set_node_attributes(G, dca, "dca")
nx.set_node_attributes(G, dci, "dci")
nx.set_node_attributes(G, dco, "dco")


df_att = pd.DataFrame({
    'node':list(G.nodes), 
    'bt':bt.values(),
    'dca':dca.values(),
    'dci':dci.values(),
    'dco':dco.values()
        })


metrics = ['bt', 'dca', 'dci', 'dco']
for field in metrics:
    arcpy.AddField_management(out_pts, field, 'DOUBLE')

fields = metrics[:]  # need to be careful how I copy lists
fields.append('uID')        
with arcpy.da.UpdateCursor(out_pts, fields) as cursor:
    for row in cursor:
        if row[-1] not in df_att.node.values:
            cursor.deleteRow()
            continue # I should only need this for testing
        dftemp = df_att[df_att.node==row[-1]]
        for i,m in enumerate(metrics):
            row[i] = dftemp[m].values[0]
        cursor.updateRow(row)

