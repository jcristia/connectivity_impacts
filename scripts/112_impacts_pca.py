# exploratory pca plots
# env: plotting

# see script 103 for notes on pca and different methods tried
# I'm using the plotly approach. It still uses sklearn like all the other
# methods, it just allows me to have interactive plots. This is super convenient
# when you have a lot of points. I can hover over certain points and find out
# their uID.
# https://plotly.com/python/pca-visualization/


# PCA in general:
# view multiple dimensions on 2 axes. Reduce the number of dimensions. View
# what is driving most of the variation and see which seagrass meadows load on
# which drivers.
#
# Geometrically speaking, principal components represent the directions of the 
# data that explain a maximal amount of variance, that is to say, the lines that
# capture most information of the data. The relationship between variance and 
# information here, is that, the larger the variance carried by a line, the 
# larger the dispersion of the data points along it, and the larger the 
# dispersion along a line, the more the information it has. To put all this 
# simply, just think of principal components as new axes that provide the best 
# angle to see and evaluate the data, so that the differences between the 
# observations are better visible.

# One thing to remember: this isn't necessarily telling me anything absolute
# about the values. It is simply showing what are the primary varibales that
# are making meadows VARY.


# in separate environment, output to csv
import arcpy
import pandas as pd
root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
gdb = os.path.join(root, r'spatial/main_seagrass.gdb')
arcpy.env.workspace = gdb
arcpy.Project_management('sg_7_imptotal_sourcesink_pts', 'temp', 4326)
field_names = [i.name for i in arcpy.ListFields('temp') if i.type != 'OID']
cursor = arcpy.da.SearchCursor('temp', field_names)
df = pd.DataFrame(data=[row for row in cursor], columns=field_names)
# add northing as a field
df[['longitude', 'latitude']] = pd.DataFrame(df.Shape.to_list())
df = df[df.canusa=='can']
df.to_csv(os.path.join(root, r'scripts\csv\sg_pca.csv'))
arcpy.Delete_management('temp')


# env: plotting
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px

# read in csv as df
root = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3'
df = pd.read_csv(os.path.join(root, r'scripts\csv\sg_pca.csv'))
df = df.drop(
    ['Unnamed: 0', 'Shape', 'area', 'ORIG_FID', 'canusa', 'total_norm_0_1', 
    'total_norm_1_2', 'total_norm_1_10', 'total_norm_1_100', 'regsink', 
    'regsource', 'longitude'], 
    axis=1)

df = df.rename(columns={
    'popn':'population', 
    'ow_perc':'overwater structures',
    'smodperc':'shoreline modifcation',
    'agricult':'agriculture',
    'gcrab':'green crab'})

df_featall = df.copy(deep=True)
df_x = df_featall.drop(['uID', 'latitude'], axis=1)
df_y = df_featall.loc[:, ['latitude']]
x = StandardScaler().fit_transform(df_x)
x = pd.DataFrame(x, columns=df_x.columns)

# (1) every feature vs every other feature
# fig = px.scatter_matrix(x)
# fig.update_traces(diagonal_visible=False)
# fig.show()
# fig.write_html('figs_out/scatter_matrix_impacts.html')

# (2) cumulative explained variation
# pca = PCA()
# pca.fit(x)
# exp_var_cumul = np.cumsum(pca.explained_variance_ratio_)
# fig = px.area(
#     x=range(1, exp_var_cumul.shape[0] + 1),
#     y=exp_var_cumul,
#     labels={"x": "# Components", "y": "Explained Variance"}
# )
# fig.show()
# fig.write_html('figs_out/variation_explained_impacts.html')

# (3) scatter and loadings plot
pcamodel = PCA(n_components=2)
pca = pcamodel.fit_transform(x)
score = pca[:,0:2]
xs = score[:,0]
ys = score[:,1]
n = 2
scalex = 1.0/(xs.max() - xs.min())
scaley = 1.0/(ys.max() - ys.min())
fig = px.scatter(x=xs*scalex, y=ys*scaley, color=df_y['latitude'], template='ggplot2',
    labels=dict(x="PCA1 (26%)", y="PCA2 (19%)"))
loadings = pcamodel.components_.T * np.sqrt(pcamodel.explained_variance_)
for i, feature in enumerate(x.columns):
    fig.add_shape(
        type='line',
        line_color="grey", line_width=1.5, opacity=1, #line_dash="dot",
        x0=0, y0=0,
        x1=loadings[i, 0],
        y1=loadings[i, 1]
    )
    fig.add_annotation(
        x=loadings[i, 0],
        y=loadings[i, 1],
        ax=0, ay=0,
        xanchor="center",
        yanchor="bottom",
        text=feature,
    )
fig.update_yaxes(
    zeroline=True, zerolinewidth=1, zerolinecolor='black',
    showgrid=False,
    showline=True, linewidth=1, linecolor='black', mirror=True
)
fig.update_xaxes(
    zeroline=True, zerolinewidth=1, zerolinecolor='black',
    showgrid=False,
    showline=True, linewidth=1, linecolor='black', mirror=True
)
fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)'
)
fig.layout.coloraxis.colorbar.title = 'latitude'
fig.show()
fig.write_image(os.path.join(root, 'scripts/figs/pca.png'))

# population and shoreline modification are driving a lot of the variation
# it is interesting to see it opposite of cutblocks. I guess that is because
# most cutblocks are in natural areas and they leave coastline buffers

# However, I think it is just a few highly impacted meadows showing up as scattered
# and the rest are more clustered along these first 2 axes. But, I think this is
# ok, it is showing that my metrics aren't redundant.

# One thing to remember: this isn't necessarily telling me anything absolute
# about the values. It is simply showing what are the primary varibales that
# are making meadows VARY.
# BUT remember, these 2 axes are only explaining xx percent of the variation,
# so in a way, many of things are needed to explain the differences in meadows.

# Its good that most metrics don't align with each other, or else they would be redundant.
# !!! Impacts are not redundant in their spatial distribution, so even though they 
# could be redundant in their effects on seagrass/inverts/fish (e.g. cutblocks 
# have the same resulting effect as shoreline mod), those effects would be 
# spatially distributed.