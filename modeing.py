# %%
import statsmodels.api as sm
import pandas as pd

# %%

sch_df = 'processed_schools_2015.csv'
nta_df = 'nta_SE_indicators_2015.csv'

# normalize all data pints to a single scale (z-scores)

# define independent variables (X) -> CCItpenalty/CCI (nta <-> school)
# CCI = travel_time + transfer_penalty
# school : funding_per_students(budget/size), 
# nta : poverty_rate_pct, median_income_estimate, unemployment_rate_pct, pop_15_to_19_pct, rent_burdened_35plus_pct, bachelors_deg_or_higher_pct, limited_english_proficiency_pct
# define dependent variable (y) -> grad_rate, adv_regents_rate

# interaction between travel_time and proverty_rate

# maybe add funding per pupil into CCI
# possible models : MLR (Lasso/Ridge), OLS, WLS, SAR/SEM, Mixed-Effects, GWR

# need to explore certain assumptions :
'''
Linearity - scatter plot of predictors vs residuals
Homosedasiticty - Breusch-Pagan test
Independence - check for variance inflation factor
Nomrmality of Residuals - 
'''

# model adequacy measures : RMSE, R^2, R^2 Adjusted, AIC/BIC, MAE
# calculate ICC 

X = data[['CCI','']]
y = data['Graduation_Rate']

# model fitting
model = sm.OLS(y, X).fit()

# result
print(model.summary())