# calculate area of overwater structures in 1km buffer for each seagrass meadow
# Some !!!MANUAL!!! edits required. Review script before running again.

# KML file is from the work that Katherine Bannar-Martin did for me

import arcpy
import os
import pandas as pd
import numpy as np
import openpyxl

# I am using a 1km buffer.
# Iacarella 2018 used a 2km buffer. They said this was because it was about the
# of the bay scale in the southern Strait of Georgia.
# Nagel et al 2020 used a 1km buffer (no justification given).
# I will use a 1km buffer since I am doing it for so many meadows and I want to
# draw more differences between them.


root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial'
ow_gdb = 'overwater_structures.gdb'
arcpy.env.workspace = os.path.join(root, ow_gdb)
sg_og = os.path.join(root, 'main_seagrass.gdb/sg_2_canada')
land = os.path.join(root, 'main_seagrass.gdb/coastline_bc_ak_wa_or_cleaned_less10000')
ow_kml = os.path.join(root, 'shoreline_modification/Katherine/EelgrassContract_BannarMartin/ow_structures_TOEDIT_BannarMartin.kmz')
sheet = os.path.join(root, 'overwater_structures/Docks&Floathomes_BC_2017.xlsx')

##########################
# buffers
arcpy.Buffer_analysis(sg_og, 'sg_01_buff1km', 1000)
arcpy.Erase_analysis('sg_01_buff1km', land, 'sg_02_erase')
arcpy.MultipartToSinglepart_management('sg_02_erase', 'sg_03_multisingle')
arcpy.AddField_management('sg_03_multisingle', 'partID', 'SHORT')
with arcpy.da.UpdateCursor('sg_03_multisingle', ['OBJECTID', 'partID']) as cursor:
    for row in cursor:
        row[1]=row[0]
        cursor.updateRow(row)

# Doing one spatial select with 'Intersect' or 'Contains' does not work. You 
# still get small pieces selected because they touch other meadows that are not 
# their ID meadow. So I think I need to do more brute force:
# In a for loop, create a layer for each uID, for both the sg and the buff
# do the spatial select and add the partid of the piece to a list
# then use the list to select the pieces by attribute.
# This takes a while to run, but I think it is the only way.

