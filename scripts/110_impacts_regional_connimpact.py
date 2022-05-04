# calculate regionally distributed impacts
# This is based on Jonsson et al 2020
# Essentially, this is source-sink dynamics and the transfer of impacts in the 
# form of lost recruits i.e. reduced dispersal from sites with high impacts and 
# reduced survival of recruits coming into high impacted sites.

# 2 sections:
# (1) calculate the source/sink total impact potential for each meadow (this 
# isn't really used in the analysis)
# (2) calculate the reduction in individual dispersal probabilities based on 
# local origin impacts (this is used in the metapopulation model)

import arcpy
import os
import pandas as pd
import numpy as np


root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
outgdb = 'regional_connimpact.gdb'
conn_lines = os.path.join(root, 'connectivity.gdb/conn_avg_pld21_noUS')
sg_impacts = os.path.join(root, 'main_seagrass.gdb/sg_6_imptotal')
arcpy.env.workspace = os.path.join(root, outgdb)
naturalness_levels = ['total_norm_1_2', 'total_norm_1_10']


# read in connectivity lines as dataframe
field_names = [i.name for i in arcpy.ListFields(conn_lines) if i.type != 'OID']
cursor = arcpy.da.SearchCursor(conn_lines, field_names)
df_conn = pd.DataFrame(data=[row for row in cursor], columns=field_names)
df_conn = df_conn.drop(['Shape', 'freq', 'totalori', 'totquant', 'Shape_Length'], axis=1)


# read in impacts as df
field_names = [i.name for i in arcpy.ListFields(sg_impacts) if i.type != 'OID']
cursor = arcpy.da.SearchCursor(sg_impacts, field_names)
df_imp = pd.DataFrame(data=[row for row in cursor], columns=field_names)
df_imp = df_imp[['uID', 'total_norm_0_1', 'total_norm_1_2', 'total_norm_1_10']]



################################################################
# For each meadow, calculate source/sink distributed impact
# This will be a MEADOW-level impact

# Remove self connections just for looking at point-level potential for the
# transfer of impacts. However, in the metapop model, I will want to consider
# self connections so that I know how recruits might have trouble returning
# home.
df_conn_noself = df_conn[df_conn.from_id != df_conn.to_id]

uIDs = df_imp.uID.values
s_dict = {
    'uID':[],
    'regsink':[],
    'regsource':[]
    }
for uid in uIDs:

    # get in/out connections
    in_conns = df_conn_noself[df_conn_noself.to_id == uid]
    ot_conns = df_conn_noself[df_conn_noself.from_id == uid]

    # get impacts for the uIDs coming in
    imps_in = df_imp[df_imp.uID.isin(in_conns.from_id)]
    # get impact for just the from meadow
    imp_ot = df_imp['total_norm_0_1'][df_imp.uID == uid]

    # multiply impact by connectivity probability for incoming connections
    imps_mult_in = in_conns.merge(imps_in, left_on='from_id', right_on='uID')
    imps_mult_in['impconn'] = imps_mult_in.prob_avg * imps_mult_in['total_norm_0_1']
    # multiply home impact by conn prob for outgoing connections
    imps_mult_out = ot_conns
    imps_mult_out['impconn'] = ot_conns.prob_avg * imp_ot.values[0]
    # sum
    sink = imps_mult_in.impconn.sum()
    source = imps_mult_out.impconn.sum()

    # add to dictionary
    s_dict['uID'].append(uid)
    s_dict['regsink'].append(sink)
    s_dict['regsource'].append(source)


# turn dict to dataframe
df_all = pd.DataFrame.from_dict(s_dict)

# export to arc table and join
x = np.array(np.rec.fromrecords(df_all.values))
names = df_all.dtypes.index.tolist()
x.dtype.names = tuple(names)
arcpy.da.NumPyArrayToTable(x, os.path.join(arcpy.env.workspace, f'imp_sourcesink_tbl'))

arcpy.env.qualifiedFieldNames = False
jt = arcpy.AddJoin_management(sg_impacts, 'uID', 'imp_sourcesink_tbl', 'uID')
arcpy.CopyFeatures_management(jt, 'sg_7_imptotal_sourcesink')
arcpy.DeleteField_management('sg_7_imptotal_sourcesink', ['OBJECTID_1', 'uID_1'])
arcpy.CopyFeatures_management('sg_7_imptotal_sourcesink', os.path.join(root, 'main_seagrass.gdb/sg_7_imptotal_sourcesink'))

# make centroids
arcpy.FeatureToPoint_management('sg_7_imptotal_sourcesink', 'sg_7_imptotal_sourcesink_pts', 'INSIDE')
arcpy.CopyFeatures_management('sg_7_imptotal_sourcesink_pts', os.path.join(root, 'main_seagrass.gdb/sg_7_imptotal_sourcesink_pts'))


###############################################################
# For the metapopulation model
# rescale the connectivity lines for the 3 (well, 2) naturalness levels (just
# copy over the original values of the lines)
# This is a LINE MEADOW to MEADOW level impact.

# copy connections
arcpy.CopyFeatures_management(conn_lines, 'conn_lines_temp')

# add fields for the 3 new fields
arcpy.AddField_management('conn_lines_temp', 'probavg_BASE', 'DOUBLE')
arcpy.AddField_management('conn_lines_temp', 'probavg_1_2', 'DOUBLE')
arcpy.AddField_management('conn_lines_temp', 'probavg_1_10', 'DOUBLE')

# calculate 1st one as is
arcpy.CalculateField_management('conn_lines_temp', 'probavg_BASE', '!prob_avg!')

# join impacts table to it based on from_id and uID
arcpy.env.qualifiedFieldNames = False
jt = arcpy.AddJoin_management('conn_lines_temp', 'from_id', 'sg_7_imptotal_sourcesink_pts', 'uID')
arcpy.CopyFeatures_management(jt, 'conn_lines_impacts')
arcpy.Delete_management('conn_lines_temp')
fields = ['OBJECTID_1', 'uID', 'area', 'popn', 'ow_perc', 'smodperc', 'agricult', 'cutblock', 'gcrab', 'canusa', 'ORIG_FID', 'regsink', 'regsource']
arcpy.DeleteField_management('conn_lines_impacts', fields)

# calculate the other two fields by dividing the conn prob by the impact
fields = [
    'probavg_BASE',
    'probavg_1_2',
    'probavg_1_10',
    'total_norm_1_2',
    'total_norm_1_10']
with arcpy.da.UpdateCursor('conn_lines_impacts', fields) as cursor:
    for row in cursor:
        row[1] = row[0] / row[3]
        row[2] = row[0] / row[4]
        cursor.updateRow(row)

