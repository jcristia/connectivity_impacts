# append the US meadows I am including to the seagrass feature class


import arcpy

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
out_gdb = os.path.join(root, r'spatial\main_seagrass.gdb')
seagrass_pts = os.path.join (root, 'spatial\connectivity.gdb\conn_metrics_pld21') # this is generated in the 002 script
arcpy.env.workspace = out_gdb


# get uIDs from both seagrass datasets
uIDs_all = [row[0] for row in arcpy.da.SearchCursor(seagrass_pts, ['uID'])]
uIDs_can = [row[0] for row in arcpy.da.SearchCursor('sg_4_join_norm', ['uID'])]
uIDs_usa = set(uIDs_all) - set(uIDs_can)

# select and append
sel = arcpy.SelectLayerByAttribute_management(
    'sg_1_og',
    'NEW_SELECTION',
    '"uID" IN {}'.format(str(tuple(uIDs_usa)))
)
arcpy.Merge_management(['sg_4_join_norm', sel], 'sg_5_canusa')

# add canada/usa field
arcpy.AddField_management('sg_5_canusa', 'canusa', 'TEXT')
with arcpy.da.UpdateCursor('sg_5_canusa', ['uID', 'canusa']) as cursor:
    for row in cursor:
        if row[0] in uIDs_usa:
            row[1] = 'usa'
        else:
            row[1] = 'can'
        cursor.updateRow(row)