arcpy.SetLogHistory(False) # trying to speed this up, not sure if it matters
features = []
uIDs = [row[0] for row in arcpy.da.SearchCursor(sg_og, ['uID'])]
arcpy.MakeFeatureLayer_management(sg_og, 'tmp_sg') # way faster creating layers
arcpy.MakeFeatureLayer_management('sg_03_multisingle', 'tmp_buff')
for i in uIDs:
    print('spatial select for feature {}, {} of {}'.format(str(i), str(uIDs.index(i)), str(len(uIDs))))
    arcpy.SelectLayerByAttribute_management(
        'tmp_sg',
        'NEW_SELECTION',
        "uID = {}".format(i)
    )
    arcpy.SelectLayerByLocation_management(
        'tmp_buff',
        'INTERSECT',
        'tmp_sg',
    )  
    arcpy.SelectLayerByAttribute_management(
        'tmp_buff',
        'SUBSET_SELECTION',
        "uID = {}".format(i)
    ) 
    sel_count = int(arcpy.GetCount_management('tmp_buff')[0])
    if sel_count!=1:
        print(sel_count)
        print('more/less than 1 feature selected')
        break
    with arcpy.da.SearchCursor('tmp_buff', ['partID']) as cursor:
        for row in cursor:
            features.append(row[0])
    arcpy.SelectLayerByAttribute_management('tmp_buff', 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management('tmp_sg', 'CLEAR_SELECTION')

feat_tup = tuple(features)
sel_feat = arcpy.SelectLayerByAttribute_management(
    'sg_03_multisingle',
    'NEW_SELECTION',
    "partID IN {}".format(feat_tup)
)
arcpy.CopyFeatures_management(sel_feat, 'sg_04_remPart')
arcpy.Delete_management('tmp_buff')
arcpy.Delete_management('tmp_sg')


#############################
# overwater structures from kmz and csv

# Katherine's
arcpy.KMLToLayer_conversion(
    ow_kml,
    os.path.join(root, 'overwater_structures'),
    'ow_transfer_TEMP'    
)
points = os.path.join(root, 'overwater_structures', 'ow_transfer_TEMP.gdb', 'Placemarks/Points')
arcpy.CopyFeatures_management(points, 'ow_01a_Katherine')
arcpy.Delete_management(os.path.join(root, 'overwater_structures/ow_transfer_TEMP.gdb'))
arcpy.Delete_management(os.path.join(root, 'overwater_structures/ow_transfer_TEMP.lyrx'))

# Josie's
docks = pd.read_excel(sheet, 'Docks', engine='openpyxl')
out = os.path.join(root, 'overwater_structures/docks_TEMP.csv')
docks.to_csv(out)
arcpy.MakeXYEventLayer_management(out, 'Long', 'Lat', 'tmp_lyr', 4326)
arcpy.CopyFeatures_management('tmp_lyr', 'ow_01b_JosieDocks')
arcpy.Delete_management(out)
arcpy.Delete_management('tmp_lyr')

fhomes = pd.read_excel(sheet, 'Floathomes', engine='openpyxl')
out = os.path.join(root, 'overwater_structures/fhomes_TEMP.csv')
fhomes.to_csv(out)
arcpy.MakeXYEventLayer_management(out, 'Long', 'Lat', 'tmp_lyr', 4326)
arcpy.CopyFeatures_management('tmp_lyr', 'ow_01c_JosieFloathomes')
arcpy.Delete_management(out)
arcpy.Delete_management('tmp_lyr')


############################
# Attributes:

# floathome measurements:
# I measured a selection of the floathomes from Katherine's dataset and Josie's
# They ones from Josie fall in the range of the medium dock size, from the 
# size.measures tab in Josie's spreadsheet.
# In Katherine's dataset there are only 3 and they are all small.

# clean up Katherine dataset
arcpy.CopyFeatures_management('ow_01a_Katherine', 'ow_02a_KatherineClean')
arcpy.AddFields_management(
    'ow_02a_KatherineClean',
    [
        ['orig_id', 'SHORT', 'orig_id'],
        ['orig_desc', 'TEXT', 'orig_desc', 255],
        ['source', 'TEXT', 'source', 255],
        ['common_desc', 'TEXT', 'common_desc', 255],
        ['ow_area', 'FLOAT', 'ow_area']
    ]
)
fields = ['Name', 'PopupInfo', 'orig_id', 'orig_desc', 'source']
with arcpy.da.UpdateCursor('ow_02a_KatherineClean', fields) as cursor:
    for row in cursor:
        row[2] = int(row[0])
        row[3] = row[1]
        row[4] = 'KBM'
        cursor.updateRow(row)
with arcpy.da.UpdateCursor('ow_02a_KatherineClean', ['orig_desc', 'common_desc']) as cursor:
    for row in cursor:
        if row[0] in ('aquaculture', 'aquaculutre', 'logboom', 'marine_area', 'medium;logging', 'planes', 'ferry'):
            row[1]='marina_area'
        elif row[0] in ('floathome', 'houseboat'):
            row[1]='small'
        elif row[0] in ('unclear', 'unknown'):
            row[1]='to_edit_manually'
        else:
            row[1]=row[0]
        cursor.updateRow(row)
# !!! next, MANUALLY determine classification for the 7 rows that are 'to_edit_manually'
# also, I'm finding that aquaculture and logbooms do not neatly fit into any category,
# so go through every row for anything not labeled marina/medium/small and do a
# quick classification
arcpy.CopyFeatures_management('ow_02a_KatherineClean', 'ow_03a_KBMmanualedits')
arcpy.DeleteField_management('ow_03a_KBMmanualedits', ['Name', 'FolderPath', 'SymbolID', 'AltMode', 'Base', 'Snippet', 'PopupInfo', 'HasLabel', 'LabelID'])

# add common_type field. I will use this to create separate metrics for special
# cases like aquaculture and logbooms
# I decided to do this after the previous add field and after manual edits, so
# it is separate.
arcpy.AddField_management('ow_03a_KBMmanualedits', 'common_type', 'TEXT')
with arcpy.da.UpdateCursor('ow_03a_KBMmanualedits', ['orig_desc', 'common_type']) as cursor:
    for row in cursor:
        if row[0] in ('aquaculture', 'aquaculutre'):
            row[1]='aquaculture'
        elif row[0] in ('logboom', 'medium;logging'):
            row[1]='logboom'
        elif row[0] in ('marine_area', 'medium', 'small', 'planes', 'ferry'):
            row[1]='dock'
        elif row[0] in ('floathome', 'houseboat'):
            row[1]='floathome'
        elif row[0] in ('unclear', 'unknown'):
            row[1]='to_edit_manually'
        cursor.updateRow(row)
# !!! next, MANUALLY determine classification for the 7 rows that are 'to_edit_manually'


# do the same for Josie's docks and floathomes
arcpy.CopyFeatures_management('ow_01b_JosieDocks', 'ow_02b_JDocksClean')
arcpy.CopyFeatures_management('ow_01c_JosieFloathomes', 'ow_02c_JFloathomesClean')
arcpy.AddFields_management(
    'ow_02b_JDocksClean',
    [
        ['orig_id', 'SHORT', 'orig_id'],
        ['orig_desc', 'TEXT', 'orig_desc', 255],
        ['source', 'TEXT', 'source', 255],
        ['common_desc', 'TEXT', 'common_desc', 255],
        ['ow_area', 'FLOAT', 'ow_area'],
        ['common_type', 'TEXT', 'common_type', 255]
    ]
)
arcpy.AddFields_management(
    'ow_02c_JFloathomesClean',
    [
        ['orig_id', 'SHORT', 'orig_id'],
        ['orig_desc', 'TEXT', 'orig_desc', 255],
        ['source', 'TEXT', 'source', 255],
        ['common_desc', 'TEXT', 'common_desc', 255],
        ['ow_area', 'FLOAT', 'ow_area'],
        ['common_type', 'TEXT', 'common_type', 255]
    ]
)
fields = ['Field1', 'Category', 'orig_id', 'orig_desc', 'source', 'common_desc', 'common_type']
with arcpy.da.UpdateCursor('ow_02b_JDocksClean', fields) as cursor:
    for row in cursor:
        row[2]=row[0]
        row[3]=row[1]
        row[4]='JIdocks'
        row[6]='floathome'
        if row[1]=='Marina.area':
            row[5]='marina_area'
        elif row[1]=='Medium':
            row[5]='medium'
        elif row[1]=='Small':
            row[5]='small'
        cursor.updateRow(row)
fields = ['Field1', 'Category', 'orig_id', 'orig_desc', 'source', 'common_desc', 'common_type']
with arcpy.da.UpdateCursor('ow_02c_JFloathomesClean', fields) as cursor:
    for row in cursor:
        row[2]=row[0]
        row[3]=row[1]
        row[4]='JIfloathomes'
        row[6]='floathome'
        row[5]='medium'  # in Josies datasets most floathomes are medium. In Katherine's there are only 3 and they are small.
        cursor.updateRow(row)

arcpy.DeleteField_management('ow_02b_JDocksClean', ['Field1', 'Region', 'FID', 'ID', 'Category', 'Lat', 'Long', 'Area_m2'])
arcpy.DeleteField_management('ow_02c_JFloathomesClean', ['Field1', 'Region', 'FID', 'ID', 'Category', 'Lat', 'Long', 'Type', 'Transport_Canada_IDed_locations', 'Unnamed__8'])


############################
# combine all and fill in area field

arcpy.Merge_management(
    ['ow_03a_KBMmanualedits', 'ow_02b_JDocksClean', 'ow_02c_JFloathomesClean'],
    'ow_04_merge'
)
with arcpy.da.UpdateCursor('ow_04_merge', ['common_desc','ow_area']) as cursor:
    for row in cursor:
        if row[0]=='marina_area':
            row[1]=2755.7
        elif row[0]=='medium':
            row[1]=429.97
        elif row[0]=='small':
            row[1]=67.05
        cursor.updateRow(row)

############################
# associate seagrass and overwater structures

arcpy.SpatialJoin_analysis(
    'sg_04_remPart',
    'ow_04_merge',
    'sg_05_sjoin',
    'JOIN_ONE_TO_MANY',
    'KEEP_ALL',
    match_option='INTERSECT'
)

# overwater percent
arcpy.Frequency_analysis('sg_05_sjoin', 'sg_06_freqArea', ['uID'], ['ow_area'])
arcpy.env.qualifiedFieldNames = False # prevent table being part of field names in 
joined_table = arcpy.AddJoin_management('sg_04_remPart', 'uID', 'sg_06_freqArea', 'uID')
arcpy.CopyFeatures_management(joined_table, 'sg_07a_AREA')
arcpy.AddField_management('sg_07a_AREA', 'ow_percent', 'DOUBLE')
with arcpy.da.UpdateCursor('sg_07a_AREA', ['ow_area', 'Shape_Area', 'ow_percent']) as cursor:
    for row in cursor:
        if row[0] == None:
            row[2]=0.0
        else:
            row[2]=(row[0]/row[1]) *100
        cursor.updateRow(row)

# count of type
field_names = [i.name for i in arcpy.ListFields('sg_05_sjoin')]
field_names = ['uID', 'common_type']
cursor = arcpy.da.SearchCursor('sg_05_sjoin', field_names)
df = pd.DataFrame(data=[row for row in cursor], columns=field_names)

df_agg = df.groupby(['uID', 'common_type']).agg(
    common_type_COUNT = ('uID', 'count')
).reset_index()

df_pivot = df_agg.pivot_table('common_type_COUNT', 'uID', 'common_type')
df = df_pivot.rename_axis(None, axis=1).reset_index()

x = np.array(np.rec.fromrecords(df.values))
names = df.dtypes.index.tolist()
x.dtype.names = tuple(names)
arcpy.da.NumPyArrayToTable(x, os.path.join(arcpy.env.workspace, 'sg_07b_TYPECOUNT'))
# for some reason the numpy to table function requires a full file path



# RESULTS:
# sg_07a_AREA gives me AREA PERCENT. It also still has the FREQUENCY field so
# that I can get a count.
# sg_07b_TYPECOUNT gives me the count of structure type in each buffer. This
# might be useful for noting the extra effects from aquaculture and wood waste