# link component ID of connections to seagrass centroid persistence points

# the idea behind linking persistence to components:
# From the population model, I want to know which are the meadows that are 
# contributing to persistence. This is directly related to 'strongly connected 
# components'. 
# First start with ones that persistent. Then find which ones form closed loops.
# A node that is a sink but sends nothing to the network it is connected to, is
# not contributing to persistence.

import arcpy
import pandas as pd


gdb = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\metapop_pers.gdb'
arcpy.env.workspace = gdb
metapop_pers = f'metapop_pers_centroids'

naturalness_levels = ['probavg_BASE', 'probavg_1_2', 'probavg_1_10', 'probavg_1_100']
mort_rates = [0.15] # mortality rate of the settled population at each time step
larvae_dispersing_per_adult = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.50, 0.55, 0.6] # viable larvae produce that disperse


# copy metapop persistence points
arcpy.env.overwriteOutput = True
metapop_fc = 'metapop_pers_centroids_components'
arcpy.CopyFeatures_management(metapop_pers, metapop_fc)
arcpy.env.overwriteOutput = False


# go through each nlevel-disp-r0 combo and for each uID assign which component it
# is part of based on the components assigned to connections
# Note: I will use strongly connected components here.
# a point can be a sink from two different strongly connected components, but 
# since it doesn't send anything back to them, it shouldn't be considered as 
# part of their metapopulation. It provides no rescue effect. However, I don't 
# want to ignore it if it is persistent because of self-connection and sink 
# connections, so I will still symbolize it in the map but with a grey color.

for nlevel in naturalness_levels:
    for disp_prop in larvae_dispersing_per_adult:
        for mort in mort_rates:

            str_prop = str(disp_prop).replace('.', '')
            str_mort = str(mort).split('.')[1]

            # add field for component id
            field_comp = f'comp_{nlevel}_{str_prop}_{str_mort}'
            arcpy.AddField_management(metapop_fc, field_comp, 'SHORT')

            # get connections associated with that pld-prop-r0 combo as pandas df
            conns = f'conn_{nlevel}_prop{str_prop}_m{str_mort}_comps'
            if not arcpy.Exists(conns):
                continue # if nothing was persistent then it won't exist, can just leave the field empty
            field_names = [i.name for i in arcpy.ListFields(conns)]
            cursor = arcpy.da.SearchCursor(conns, field_names)
            conns_df = pd.DataFrame(data=[row for row in cursor], columns=field_names)

            # using an update cursor, for the uID, look up the from_id in the connections and get the id of the strongly connected component
            with arcpy.da.UpdateCursor(metapop_fc, ['uID', field_comp]) as cursor:
                for row in cursor:
                    comp_id = conns_df.component_strong[conns_df.from_id == row[0]].reset_index(drop=True)
                    # for a given from_id, a component id can be one id or -1
                    if len(comp_id.unique()) > 2:
                        print(f'uID belongs to multiple components: {row[0]}')
                        raise ValueError('Cannot assign component')
                    # just assign the max
                    if len(comp_id.unique()) > 0:
                        row[1] = comp_id.unique().max()
                    else: # there is a meadow that has no self-connections so it doesn't appear in the connectionst list
                        row[1] = -1
                    cursor.updateRow(row)




