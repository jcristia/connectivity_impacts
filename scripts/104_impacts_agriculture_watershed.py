# calculate area of agricutlture in each watershed overlapping with each 
# seagrass meadow


import arcpy
from arcpy.sa import *
import os

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
outgdb = 'agriculture_watershed.gdb'
sg_ext = os.path.join(root, 'population.gdb/sg_103_extend') # sg polys already buffered and extended to overlap with watersheds
watersheds_overlapping = os.path.join(root, 'population.gdb/watersheds_01_intersect') # watersheds already selected as overlapping with seagrass
coastline = 'main_seagrass.gdb/coastline_bc_ak_wa_or_cleaned_less10000'
landuse_rast = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\1Data_BASE\LandUse\LandUse_Canada_2010.gdb\landuse_2010'
arcpy.env.workspace = os.path.join(root, outgdb)

# create raster with only agriculture, all other cells null
inRas = Raster(landuse_rast)
outRas = Con(inRas, inRas, None, 'Value = 51')
outRas.save('landuse_01_cropland')

# raster to polygon
arcpy.RasterToPolygon_conversion(
    'landuse_01_cropland', 
    'landuse_02_polys', 
    'NO_SIMPLIFY')

# intersect with watersheds
arcpy.Intersect_analysis(
    ['landuse_02_polys', watersheds_overlapping],
    'landuse_03_intersect')

# 
arcpy.Frequency_analysis('landuse_03_intersect', 'landuse_04_freq', 'jc_ID', 'Shape_Area')
arcpy.AddField_management('landuse_04_freq', 'area_cropland', 'FLOAT')
with arcpy.da.UpdateCursor('landuse_04_freq', ['Shape_Area', 'area_cropland']) as cursor:
    for row in cursor:
        row[1] = row[0]
        cursor.updateRow(row)

arcpy.env.qualifiedFieldNames = False
w_join = arcpy.AddJoin_management(watersheds_overlapping, 'jc_ID', 'landuse_04_freq', 'jc_ID')
arcpy.CopyFeatures_management(w_join, 'watersheds_02_agriculture')

arcpy.AddField_management('watersheds_02_agriculture', 'area_total_watershed', 'FLOAT')
with arcpy.da.UpdateCursor('watersheds_02_agriculture', ['area_total_watershed', 'SHAPE_Area']) as cursor:
    for row in cursor:
        row[0]=row[1]
        cursor.updateRow(row)

# spatial join, watersheds to seagrass
arcpy.SpatialJoin_analysis(
    sg_ext,
    'watersheds_02_agriculture',
    'sg_104_sjoin',
    'JOIN_ONE_TO_MANY',
    'KEEP_ALL',
    match_option='INTERSECT'
)

arcpy.Frequency_analysis('sg_104_sjoin', 'sg_105_freq', ['uID'], ['area_cropland', 'area_total_watershed'])
arcpy.AddField_management('sg_105_freq', 'percent_cropland', 'FLOAT')
with arcpy.da.UpdateCursor('sg_105_freq', ['area_cropland', 'area_total_watershed', 'percent_cropland']) as cursor:
    for row in cursor:
        if row[0] == None:
            areacrop=0
        else:
            areacrop=row[0]
        row[2] = (areacrop/row[1]) * 100.0
        cursor.updateRow(row)

# sg_105_freq, attribute percent_cropland is my final result