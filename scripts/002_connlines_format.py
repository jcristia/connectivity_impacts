
# output to feature class
# remove US meadows

# I'm not filtering weak connections. I can just leave them in and they won't
# have a lot of influence on the metapopulation model anyways. I doublechecked
# the model and since it assigns particles by probability (which includes
# assigning them to no meadow), then the model will only very rarely assign
# particles to these connections.
# This makes my life easier by not having to specify a threshold, which will be
# hard to justify biologically.


import arcpy
import pandas as pd
import networkx as nx
import numpy as np

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
out_gdb = os.path.join(root, 'spatial/connectivity.gdb')
arcpy.env.workspace = out_gdb
shp = os.path.join(root, 'conn_avg_pld21.shp')
seagrass = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Hakai_chap1\scripts_runs_localstage\seagrass\seagrass\seagrass_20200228_SS\seagrass_prep\seagrass.gdb\seagrass_all_19FINAL'


# output to feature class
fc = 'conn_avg_pld21'
if not arcpy.Exists(fc):
    arcpy.CopyFeatures_management(shp, fc)
    arcpy.Delete_management(shp)

# remove US meadow connections that are not part of a strongly connected 
# component that contains a Canadian meadow. There's no point in keeping US 
# meadows that are sources if they are not part of a loop.
# This is not perfect though, for instance a US meadow that is just a source
# to a Canadian meadow might be part of a loop in the states and the Canadian
# meadow could be just a sink to that strongly connected component.
# There may also be complex loops within the states that link back to Canada.
# HOWEVER, given the lack of impact data for US meadows, I think I can limit 
# what I include. I just need to show that I considered it.
# I could write something like: "We only included meadows in the states if they
# were part of loops including Canadian meadows. While this may exclude complex
# linkages in the states that eventually source a Canadian meadow, we were
# satisfied with this assumption given the lack of impact data"

# I made a selection poly for the US meadows since I never identified which uIDs
# are associated with US meadows.
spat_select = arcpy.SelectLayerByLocation_management(
    seagrass,
    'COMPLETELY_WITHIN',
    'select_US_poly')
cursor = arcpy.da.SearchCursor(spat_select, ['uID'])
us_uids = [row[0] for row in cursor]


# get uIDs of US meadows that are part of a strongly connected component that
# contains at least 1 Canadian meadow
# read in conns as pandas df
field_names = [i.name for i in arcpy.ListFields(fc)]
cursor = arcpy.da.SearchCursor(fc, field_names)
conns_df = pd.DataFrame(data=[row for row in cursor], columns=field_names)
conns_df = conns_df.drop(['OBJECTID', 'Shape', 'freq', 'totalori', 'totquant', 'Shape_Length'], 1)

# create directed graph
G = nx.from_pandas_edgelist(
    conns_df, 
    source='from_id', 
    target='to_id', 
    edge_attr='prob_avg', 
    create_using=nx.DiGraph)
# identify strongly connected components
comps_strong = nx.strongly_connected_components(G)

# add field, give all rows -1 to start
conns_df[f'component_strong'] = -1
# each component is listed as SET type, which are unordered, unchangeable and don't allow duplicates
i = 1
for comp in comps_strong:
    c = list(comp)
    if len(c)==1:
        continue
    # add a component id to connection dataframe
    conns_df[f'component_strong'] = np.where(
        ((conns_df.from_id.isin(c)) & (conns_df.to_id.isin(c))),
        i,  # change it to i
        conns_df[f'component_strong'] # or keep it the same
    )
    i+=1


arcpy.CopyFeatures_management(fc, 'conn_avg_pld21_noUS')


#get list of US meadows that are sources to Canada meadows
us_sources = []
with arcpy.da.SearchCursor('conn_avg_pld21_noUS', ['from_id', 'to_id']) as cursor:
    for row in cursor:
        if row[0] in us_uids and row[1] not in us_uids:
            if row[0] not in us_sources:
                us_sources.append(row[0])

# remove connections
# There was probably a more elegant way to do this in fewer criteria.
with arcpy.da.UpdateCursor('conn_avg_pld21_noUS', ['from_id', 'to_id']) as cursor:
    for row in cursor:

        # remove if both meadows in the us and the source meadow is not also a source to Canada
        if (row[0] in us_uids and row[1] in us_uids) and (row[0] not in us_sources):
            cursor.deleteRow()
            continue

        # remove if from or to is in the us and it is not part of a strongly connected component
        comp_id = conns_df.component_strong[(conns_df.from_id == row[0]) & (conns_df.to_id==row[1])]
        if (row[0] in us_uids or row[1] in us_uids) and comp_id.item==-1:
            cursor.deleteRow()
            continue

        # remove if it is a connection to the states and it is not a US source
        if row[1] in us_uids and row[1] not in us_sources:
            cursor.deleteRow()


