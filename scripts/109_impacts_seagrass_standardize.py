# sum the normalized impacts
# assign the median value to the US meadows
# standardize impacts to different ranges
# These ranges will apply a different scale of naturalness to the meadows that
# when they are used to divide the connection probabilities, I'll get different
# scales of severity of impacts.

import arcpy
import pandas as pd
import numpy as np

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
out_gdb = os.path.join(root, r'spatial\main_seagrass.gdb')
arcpy.env.workspace = out_gdb
sg = 'sg_5_canusa'


# read in as pandas df
field_names = [i.name for i in arcpy.ListFields(sg) if i.type != 'OID']
cursor = arcpy.da.SearchCursor(sg, field_names)
df_imp = pd.DataFrame(data=[row for row in cursor], columns=field_names)
df_imp = df_imp.drop(['area', 'Shape', 'Shape_Length', 'Shape_Area'] , axis=1)

# add up impacts (which are individuallly normalized) 
# and normalize between 0 and 1 again
imp_fields = ['popn', 'ow_perc', 'smodperc', 'agricult', 'cutblock', 'gcrab']
df_imp['total'] = df_imp[imp_fields].sum(axis=1)
# get mean and apply to usa meadows
# rationale:
# I considered applying no value, an informed value, a random value, or the median.
# I think the median makes sense and requires the least explanation. It's a big
# assumption but it doesn't have a chain of assumptions associated with it.
median = df_imp.total[df_imp.canusa=='can'].mean()
df_imp.total[df_imp.canusa=='usa'] = median
min = df_imp.total.min()
max = df_imp.total.max()
df_imp['total_norm_0_1'] = (df_imp.total - min) / (max - min)
df_imp = df_imp.drop(
    ['popn', 'ow_perc', 'smodperc', 'agricult', 'cutblock', 'gcrab', 'total', 'canusa'],
    axis=1
)

# create two new columns:
# 1-2 and 1-10
# standardize scores between these ranges
# rationale:
# I don't want to reduce a meadows connections to 0 (if highest impact meadows connections get reduced to zero)
# If I divide by 2 then I half the connection probability.
# If I divide by 10 then I reduce by a level of magnitude.
# Also keep in mind: I will already have a 3rd level of not applying any impacts.
start = 1
end = 2
width = end - start
# res = (arr - arr.min())/(arr.max() - arr.min()) * width + start
# my values are already scaled between 0 and 1, so it just results in dividng by 1
df_imp['total_norm_1_2'] = df_imp.total_norm_0_1 * width + start
start = 1
end = 10
width = end - start
df_imp['total_norm_1_10'] = df_imp.total_norm_0_1 * width + start


# create table and join back to sg fc
x = np.array(np.rec.fromrecords(df_imp.values))
names = df_imp.dtypes.index.tolist()
x.dtype.names = tuple(names)
arcpy.da.NumPyArrayToTable(x, os.path.join(arcpy.env.workspace, f'impacts_total_norm'))

arcpy.env.qualifiedFieldNames = False
jt = arcpy.AddJoin_management(sg, 'uID', 'impacts_total_norm', 'uID')
arcpy.CopyFeatures_management(jt, 'sg_6_imptotal')
arcpy.Delete_management('impacts_total_norm')
arcpy.DeleteField_management('sg_6_imptotal', ['OBJECTID_1', 'uID_1'])

