
# spatial analysis of metapopulation persistence data


import arcpy
import networkx as nx
import pandas as pd
import numpy as np


gdb = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\metapop_pers.gdb'
metapop_pers = 'metapop_pers_centroids'
connections = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\regional_connimpact.gdb\conn_lines_impacts'

arcpy.env.workspace = gdb

naturalness_levels = ['probavg_BASE', 'probavg_1_2', 'probavg_1_10', 'probavg_1_100']
mort_rates = [0.15] # mortality rate of the settled population at each time step
larvae_dispersing_per_adult = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.50, 0.55, 0.6] # viable larvae produce that disperse



# for each persistence column...
# get all outgoing connections for those persistence nodes
# this will get me all relevant connections. If a node is persistent then its
# outgoing connections are persistent, even if the node it connects to is not.

for nlevel in naturalness_levels:
    for disp_prop in larvae_dispersing_per_adult:
        for mort in mort_rates:

            str_prop = str(disp_prop).replace('.', '')
            str_mort = str(mort).split('.')[1]
            field = f'{nlevel}_prop{str_prop}_m{str_mort}'

            print('Processing ' + field)

            uIDs = []

            # get uIDs of those that are persistent
            with arcpy.da.SearchCursor(metapop_pers, ['uID', field]) as cursor:
                for row in cursor:
                    if row[1] == 1:
                        uIDs.append(row[0])

            if len(uIDs)==0:
                continue
            if len(uIDs)==1: # if its length 1 then the selection below gets screwed up. Just duplicate the meadow so that it can create a tuple. It will still only select one row.
                uIDs.append(uIDs[0])

            # get outgoing connections for those uIDs
            arcpy.MakeFeatureLayer_management(connections, 'temp_lyr')
            arcpy.SelectLayerByAttribute_management(
                'temp_lyr', 
                'NEW_SELECTION', 
                #'"from_id" <> "to_id" and "from_id" IN {}'.format(str(tuple(uIDs)))  # if I want to exclude self-conns, but I think I want to see these actually, and for the visuals I can remove them at the time of mapping
                '"from_id" IN {}'.format(str(tuple(uIDs)))
                )

            fc = f'conn_{nlevel}_prop{str_prop}_m{str_mort}'
            arcpy.CopyFeatures_management('temp_lyr', fc)
            arcpy.Delete_management('temp_lyr')

            # add field for conn_id
            arcpy.AddField_management(fc, 'conn_uid', 'SHORT')
            with arcpy.da.UpdateCursor(fc, ['OBJECTID', 'conn_uid']) as cursor:
                for row in cursor:
                    row[1] = row[0]
                    cursor.updateRow(row)


# Then from those connections get the components, both normal and strongly
# connected so I can color code them.
for nlevel in naturalness_levels:
    for disp_prop in larvae_dispersing_per_adult:
        for mort in mort_rates:

            str_prop = str(disp_prop).replace('.', '')
            str_mort = str(mort).split('.')[1]
            fc = f'conn_{nlevel}_prop{str_prop}_m{str_mort}'

            if not arcpy.Exists(fc):
                continue

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
                edge_attr=nlevel, 
                create_using=nx.DiGraph)

            # create undirected graph
            H = G.to_undirected()

            # identify strongly connected components
            comps_strong = nx.strongly_connected_components(G)
            comps = nx.connected_components(H)

            # add field, give all rows -1 to start
            conns_df[f'component_strong'] = -1
            conns_df[f'component'] = -1

            # each component is listed as SET type, which are unordered, unchangeable and don't allow duplicates
            i = 1
            for comp in comps:
                c = list(comp)
                if len(c)==1:
                    continue
                # add a component id to connection dataframe
                conns_df[f'component'] = np.where(
                    ((conns_df.from_id.isin(c)) & (conns_df.to_id.isin(c))),
                    i,  # change it to i
                    conns_df[f'component'] # or keep it the same
                )
                i+=1
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

            # output to gdb table
            df_out = conns_df.drop(['from_id', 'to_id', 'prob_avg', 'probavg_BASE', 'probavg_1_2', 'probavg_1_10', 'total_norm_0_1', 'total_norm_1_2', 'total_norm_1_10'],1)
            x = np.array(np.rec.fromrecords(df_out.values))
            names = df_out.dtypes.index.tolist()
            x.dtype.names = tuple(names)
            arcpy.da.NumPyArrayToTable(x, os.path.join(gdb, 'temp_tbl'))

            # join to connections fc
            arcpy.env.qualifiedFieldNames = False
            fc = f'conn_{nlevel}_prop{str_prop}_m{str_mort}'
            conn_join = arcpy.AddJoin_management(fc, 'conn_uid', 'temp_tbl', 'conn_uid')
            arcpy.CopyFeatures_management(conn_join, fc+'_comps')
            arcpy.DeleteField_management(fc+'_comps', ['OBJECTID_1', 'conn_uid_1'])

            # delete temp fc and table
            arcpy.Delete_management(fc)
            arcpy.Delete_management('temp_tbl')

