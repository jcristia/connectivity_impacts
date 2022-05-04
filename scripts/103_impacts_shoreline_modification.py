# calculate percent of shoreline modification in 100m buffer on land

import arcpy
import os




root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
gdb = r'shoreline_modification.gdb'
arcpy.env.workspace = os.path.join(root, gdb)

sg_retrace = os.path.join(root, 'main_seagrass.gdb/sg_101_retrace')
land = os.path.join(root, 'main_seagrass.gdb/coastline_bc_ak_wa_or_cleaned_less10000')
roads = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\1Data_BASE\Roads\dgtl_road_atlas.gdb\dgtl_road_atlas.gdb\GBA\TRANSPORT_LINE'
mod_Katherine = os.path.join(root, 'shoreline_modification/Katherine/EelgrassContract_BannarMartin/shoreline_mod_TOEDIT_BannarMartin.kmz')


###################################
# programatically recreate buffers (I first created these manually in another
# geodatabase)
# shoreline_modification/shoreline_modification_ARCHIVED20210224.gdb
arcpy.CopyFeatures_management(sg_retrace, 'sg_101_retrace')
arcpy.Buffer_analysis('sg_101_retrace', 'sg_102_buff100m', 100)
arcpy.Clip_analysis('sg_102_buff100m', land, 'sg_103_clipcoast')

# recreate roads
arcpy.Clip_analysis(roads, 'sg_103_clipcoast', 'roads_01_clip')
# Buffer based on land width - 4m per lane
arcpy.AddField_management('roads_01_clip', 'lane_width', 'SHORT')
with arcpy.da.UpdateCursor('roads_01_clip', ['TOTAL_NUMBER_OF_LANES', 'lane_width']) as cursor:
    for row in cursor:
        row[1] = row[0] * 2
        cursor.updateRow(row)
arcpy.Buffer_analysis('roads_01_clip', 'roads_02_buff8m', 'lane_width', 'FULL')
arcpy.Clip_analysis('roads_02_buff8m', 'sg_103_clipcoast', 'roads_03_clip')
arcpy.Dissolve_management('roads_03_clip', 'roads_04_dissolve', multi_part='SINGLE_PART')

# convert to KMZ
# I'll keep this as a manual operation. I gave these to Katherine as inputs.
# Impacts\spatial\shoreline_modification\Katherine\for_Katherine

# Katherine then used these inputs and digitized shoreline modification within
# the 100m buffers.
# The roads were created so that she would have less to digitize. Therefore, I
# need to combine the road buffers with what she digitizes.



######################################
# kmz to fc
arcpy.KMLToLayer_conversion(
    mod_Katherine,
    os.path.join(root, 'shoreline_modification'),
    'shmod_transfer_TEMP',
    'NO_GROUNDOVERLAY'    
)
polys = os.path.join(root, 'shoreline_modification', 'shmod_transfer_TEMP.gdb', 'Placemarks/Polygons')
arcpy.Project_management(polys, 'shmod_01_Katherine', 3005)
arcpy.Delete_management(os.path.join(root, 'shoreline_modification/shmod_transfer_TEMP.gdb'))
arcpy.Delete_management(os.path.join(root, 'shoreline_modification/shmod_transfer_TEMP.lyrx'))


#######################################
# clean up attributes
arcpy.env.outputZFlag = 'Disabled'
arcpy.CopyFeatures_management('shmod_01_Katherine', 'shmod_02_cleanattrs')
arcpy.AddFields_management(
    'shmod_02_cleanattrs',
    [
        ['orig_id', 'TEXT', 'orig_id', 50],
        ['desc_1', 'TEXT', 'desc_1', 255],
        ['desc_2', 'TEXT', 'desc_2', 255],
        ['desc_3', 'TEXT', 'desc_3', 255],
    ]
)
fields = ['Name', 'PopupInfo', 'orig_id', 'desc_1', 'desc_2', 'desc_3']
with arcpy.da.UpdateCursor('shmod_02_cleanattrs', fields) as cursor:
    for row in cursor:
        row[2] = row[0]
        descriptions = row[1].split(';')
        row[3]=descriptions[0]
        if len(descriptions) > 1:
            row[4]=descriptions[1]
            if len(descriptions) == 3:
                row[5]=descriptions[2]
        cursor.updateRow(row)
