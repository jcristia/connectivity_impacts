# Set up master gdb seagrass feature classes


import arcpy


# master gdb
# this is where the main seagrass dataset will be and where I will join impacts
# and connectivity attributes to
root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
main_gdb = r'main_seagrass.gdb'
arcpy.env.workspace = os.path.join(root, 'spatial', main_gdb)

# seagrass dataset from Chapter 1
sg_og = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Hakai_chap1\scripts_runs_localstage\seagrass\seagrass\seagrass_20200228_SS\seagrass_prep\seagrass.gdb\seagrass_all_19FINAL'

# copy to main gdb
arcpy.CopyFeatures_management(sg_og, 'sg_1_og')

# erase feature (I created this manually):
erase_feat = r'erase_usa'

# erase US portion
arcpy.Erase_analysis('sg_1_og', erase_feat, 'sg_2_canada')


# RETRACING of features to match coastline
# This dataset is used to create buffers for the population and shoreline
# modification projects.

# There are many gaps between seagrass meadows and coastline, more than just 
# 100m. Therefore, if I only buffer by 100m then I am not selecting much of the 
# coastline. To deal with this:
# After much deliberation and testing automated methods the only sure way is to
# digitize. There is way too much variability in distances. If I add a series of
# buffers and move some but not others then it gets way too complicated and \
# loses accuracy.
# Follow: https://desktop.arcgis.com/en/arcmap/10.3/manage-data/editing-fundamentals/reshaping-a-polygon-to-match-another-feature.htm#
#   double click in grey area of row to zoom to feature
#   create an attribute to keep track of where I am
#   Criteria for whether or not I edit the feature: I ended up digitizing most 
#   of them even if it was just a small area. However, in some areas if it was 
#   just a sliver and there was clearly no development then I didn't bother.

# This work was done previously and it is just copied here for record keeping.
# This dataset gets referenced by other scripts, so I want it in a central place.
# This dataset had a lot of manual work involved so it is good that it is backed
# up in numerous places.
retraced_feat = os.path.join(root, r'spatial\shoreline_modification\shoreline_modification_ARCHIVED20210224.gdb\sg_101_retrace'
arcpy.CopyFeatures_management(retraced_feat, 'sg_101_retrace')

# copy in land feature class
land = os.path.join(root, r'spatial\shoreline_modification\shoreline_modification_ARCHIVED20210224.gdb\coastline_bc_ak_wa_or_cleaned_less10000')
arcpy.CopyFeatures_management(land, 'coastline_bc_ak_wa_or_cleaned_less10000')