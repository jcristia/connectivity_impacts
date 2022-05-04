# assign population in a watershed to each seagrass meadow


import arcpy
from arcpy.sa import *
import os

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
outgdb = 'population.gdb'
watersheds = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\1Data_BASE\BASE\BASE_hydrology.gdb\WHSE_BASEMAPPING_FWA_WATERSHEDS_POLY'
sg = 'main_seagrass.gdb/sg_101_retrace'
coastline = 'main_seagrass.gdb/coastline_bc_ak_wa_or_cleaned_less10000'
pop_rast = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\1Data_BASE\Population\gpw-v4-population-count-rev11_2020_30_sec_tif\gpw_v4_population_count_rev11_2020_30_sec.tif'
arcpy.env.workspace = os.path.join(root, outgdb)

# copy seagrass to population gdb
# these are the polys that were retraced to align with the coastline
sg_retraced = os.path.join(root, sg)
arcpy.CopyFeatures_management(sg_retraced, 'sg_101_retraced')

# buffer by 100m to remove any slivers and to create overlap with watershed
# so that I can do a spatial select. It will also create overlap for meadows
# that are more offshore.
arcpy.Buffer_analysis('sg_101_retraced', 'sg_102_buff100', 100)

# Copy
# and then do a spatial select with watersheds to see which meadows are not
# overlapping. Then, !!!MANUALLY!!! extend these to the coast. Create a bit of overlap
# for a spatial select.
arcpy.CopyFeatures_management('sg_102_buff100', 'sg_103_extend')
# there were 6 features that overlapped, but I also edited additional features
# near Nanaimo (uid 569, 568, 601, 603, 605). There overlap with parts of watersheds was weird.
# I want them all to overlap the same watersheds.

# Spatially select the watersheds that intersect with the seagrass meadows
arcpy.MultipartToSinglepart_management(watersheds, 'watersheds_multisingle')
watershed_sel = arcpy.SelectLayerByLocation_management('watersheds_multisingle', 'INTERSECT', 'sg_103_extend')
arcpy.CopyFeatures_management(watershed_sel, 'watersheds_01_intersect')
arcpy.Delete_management('watersheds_multisingle')
# there isn't a clear unique ID in the dataset. Add one.
arcpy.AddField_management('watersheds_01_intersect', 'jc_ID', 'SHORT')
with arcpy.da.UpdateCursor('watersheds_01_intersect', ['OBJECTID_1', 'jc_ID']) as cursor: # note that objectdid is actually 'OBJECTID_1'
    for row in cursor:
        row[1] = row[0]
        cursor.updateRow(row)

# clip raster to poly (this was created manually) 
arcpy.CopyRaster_management(pop_rast, 'population_01')
outRast = ExtractByMask('population_01', 'clip_rast_poly')
outRast.save('population_02_clip')

# https://support.esri.com/en/technical-article/000012696
arcpy.RasterToPoint_conversion('population_02_clip', 'population_03_pts')
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
arcpy.CreateFishnet_management(
    'population_04_fishnet',
    '-126.308333333333 48.1999999999999',
    '-126.308333333333 58.1999999999999',
    None, None,
    290, 478,
    '-122.325 50.6166666666666',
    'LABELS',
    None,
    'POLYGON')
arcpy.FeatureToPolygon_management(
    'population_04_fishnet',
    'population_05_values',
    label_features='population_03_pts')

arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3005)


# clip to coastline
# This is important to do before I do an intersect and recalculate population
# based on the new area. For cells that overlap the coastline and have a lot of
# water in them, if I readjust based on this new area the I am reducing the pop
# by too much. Think of it as a big 1km cell that is over a very small island
# that has just a few people. If I clip to that island and then reduce the pop
# by that new area then I will be getting a very small fraction of people present.
arcpy.Clip_analysis(
    'population_05_values',
    os.path.join(root, coastline),
    'population_06_clip')
arcpy.MultipartToSinglepart_management('population_06_clip', 'population_07_multising')

# project so that I can get areas in meters
arcpy.Project_management('population_07_multising', 'population_08_project', 3005)
# add area field so that this carries over to the next step
arcpy.AddField_management('population_08_project', 'area_orig', 'DOUBLE')
with arcpy.da.UpdateCursor('population_08_project', ['Shape_Area', 'area_orig']) as cursor:
    for row in cursor:
        row[1] = row[0]
        cursor.updateRow(row)

# intersect with watersheds
arcpy.Intersect_analysis(
    ['population_08_project', 'watersheds_01_intersect'], 
    'population_09_intersect')

# calc population per piece
arcpy.AddField_management('population_09_intersect', 'pop_adjusted', 'DOUBLE')
with arcpy.da.UpdateCursor('population_09_intersect', ['grid_code', 'area_orig', 'Shape_Area', 'pop_adjusted']) as cursor:
    for row in cursor:
        row[3] = row[0] * (row[2]/row[1])
        cursor.updateRow(row)

# This will assume that population is spread evenly throughout a raster cell.
# This is not perfect for getting absolute amounts, but it should work
# relatively betewen meadows.

# dissolve by jc_ID and add pop_adjusted
arcpy.Dissolve_management(
    'population_09_intersect', 
    'population_10_dissolve',
    'jc_ID',
    [['pop_adjusted', 'SUM']]
    )

# spatial join, watersheds to seagrass
arcpy.SpatialJoin_analysis(
    'sg_103_extend',
    'population_10_dissolve',
    'sg_104_sjoin',
    'JOIN_ONE_TO_MANY',
    'KEEP_ALL',
    match_option='INTERSECT'
)

# frequency
arcpy.Frequency_analysis('sg_104_sjoin', 'sg_105_freq', ['uID'], ['SUM_pop_adjusted'])
# change null to zero
# there are 6 meadows that didn't overlap any land and therefore do not have values
# this is because the land dataset I used had very small islands removed
# all of these meadows except 1 overlap islands that do not have any structures
# on them. The one that has a dock doesn't appear to have a house, but it might
# be buried in the few trees. I'll ignore it.
with arcpy.da.UpdateCursor('sg_105_freq', ['SUM_pop_adjusted']) as cursor:
    for row in cursor:
        if row[0] == None:
            row[0] = 0
        cursor.updateRow(row)


# this is the end product. From this I have the uID of the seagrass meadow,
# the population of all the watersheds that touch that seagrass meadow
# and there is also a frequency field that shows how many touch that meadow