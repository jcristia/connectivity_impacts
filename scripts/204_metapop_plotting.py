# plots
# proportion of persistent populations by naturalness level, dispersal proportion, and r_0


import arcpy
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

gdb = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\metapop_pers.gdb'
arcpy.env.workspace = gdb
metapop_pers_pts = f'metapop_pers_centroids'
sg_orig = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\regional_connimpact.gdb\sg_7_imptotal_sourcesink_pts'

canada_only = True
naturalness_levels = ['probavg_BASE', 'probavg_1_2', 'probavg_1_10', 'probavg_1_100']
mort_rates = [0.15] # mortality rate of the settled population at each time step
larvae_dispersing_per_adult = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.50, 0.55, 0.6] # viable larvae produce that disperse


# read in pts as pandas df
field_names = [i.name for i in arcpy.ListFields(metapop_pers_pts)]
cursor = arcpy.da.SearchCursor(metapop_pers_pts, field_names)
persistence_df = pd.DataFrame(data=[row for row in cursor], columns=field_names)

# process only Canadian meadows?
if canada_only:

    # read in sg_orig dataset as df
    field_names = [i.name for i in arcpy.ListFields(sg_orig)]
    cursor = arcpy.da.SearchCursor(sg_orig, field_names)
    sg_orig = pd.DataFrame(data=[row for row in cursor], columns=field_names)

    # remove US ones from metapop df
    uids_keep = sg_orig.uID[sg_orig.canusa=='can']
    persistence_df = persistence_df[persistence_df.uID.isin(uids_keep)]

# get total length
sg_total_count = len(persistence_df)

# create blank df to append to
df_summary = pd.DataFrame(columns=['canada_only', 'naturalness', 'disp_prop', 'mortality_rate', 'persistent_percent'])

# for each persistence field
# get the nlevel, prop, r values
# calculate % persistent
# append to df
for nlevel in naturalness_levels:
    for prop in larvae_dispersing_per_adult:
        for mort in mort_rates:

            str_prop = str(prop).replace('.', '')
            str_mort = str(mort).split('.')[1]
            field = f'{nlevel}_prop{str_prop}_m{str_mort}'

            # check if field exists. If not, set perc_pers to zero.
            if field in list(persistence_df.columns):
                perc_pers = persistence_df[field].sum() / sg_total_count * 100
            else:
                perc_pers = pd.to_numeric('')

            df_summary = pd.concat([df_summary, pd.DataFrame({
                'canada_only': str(canada_only),
                'naturalness':nlevel, 
                'disp_prop':prop, 
                'mortality_rate':mort, 
                'persistent_percent':perc_pers
            }, index=[0,1,2,3,4])], ignore_index=True)

df_summary.loc[df_summary['naturalness'] == 'probavg_BASE', 'naturalness'] = 'base'
df_summary.loc[df_summary['naturalness'] == 'probavg_1_2', 'naturalness'] = '1-2'
df_summary.loc[df_summary['naturalness'] == 'probavg_1_10', 'naturalness'] = '1-10'
df_summary.loc[df_summary['naturalness'] == 'probavg_1_100', 'naturalness'] = '1-100'

# # plots (multiple plots across mortality rates)
# sns.set()
# sns.set_style('white')
# sns.set_context('paper')
# f = sns.relplot(
#     data = df_summary,
#     x = 'disp_prop',
#     y = 'persistent_percent',
#     hue = 'naturalness',
#     col='mortality_rate',
#     kind='line',
#     palette = 'tab10',
#     marker='o'
# )
# #f.set(xscale='log')
# f.set(xlabel='Proportion of population dispersing at each timestep', ylabel='% of seagrass meadows persistent')
# f.savefig('figs/sg_persistent.svg')


# Final plot for just 1 mortality rate:
df_final = df_summary[df_summary.mortality_rate == 0.15]
sns.set()
sns.set_style('white')
sns.set_context('paper', font_scale=1.25, rc={"lines.linewidth": 2})
f = sns.relplot(
    data = df_final,
    x = 'disp_prop',
    y = 'persistent_percent',
    hue = 'naturalness',
    kind='line',
    palette = 'tab10',
    marker='o'
)
f._legend.remove()
plt.legend(title='Naturalness range')
f.set(xlabel='Proportion of population produced and \n dispersing at each timestep ($\it{d}$)', ylabel='% of seagrass meadow populations persistent')
f.savefig(r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\scripts\figs\sgpersistent.svg')

# Output formatting:
# 1 column width in Facets is 8.84cm. Requires 300dpi.
# Size and DPI are printer settings not image file settings.
# Output as .svg and then use a free online tool to change dpi and convert to
# .tif. Choose one that allows you to specify no compression.
# https://www.freeconvert.com/svg-to-tiff
# To calculate pixel width from cm at 300 dpi:
# https://www.pixelto.net/cm-to-px-converter (1049 pixels)
