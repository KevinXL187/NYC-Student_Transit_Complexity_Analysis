# %%
# pyright: basic
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
import statsmodels.formula.api as smf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.linear_model import LassoCV, RidgeCV
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# %%
sch_df = pd.read_csv('processed_schools_2015.csv')
nta_df = pd.read_csv('nta_SE_indicators_2015.csv')
cci_df = pd.read_csv('cci_result.csv')

if 'cci_cost' in cci_df.columns and 'CCI' not in cci_df.columns:
    cci_df = cci_df.rename(columns={'cci_cost': 'CCI'})
cci_df['school_id'] = cci_df['school_id'].str.replace('school_', '')
cci_df['origin_id'] = cci_df['origin_id'].str.replace('nta_', '')

main_df = pd.merge(cci_df, sch_df, left_on='school_id', right_on='LOCATION_CODE', how='inner')
main_df = pd.merge(main_df, nta_df, left_on='origin_id', right_on='GeoID', how='inner')

# Interaction term: Travel accessibility impact moderated by poverty
main_df['travel_poverty_interaction'] = main_df['CCI'] * main_df['poverty_rate_pct']

predictors = [
    'CCI', 'funding_per_student', 'poverty_rate_pct', 'median_income_estimate', 
    'unemployment_rate_pct', 'rent_burdened_35plus_pct', 'travel_poverty_interaction'
]
target = 'grad_rate'

# Drop missing values
main_df = main_df.dropna(subset=predictors + [target])

# %%
# train,test spilt & scale 
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    main_df[predictors], 
    main_df[target], 
    test_size=0.2, 
    random_state=42
)

scaler = StandardScaler()
X_train = pd.DataFrame(scaler.fit_transform(X_train_raw), columns=predictors, index=X_train_raw.index)
X_test = pd.DataFrame(scaler.transform(X_test_raw), columns=predictors, index=X_test_raw.index)

# %%
# OLS MODEL Base
X_train_ols = sm.add_constant(X_train)
ols_model = sm.OLS(y_train, X_train_ols).fit()

print("OLS Regression Summary (Training Set)")
print(ols_model.summary())
print("\n")

# %%
# Assumption 
residuals = ols_model.resid
fitted_values = ols_model.fittedvalues

# Linearity
plt.figure(figsize=(8, 5))
sns.scatterplot(x=fitted_values, y=residuals, alpha=0.5)
plt.axhline(0, color='red', linestyle='--')
plt.title("Linearity: Fitted Values vs Residuals")
plt.show()

# Homoscedasticity (Breusch-Pagan)
bp_test = het_breuschpagan(residuals, ols_model.model.exog)
print(f"=== Breusch-Pagan Test (p-value): {bp_test[1]:.4f} ===")

# Independence (VIF & Durbin-Watson)
vif_data = pd.DataFrame({
    "Feature": ols_model.model.exog_names,
    "VIF": [variance_inflation_factor(ols_model.model.exog, i) for i in range(ols_model.model.exog.shape[1])]
})
print("\n=== VIF Results ===\n", vif_data)
print(f"Durbin-Watson Score: {durbin_watson(residuals):.4f}")

# Normality (Q-Q Plot & Shapiro-Wilk)
plt.figure(figsize=(6, 6))
stats.probplot(residuals, dist="norm", plot=plt)
plt.show()
shapiro_p = stats.shapiro(residuals)[1]
print(f"=== Shapiro-Wilk Normality Test (p-value): {shapiro_p:.4f} ===")

# %%
# MLR (LASSO / RIDGE)
print("\nRegularized Regression (Lasso & Ridge)")

# Lasso (L1) - Good for feature selection
lasso = LassoCV(cv=5, random_state=42).fit(X_train, y_train)
y_pred_lasso = lasso.predict(X_test)

# Ridge (L2) - Good for multicollinearity
ridge = RidgeCV(cv=5).fit(X_train, y_train)
y_pred_ridge = ridge.predict(X_test)

def eval_reg(name, model_obj, y_pred):
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"--- {name} Results ---")
    print(f"Best Alpha: {model_obj.alpha_:.4f}")
    print(f"Test RMSE:  {rmse:.4f}")
    print(f"Coefficients: {dict(zip(predictors, model_obj.coef_.round(4)))}\n")

eval_reg("Lasso", lasso, y_pred_lasso)
eval_reg("Ridge", ridge, y_pred_ridge)

# %%
# MIXED MODELING (NTA GROUPING)
# use unscaled data for clarity
mixed_formula = f"{target} ~ {' + '.join(predictors)}"
mixed_model = smf.mixedlm(
    mixed_formula, main_df, 
    groups=main_df["origin_id"]
    ).fit()

print("=== Mixed Effects Model (Grouping by NTA) ===")
print(mixed_model.summary())

# %%
# Model Comparison
X_test_ols = sm.add_constant(X_test)
y_pred_ols = ols_model.predict(X_test_ols)

def get_error_metrics(y_true, y_pred):
    return {
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAE": mean_absolute_error(y_true, y_pred)
    }

prediction_comparison = pd.DataFrame({
    "OLS": get_error_metrics(y_test, y_pred_ols),
    "Lasso": get_error_metrics(y_test, y_pred_lasso),
    "Ridge": get_error_metrics(y_test, y_pred_ridge)
})

print("=== Predictive Performance (Test Set) ===")
print(prediction_comparison)
print("\n")

print("=== Statistical Fit Comparison ===")
likelihood_comparison = pd.DataFrame({
    "Metric": ["AIC", "BIC", "Log-Likelihood"],
    "OLS (Train)": [ols_model.aic, ols_model.bic, ols_model.llf],
    "Mixed (Full)": [mixed_model.aic, mixed_model.bic, mixed_model.llf]
})
print(likelihood_comparison)
# %%
