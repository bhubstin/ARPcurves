# ARPS Curve Fitting Bug Fix

## Issue Summary
The ARPS (Arps Decline Curve Analysis) curves were not fitting production data correctly due to a **time array indexing mismatch** between the curve fitting process and visualization.

## Root Cause

### The Problem
There was an inconsistency in how time arrays were constructed:

**During Curve Fitting:**
```python
# INCORRECT - Time started at 1
t_act = df['Date'].rank(method='min', ascending=True).to_numpy()
# Result: [1, 2, 3, 4, ...]
```

**During Visualization:**
```python
# Time started at 0
t_months = np.arange(0, len(actual_data) + forecast_months)
# Result: [0, 1, 2, 3, ...]
```

### Why This Matters

The ARPS hyperbolic decline equation is:
```
q(t) = Qi / (1 + b * Di * t)^(1/b)
```

Where:
- `Qi` = Initial production rate at **t=0**
- `t` = Time in months from start of production
- `b` = Hyperbolic decline exponent
- `Di` = Initial nominal decline rate

**The Issue:**
1. When fitting with t=[1,2,3,...], the optimizer finds `Qi` that makes the curve pass through the data points
2. But this `Qi` is actually the rate at t=1, not t=0
3. When visualizing with t=[0,1,2,...], the curve evaluates q(0)=Qi, which is incorrect
4. This causes the entire curve to be **shifted and misaligned** with the actual data

### Standard ARPS Practice

According to petroleum engineering standards (SPE guidelines):
- **Time must start at t=0** for the first production data point
- The parameter `Qi` represents the production rate at t=0 (time zero)
- Subsequent time points are t=1, t=2, etc. (months after first production)

## Files Fixed

### 1. `/play_assesments_tools/python files/arps_autofit_csv.py`
**Line 188** - Changed from:
```python
t_act = df['Date'].rank(method='min', ascending=True).to_numpy()
```
To:
```python
# CRITICAL FIX: Time must start at 0 for ARPS equations (not 1)
# This ensures consistency with visualization and standard ARPS practice
t_act = df['Date'].rank(method='min', ascending=True).to_numpy() - 1
```

### 2. `/play_assesments_tools/Jupyter Notebooks/arps_autofit.ipynb`
**Cell 9** - Applied the same fix to the notebook version of the fitting function

### 3. `/play_assesments_tools/python files/arps_autofit.py`
**Line 508** - Already correct! Uses:
```python
t_act = (df['MonthsProducing'] - df['MonthsProducing'].iloc[0]).to_numpy(dtype=float)
```
This naturally creates zero-based time indexing.

## Impact

### Before Fix
- ARPS curves appeared to not fit the data well
- Curves were systematically offset from actual production points
- R² values were artificially lower than they should be
- Forecasts were unreliable

### After Fix
- ARPS curves will properly align with production data
- Initial rate (Qi) correctly represents rate at first production point
- R² values will accurately reflect goodness of fit
- Forecasts will be more reliable and accurate

## Testing Recommendations

1. **Re-run curve fitting** on existing wells to get corrected parameters
2. **Compare R² values** - should see improvement in fit quality
3. **Visual inspection** - curves should now pass through data points correctly
4. **Validate forecasts** - compare new forecasts against historical performance

## Technical Details

### ARPS Equation Forms

**Exponential Decline:**
```
q(t) = Qi * exp(-D * t)
```

**Hyperbolic Decline:**
```
q(t) = Qi / (1 + b * Di * t)^(1/b)
```

**Harmonic Decline (b=1):**
```
q(t) = Qi / (1 + Di * t)
```

In all forms, `t=0` corresponds to the initial rate `Qi`.

### Time Conversion
The code uses monthly time steps:
- t=0: First production month
- t=1: Second production month (1 month after start)
- t=n: (n+1)th production month

The decline rates (Di, Dei, Def) are expressed as **effective annual decline rates**, which are converted to nominal rates internally using:
```
Dn = (1/b) * ((1 - Dei)^(-b) - 1)
```

## Related Code

The visualization code in `visualization_utils.py` correctly uses zero-based indexing:
```python
t_months = np.arange(0, len(actual_data) + forecast_months)
forecast = fcst.varps_decline(wellid, 1, result_row['Q3'], 
                               result_row['Dei'], def_val, 
                               result_row['b_factor'], t_months, 0, 0)
```

The core ARPS function `arps_decline()` in `prod_fcst_functions.py` expects zero-based time.

## Date
Fixed: November 19, 2024

## References
- Society of Petroleum Engineers (SPE) - Decline Curve Analysis Standards
- Arps, J.J. (1945). "Analysis of Decline Curves". Transactions of the AIME, 160(01), 228-247.
