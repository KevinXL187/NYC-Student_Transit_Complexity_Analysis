# %%
import statsmodels.api as sm

# %%

data = 

# define independent variables (X) and dependent variable (y)
X = data[['CCI', 'funding_per_pupil', 'pct_temp_housing']]
y = data['Graduation_Rate']

# model fitting
model = sm.OLS(y, X).fit()

# result
print(model.summary())