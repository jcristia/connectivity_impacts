
# - format connectivity lines -
# get connectivity data for PLD of 21 days
# average across all time periods
# (community detection env)

import os
import pandas as pd
import geopandas as gp

root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
out_gdb = os.path.join(root, 'spatial/connectivity.gdb')
conn_lines = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Hakai_chap1\scripts_runs_cluster\seagrass\seagrass_{}\shp_merged\connectivity_pld21.shp'
time_periods = [
    '20200228_SS201701', '20200309_SS201705', '20200309_SS201708',
    '20200310_SS201101', '20200310_SS201105', '20200310_SS201108',
    '20200327_SS201401', '20200327_SS201405', '20200327_SS201408'
]


# get all the shapefiles for a pld across all times
files = []
for sim in time_periods:
    file = conn_lines.format(sim)
    files.append(file)

# put them all in geodataframe
gdf_all = gp.GeoDataFrame()
for shp in files:
    gdf = gp.read_file(shp)
    gdf_all = gdf_all.append(gdf)
gdf_all = gdf_all.astype({'from_id':int, 'to_id':int}) # there's still a mix of datatypes in the columns for some reason. This was super important to do or else the code below didn't recognize duplicates.

# function to average lines across time periods
def mean_cust_denom(x):
    s = x.sum()
    m = s/float(len(time_periods))
    return m

# average
gdf_group = gdf_all.groupby(['from_id', 'to_id']).agg(
    freq = ('from_id', 'count'),
    prob_avg = ('prob', mean_cust_denom),
    totalori = ('totalori', 'sum'),
    totquant = ('quantity', 'sum'),
    geometry = ('geometry', 'first'),
    )
gdf_group = gdf_group.astype({'totalori':int, 'totquant':int})
gdf_group = gdf_group.reset_index()

# output
gdf_f = gp.GeoDataFrame(gdf_group, crs=gdf.crs)
gdf_f.to_file(filename=os.path.join(root, 'conn_avg_pld21.shp'), driver='ESRI Shapefile')