arcpy.DeleteField_management('shmod_02_cleanattrs', ['Name', 'FolderPath', 'SymbolID', 'AltMode', 'Base', 'Clamped', 'Extruded', 'Snippet', 'PopupInfo'])


########################################
# clean up spatially

# spatial tools like Erase are not working on shmod because there are a lot of
# geometry errors (self intersections, repeat points, etc) Clean these up first.
arcpy.CopyFeatures_management('shmod_02_cleanattrs', 'shmod_03_repairGeom')
arcpy.CheckGeometry_management('shmod_03_repairGeom', 'shmod_03b_checkGeom')
arcpy.RepairGeometry_management('shmod_03_repairGeom')
arcpy.CheckGeometry_management('shmod_03_repairGeom', 'shmod_03c_checkGeom') # there shouldn't be any row now

# erase with roads
arcpy.Erase_analysis('shmod_03_repairGeom', 'roads_04_dissolve', 'shmod_04_eraseRoads')
# merge with roads
arcpy.Merge_management(['shmod_04_eraseRoads', 'roads_04_dissolve'], 'shmod_05_merge')
# clip to original 100m buffers
arcpy.Clip_analysis('shmod_05_merge', 'sg_103_clipcoast', 'shmod_06_clip')

# attributes
arcpy.DeleteField_management('shmod_06_clip', ['GEOMETRY_Length', 'GEOMETRY_Area'])
with arcpy.da.UpdateCursor('shmod_06_clip', ['desc_1']) as cursor:
    for row in cursor:
        if row[0] == None:
            row[0] = 'road'
        cursor.updateRow(row)


#########################################
# associate with seagrass and calculate area and % modified

# it looks like there might be a few places where if buffers overlap and there
# is also a shoreline mod that overlaps, then a spatial join will be
# picking up more area than it should. These look minor for the most part, but
# there a few places where it would be significant. See uid 280 and 291.
# So I need to split these features up by the buffer feature class.
# It looks like the most straightforward way is Identity.
arcpy.Identity_analysis('shmod_06_clip', 'sg_103_clipcoast', 'shmod_07_identity', 'ONLY_FID')
# bit it creates identical features where there is overlap
arcpy.DeleteIdentical_management('shmod_07_identity', ['Shape'])
arcpy.DeleteField_management('shmod_07_identity', ['FID_shmod_06_clip', 'FID_sg_103_clipcoast'])

# note the "contains". Can't do intersect here.
arcpy.SpatialJoin_analysis(
    'sg_103_clipcoast',
    'shmod_07_identity',
    'sg_104_sjoin',
    'JOIN_ONE_TO_MANY',
    'KEEP_ALL',
    match_option='CONTAINS'
)

arcpy.Frequency_analysis('sg_104_sjoin', 'sg_105_freqArea', ['uID'], ['Shape_Area_1']) # this is the area from the shmods
arcpy.env.qualifiedFieldNames = False # prevent table being part of field names in 
joined_table = arcpy.AddJoin_management('sg_103_clipcoast', 'uID', 'sg_105_freqArea', 'uID')
arcpy.CopyFeatures_management(joined_table, 'sg_106_AREA')

# clean up attributes
arcpy.AddFields_management(
    'sg_106_AREA',
    [
        ['shmod_area', 'DOUBLE', 'shmod_area'],
        ['shmod_percent', 'DOUBLE', 'shmod_percent']
    ]
)
with arcpy.da.UpdateCursor('sg_106_AREA', ['Shape_Area_1', 'Shape_Area', 'shmod_area', 'shmod_percent']) as cursor:
    for row in cursor:
        if row[0] ==  None:
            row[2]=0.0
            row[3]=0.0
        else:
            row[2]=row[0]
            row[3]=row[0]/row[1] * 100
        cursor.updateRow(row)
arcpy.DeleteField_management('sg_106_AREA', ['area', 'traced', 'BUFF_DIST', 'ORIG_FID', 'OBJECTID_1', 'uID_1', 'Shape_Area_1'])

# sg_106_AREA is my primary output. It contains:
# shmod_area: the area of all the shoreline modification in the 100m buffer
# shmod_percent: the percentage of the buffer the is modified