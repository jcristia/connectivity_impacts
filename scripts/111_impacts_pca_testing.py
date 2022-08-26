# THIS script ended up having so much trial stuff in it that I ended up not
# using it for official plotting. It is good reference for the different methods
# that I tried, but see the next script for the official pca plots.

# exploratory pca plots
# env: plotting

# some general info (the links in each method are great too)
# https://builtin.com/data-science/step-step-explanation-principal-component-analysis


# try 3 ways:

# sklearn pca - this is the most widely used method in python, but to get
# loading arrows and labels it requires manual plotting work
# https://ostwalprasad.github.io/machine-learning/PCA-using-python.html
# https://towardsdatascience.com/pca-using-python-scikit-learn-e653f8989e60
# https://stackoverflow.com/questions/57340166/how-to-plot-the-pricipal-vectors-of-each-variable-after-performing-pca


# pca package - this is bult on sklearn, but it look like it packages up some of
# the more annoying plotting things. It looks like it is just 1 guy that
# maintains this though. It may not be something to rely on long term.
# https://pypi.org/project/pca/
# https://stackoverflow.com/questions/39216897/plot-pca-loadings-and-loading-in-biplot-in-sklearn-like-rs-autoplot

# plotly and dash - this is also built on sklearn but add some nicer looking
# plotting funcionality and gives the opportunity to have some interactive plots.
# https://plotly.com/python/pca-visualization/



# I don't understand all the different ordination methods, so I don't even know
# if a PCA is the best method here. However...
# In the end, don't worry about if you are using the best method. It is just to 
# do some exploratory analysis anyways.

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




##################################
# FIRST, a simple test to understand the scaling and transforming
# I was confused about how the scaling is actually done and why fit_transform
# is done twice.
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
df = pd.read_csv(r"C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_prioritizr_archive\scripts\rank_prioritize\test.csv")
df
x = StandardScaler().fit_transform(df)
x = pd.DataFrame(x, columns=df.columns)
x
# as you can see, we scale each feature so that the mean is at 0
# and then we use the standard deviation to compute the location of the values
pcamodel = PCA(n_components=2)
pca = pcamodel.fit_transform(x) 
# I'm not sure but I think the fit transform here is related to the dimension reduction.
# We are giving the empty pcamodel some data.
# Notice how fit_transform is a method of both standardscaler and PCA. However,
# in the documentation, it is just the pca that mentions that the transform is
# related to dimensionality reduction. So maybe they are called the same thing
# but they are doing something different.
j = pd.DataFrame(pca)
j # these are the coordinates in the new plane space for each point. Each row is a point.
pcamodel.components_ # these are the loadings?
pcamodel.components_.T
####################################



# and now the testing of the 3 methods described above:

