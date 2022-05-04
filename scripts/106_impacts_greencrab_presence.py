# identify meadows with European green crab presence

# csv came from Brett Howard
# There were a few errors and some rows had to be deleted. See her email and the
# original csv for reference.

import arcpy
import os


root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
outgdb = 'greencrab.gdb'
gc_csv = os.path.join(root, 'green_crab/AllEGCPresenceRecords_DFO2020.csv')
sg_retrace = os.path.join(root, 'main_seagrass.gdb/sg_101_retrace')
arcpy.env.workspace = os.path.join(root, outgdb)

# import points
arcpy.MakeXYEventLayer_management(gc_csv, 'startLONG', 'startLAT', 'gc_lyr', 4326)
arcpy.CopyFeatures_management('gc_lyr', 'greencrab_01_points')
arcpy.Delete_management('gc_lyr')


# Buffer points by 1.5 km - this is based off a visual assessment of the few
# points in the salish sea and the nearby meadows that could be realisticaly
# reached from the meadow with the point. If points get added then I will need
# to redo this assessment.
# Don't rely on the 1.5 km buffer.
arcpy.Project_management('greencrab_01_points', 'greencrab_02_project', 3005)
arcpy.Buffer_analysis('greencrab_02_project', 'greencrab_03_buff', 1500)

# join to seagrass
arcpy.SpatialJoin_analysis(
    sg_retrace,
    'greencrab_03_buff',
    'sg_02_sjoin',
    'JOIN_ONE_TO_MANY',
    'KEEP_ALL',
    match_option='INTERSECT'
)
arcpy.AddField_management('sg_02_sjoin', 'gc_presence', 'SHORT')
with arcpy.da.UpdateCursor('sg_02_sjoin', ['ORIG_FID','gc_presence']) as cursor:
    for row in cursor:
        if row[0] == None:
            row[1] = 0
        else:
            row[1] = 1
        cursor.updateRow(row)
arcpy.Frequency_analysis('sg_02_sjoin', 'sg_03_freq', 'uID', 'gc_presence')

# my metric is simply that EGC is present. I'm not interested in the number of
# points
with arcpy.da.UpdateCursor('sg_03_freq', ['gc_presence']) as cursor:
    for row in cursor:
        if row[0] >= 1:
            row[0] = 1
        cursor.updateRow(row)

# sg_03_freq and attribute gc_presence is my result. It is simply a 1/0
# presence/absence