# calculate percent of watershed that is cutblocks and associate to seagrass
# meadows

import arcpy
import os

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
outgdb = 'cutblocks_watershed.gdb'
sg_ext = os.path.join(root, 'population.gdb/sg_103_extend') # sg polys already buffered and extended to overlap with watersheds
watersheds_overlapping = os.path.join(root, 'population.gdb/watersheds_01_intersect') # watersheds already selected as overlapping with seagrass
cutblocks = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\1Data_BASE\BASE\BASE_forestry.gdb\Cut_Block_all_BC'
shmod = os.path.join(root, 'shoreline_modification.gdb/shmod_07_identity')
arcpy.env.workspace = os.path.join(root, outgdb)



# select cutblocks from the last 15 years (this was suggested by Nick)
# Free-to-grow status is usually reached in 11-20 years
sql_where = 'Harvest_Year >= 2006'
cb_sel = arcpy.SelectLayerByAttribute_management(cutblocks, where_clause=sql_where)
arcpy.CopyFeatures_management(cb_sel, 'cutblocks_01_selYear')

# intersect with watersheds
arcpy.Intersect_analysis(
    ['cutblocks_01_selYear', watersheds_overlapping],
    'cutblocks_02_intersect')

# erase where polys already exist in the shoreline modification dataset
# These datasets are somewhat capturing the same impact (runoff and sedimentation),
# so I don't want them overlapping.
# I did an intersect on these datasets and it is only 17 small pieces, so it
# doesn't make that much of a difference, but I will do it anyways.
arcpy.Erase_analysis('cutblocks_02_intersect', shmod, 'cutblocks_03_erase')


# 
arcpy.Frequency_analysis('cutblocks_03_erase', 'cutblocks_04_freq', 'jc_ID', 'Shape_Area')
arcpy.AddField_management('cutblocks_04_freq', 'area_cutblocks', 'FLOAT')
with arcpy.da.UpdateCursor('cutblocks_04_freq', ['Shape_Area', 'area_cutblocks']) as cursor:
    for row in cursor:
        row[1] = row[0]
        cursor.updateRow(row)

arcpy.env.qualifiedFieldNames = False
w_join = arcpy.AddJoin_management(watersheds_overlapping, 'jc_ID', 'cutblocks_04_freq', 'jc_ID')
arcpy.CopyFeatures_management(w_join, 'watersheds_02_cutblocks')

arcpy.AddField_management('watersheds_02_cutblocks', 'area_total_watershed', 'FLOAT')
with arcpy.da.UpdateCursor('watersheds_02_cutblocks', ['area_total_watershed', 'SHAPE_Area']) as cursor:
    for row in cursor:
        row[0]=row[1]
        cursor.updateRow(row)

# spatial join, watersheds to seagrass
arcpy.SpatialJoin_analysis(
    sg_ext,
    'watersheds_02_cutblocks',
    'sg_104_sjoin',
    'JOIN_ONE_TO_MANY',
    'KEEP_ALL',
    match_option='INTERSECT'
)

arcpy.Frequency_analysis('sg_104_sjoin', 'sg_105_freq', ['uID'], ['area_cutblocks', 'area_total_watershed'])
arcpy.AddField_management('sg_105_freq', 'percent_cutblocks', 'FLOAT')
with arcpy.da.UpdateCursor('sg_105_freq', ['area_cutblocks', 'area_total_watershed', 'percent_cutblocks']) as cursor:
    for row in cursor:
        if row[0] == None:
            areacrop=0
        else:
            areacrop=row[0]
        row[2] = (areacrop/row[1]) * 100.0
        cursor.updateRow(row)

# sg_105_freq, attribute percent_cutblocks is my final result