# in separate environment, output to csv
import arcpy
import pandas as pd
sg = r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\spatial\main_seagrass.gdb\sg_7_imptotal_sourcesink_pts'
field_names = [i.name for i in arcpy.ListFields(sg) if i.type != 'OID']
cursor = arcpy.da.SearchCursor(sg, field_names)
df = pd.DataFrame(data=[row for row in cursor], columns=field_names)
# add northing as a field
df[['easting', 'northing']] = pd.DataFrame(df.Shape.to_list())
df = df[df.canusa=='can']
df.to_csv(r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\scripts\csv\sg_pca.csv')



import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from pca import pca
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px



# read in csv as df
df = pd.read_csv(r'C:\Users\jcristia\Documents\GIS\MSc_Projects\Impacts_connectivity_chap3\scripts\csv\sg_pca.csv')
df = df.drop(
    ['Unnamed: 0', 'Shape', 'area', 'ORIG_FID', 'canusa', 'total_norm_0_1', 
    'total_norm_1_2', 'total_norm_1_10', 'total_norm_1_100', 'regsink', 
    'regsource', 'easting'], 
    axis=1)


#################################
# 1st approach
#################################

# get just the features of interest:
df_featall = df.copy(deep=True)
df_x = df_featall.drop(['uID', 'northing'], axis=1)
df_y = df_featall.loc[:, ['northing']]

# need to standardize between -1 and 1
x = StandardScaler().fit_transform(df_x)
x = pd.DataFrame(x, columns=df_x.columns)

# pca components
pcamodel = PCA(n_components=5)
pca = pcamodel.fit_transform(x)
pca.shape

# explained variance plots
# I think this is the %:
pcamodel.explained_variance_ratio_ 
plt.plot(pcamodel.explained_variance_ratio_)
plt.xlabel('number of components')
plt.ylabel('cumulative explained variance')
plt.show()
# I think this is the actual variance values:
plt.bar(range(1,len(pcamodel.explained_variance_ )+1),pcamodel.explained_variance_ )
plt.ylabel('Explained variance')
plt.xlabel('Components')
plt.plot(range(1,len(pcamodel.explained_variance_ )+1),
         np.cumsum(pcamodel.explained_variance_),
         c='red',
         label="Cumulative Explained Variance")
plt.legend(loc='upper left')

# effects of variables on each component
ax = sns.heatmap(pcamodel.components_,
                 cmap='YlGnBu',
                 yticklabels=[ "PCA"+str(x) for x in range(1,pcamodel.n_components_+1)],
                 xticklabels=list(x.columns),
                 cbar_kws={"orientation": "horizontal"})
ax.set_aspect("equal")



# PCA scatter and loading plot
def myplot(score,coeff,labels=None):
    xs = score[:,0]
    ys = score[:,1]
    n = coeff.shape[0]
    scalex = 1.0/(xs.max() - xs.min())
    scaley = 1.0/(ys.max() - ys.min())
    plt.scatter(xs * scalex,ys * scaley,s=5)
    for i in range(n):
        plt.arrow(0, 0, coeff[i,0], coeff[i,1],color = 'r',alpha = 0.5)
        if labels is None:
            plt.text(coeff[i,0]* 1.15, coeff[i,1] * 1.15, "Var"+str(i+1), color = 'green', ha = 'center', va = 'center')
        else:
            plt.text(coeff[i,0]* 1.15, coeff[i,1] * 1.15, labels[i], color = 'g', ha = 'center', va = 'center')
 
    plt.xlabel("PC{}".format(1))
    plt.ylabel("PC{}".format(2))
    plt.grid()

myplot(pca[:,0:2],np.transpose(pcamodel.components_[0:2, :]),list(x.columns))
plt.show()

# This works!
# Initial impressions:
# most points are clustered around smaller values. I saw this in the base
# scatter plot in the previous script where most things have high naturalness
# and the variation is driven by a few high impact meadows.
# 
# I should definitley do a version with just impacts and just connectivity to
# dig into this deeper.
# BUT, one thing I can take from this, is that there is a lot more variation in
# the connectivity scores, which shows that once we include that information in
# the analysis, it complicates the selection.


#################################
# 2nd approach
#################################
# Initialize to reduce the data up to the number of componentes that explains 95% of the variance.
model = pca(n_components=0.95)
# Or reduce the data towards 2 PCs
model = pca(n_components=2)
# Fit transform
df_featall = df.copy(deep=True)
df_x = df_featall.drop(['uID', 'northing'], axis=1)
x = StandardScaler().fit_transform(df_x)
x = pd.DataFrame(x, columns=df_x.columns)
results = model.fit_transform(x)
# Plot explained variance
fig, ax = model.plot()
# Scatter first 2 PCs
fig, ax = model.scatter()
# Make biplot with the number of features
fig, ax = model.biplot(n_feat=4)

# Some thoughts:
# Based on some of the logging outputs, it looks like this approach does a lot
# of stuff under the hood. I'll pass by it for now. I do like the automatic
# plot labeling though.


#################################
# 3rd approach
#################################

df_featall = df.copy(deep=True)
df_x = df_featall.drop(['uID', 'northing'], axis=1)
df_y = df_featall.loc[:, ['uID']]
x = StandardScaler().fit_transform(df_x)
x = pd.DataFrame(x, columns=df_x.columns)
# so this will be every feature vs every other
fig = px.scatter_matrix(x)
fig.update_traces(diagonal_visible=False)
fig.show()
#fig.write_html('figs_out/scatter_matrix.html')
# if I want a better view of this then I can reduce which features are used by
# using 'dimensions' in the figure creation (see link)

# all principal components vs all others
pca = PCA()
components = pca.fit_transform(x)
labels = {
    str(i): f"PC {i+1} ({var:.1f}%)"
    for i, var in enumerate(pca.explained_variance_ratio_ * 100)
}

fig = px.scatter_matrix(
    components,
    labels=labels,
    dimensions=range(6)
)
fig.update_traces(diagonal_visible=False)
fig.show()

# visualize a subset of the principal components: (just 4)
n_components = 3
pca = PCA(n_components=n_components)
components = pca.fit_transform(x)
total_var = pca.explained_variance_ratio_.sum() * 100
labels = {str(i): f"PC {i+1}" for i in range(n_components)}
labels['color'] = 'Meadow'
fig = px.scatter_matrix(
    components,
    color=df_y.uID,
    dimensions=range(n_components),
    labels=labels,
    title=f'Total Explained Variance: {total_var:.2f}%',
)
fig.update_traces(diagonal_visible=False)
fig.show()

# plotting explained variance
pca = PCA()
pca.fit(x)
exp_var_cumul = np.cumsum(pca.explained_variance_ratio_)
px.area(
    x=range(1, exp_var_cumul.shape[0] + 1),
    y=exp_var_cumul,
    labels={"x": "# Components", "y": "Explained Variance"}
)

# visualize loadings
pca = PCA(n_components=2)
components = pca.fit_transform(x)
loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
fig = px.scatter(components, x=0, y=1, color=df_y['uID'])
for i, feature in enumerate(x.columns):
    fig.add_shape(
        type='line',
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
fig.show()
#
# THE lines don't scale well with this approach. I'm going to try to integrate
# the first approach into this one.
# I need to scale the values a bit. You can see this in the scalex and scaley
#
df_featall = df.copy(deep=True)
df_x = df_featall.drop(['uID', 'northing'], axis=1)
df_y = df_featall.loc[:, ['northing']]
x = StandardScaler().fit_transform(df_x)
x = pd.DataFrame(x, columns=df_x.columns)
pcamodel = PCA(n_components=2)
pca = pcamodel.fit_transform(x)
score = pca[:,0:2]
xs = score[:,0]
ys = score[:,1]
n = 2
scalex = 1.0/(xs.max() - xs.min())
scaley = 1.0/(ys.max() - ys.min())
fig = px.scatter(x=xs*scalex, y=ys*scaley, color=df_y['northing'] )
loadings = pcamodel.components_.T * np.sqrt(pcamodel.explained_variance_)
for i, feature in enumerate(x.columns):
    fig.add_shape(
        type='line',
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
fig.show()

# so from this smod is driving variation
# this isn't because the values are large, it is because there is a lot of
# variation in the values.
# cutblock is valuable information for meadows to the north

# There's very little variation between the  meadows in the north.
# To the south, the various metrics create variation.




