# join metapopulation persistence tables to patch centroids


import arcpy
import pandas as pd
import numpy as np


# Centroids
# Use the ones that are the ends of the connectivity lines
sg_centroids = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Hakai_chap1\scripts_runs_cluster\seagrass\seagrass_20200228_SS201701\seagrass_1\outputs\shp\patch_centroids.shp'

# metapopulation persistence table
dir = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\scripts\csv'
timesteps = 1750
metapop = f'metapop_pers_{timesteps}_'

# working gdb
gdb = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\metapop_pers.gdb'
arcpy.env.workspace = gdb


# make list of files that match metapop
files = os.listdir(dir)
fs = []
for file in files:
    if file.startswith(metapop):
        fs.append(file)

# if I want to exclude any, do it manually:
fs = fs[:]

# create df equal to first file in the list
df = pd.read_csv(os.path.join(dir, fs[0]))
df = df.drop(['Unnamed: 0'], axis=1)
# for each file, read in as df
for file in fs[1:]:
    df_metapop = pd.read_csv(os.path.join(dir, file))
    df_metapop = df_metapop.drop(['Unnamed: 0', 'popn'], axis=1)

    # check if there are any duplicates and remove
    col_exist = list(df.columns)
    col_new = list(df_metapop.columns)[1:] # first one will be uID
    matches = list(set(col_exist).intersection(col_new))
    if len(matches) > 0:
        for col in matches:
            df_metapop = df_metapop.drop([col], axis=1)

    # merge
    df = df.merge(df_metapop, on='uID')



# output to arc
x = np.array(np.rec.fromrecords(df.values))
names = df.dtypes.index.tolist()
x.dtype.names = tuple(names)
out_string = f'metapop_pers_{timesteps}'
arcpy.da.NumPyArrayToTable(x, os.path.join(gdb, out_string))


# join and copy
arcpy.env.qualifiedFieldNames = False
joined_table = arcpy.AddJoin_management(sg_centroids, 'uID', out_string, 'uID', 'KEEP_COMMON')
arcpy.CopyFeatures_management(joined_table, f'metapop_pers_centroids')
arcpy.DeleteField_management('metapop_pers_centroids', ['date_start', 'uID_1', 'OBJECTID'])
