# Deep Dive Research: ARPS Decline Curve Analysis

## Executive Summary

After extensive research into ARPS decline curve theory and implementation, I've identified several critical aspects that must be understood for correct implementation. The curve fitting issue may stem from multiple factors beyond just time indexing.

---

## 1. ARPS Fundamentals (J.J. Arps, 1945)

### Core Decline Types

**Exponential Decline (b = 0)**
- Decline rate is **constant** over time
- Equation: `q(t) = Qi * exp(-Di * t)`
- Linear on semi-log plot (log(q) vs t)
- Most conservative forecast

**Hyperbolic Decline (0 < b < 1)**
- Decline rate **decreases** over time
- Equation: `q(t) = Qi / (1 + b * Di * t)^(1/b)`
- Most common in real wells
- Can overestimate reserves if extrapolated too far

**Harmonic Decline (b = 1)**
- Special case of hyperbolic
- Equation: `q(t) = Qi / (1 + Di * t)`
- Most optimistic forecast

---

## 2. Critical Distinction: Nominal vs Effective Decline

### THIS IS CRUCIAL AND OFTEN MISUNDERSTOOD

**Nominal Decline Rate (Di or 'a')**
- **Instantaneous** decline rate
- Definition: `Di = -(1/q) * (dq/dt)`
- Used in ARPS equations directly
- Continuous compounding

**Effective Decline Rate (De or 'd')**
- **Period-based** decline rate (typically annual)
- Definition: `De = (q1 - q2) / q1` for a time period
- What engineers typically report
- Discrete compounding

**Conversion (EXPONENTIAL ONLY)**
```
De = 1 - exp(-Di)
Di = -ln(1 - De)
```

**⚠️ WARNING**: This conversion ONLY works for exponential decline!

For hyperbolic decline, the relationship is more complex:
```
Di(t) = Di0 / (1 + b * Di0 * t)  [nominal at time t]
De(t) = 1 - (1 / (Di(t) * b + 1))^(1/b)  [effective at time t]
```

---

## 3. Time Indexing in ARPS Equations

### Standard Practice

**Time MUST start at t=0** for the first data point where:
- `q(0) = Qi` (initial rate at time zero)
- `t` is measured in **months** (or years, consistently)
- Subsequent points: t=1, t=2, t=3, etc.

### Why t=0 Matters

The ARPS hyperbolic equation:
```
q(t) = Qi / (1 + b * Di * t)^(1/b)
```

At t=0:
```
q(0) = Qi / (1 + 0)^(1/b) = Qi
```

This is the **definition** of Qi - it's the rate at time zero!

If you fit with t=[1,2,3,...] but visualize with t=[0,1,2,...]:
- The fitted Qi is actually q(1), not q(0)
- The curve will be systematically offset
- R² will be artificially lower

---

## 4. Modified Hyperbolic Decline

### The Problem with Pure Hyperbolic

Pure hyperbolic decline can predict **unrealistically high reserves** when extrapolated far into the future because the decline rate approaches zero.

### Solution: Transition to Exponential

**Modified Hyperbolic** (also called "Limited Decline"):
1. Start with hyperbolic decline at high initial decline rate
2. When decline rate reaches a **terminal decline** (Def), switch to exponential
3. Continue with constant exponential decline

**Implementation**:
```python
if De_current > Def:
    # Use hyperbolic
    q = Qi / (1 + b * Di * t)^(1/b)
else:
    # Switch to exponential at tlim
    q = Qlim * exp(-Dmin * (t - tlim))
```

Where:
- `Def` = Terminal effective decline (typically 5-10% for gas, 8-10% for oil)
- `Qlim` = Rate when switching occurs
- `tlim` = Time when switching occurs

---

## 5. Your Implementation Analysis

### What Your Code Does

Looking at `prod_fcst_functions.py`:

```python
# Line 62-64: Calculate nominal decline
Dn = (1 / b) * (((1 - Dei) ** -b) - 1)

# Line 71: Hyperbolic equation
q = Qi * (1 + b * Dn * (t / 12)) ** (-1 / b)
```

**Key Observations**:

1. **Time Units**: Your code divides `t` by 12, suggesting `t` is in months but the equation expects years
2. **Decline Conversion**: You're converting effective decline (Dei) to nominal (Dn)
3. **Modified Hyperbolic**: You correctly implement the switch to exponential at Def

### The Conversion Formula

```python
Dn = (1 / b) * (((1 - Dei) ** -b) - 1)
```

This converts **effective annual decline** to **nominal decline** for hyperbolic curves.

**Derivation**:
```
De = 1 - (1 / (1 + b * Dn))^(1/b)
Solving for Dn:
(1 - De)^(-b) = 1 + b * Dn
Dn = (1/b) * ((1 - De)^(-b) - 1)
```

This is **correct** for hyperbolic decline!

---

## 6. Potential Issues Beyond Time Indexing

### Issue 1: Time Units Inconsistency

Your equation uses `(t / 12)` which suggests:
- `t` is in **months**
- Equation expects **years**
- `Dn` must be in **per year** units

**Check**: Are your decline rates (Dei, Def) expressed as:
- Annual rates? (e.g., 0.15 = 15% per year) ✓
- Monthly rates? (e.g., 0.0125 = 1.25% per month) ✗

### Issue 2: Initial Rate (Qi) Definition

**Critical Question**: What is Qi in your fitted results?

From `test_results.csv`:
- Well 12345678901 GAS: Q3 = 17.28, Q_guess = 17.28

The column is named `Q3` not `Qi`. This suggests:
- Q3 might be the rate at the **3rd month** or **end of ramp-up**
- If Q3 ≠ q(0), the entire curve will be wrong

**Standard Practice**:
- Qi = rate at **first production month** (t=0)
- Or rate at **peak** if there's a ramp-up period
- Must be clearly defined

### Issue 3: Segment Selection

From your results: `fit_segment = 'last'`

This means you're fitting to the **last segment** after changepoint detection.

**Potential Problem**:
- If the last segment starts at month 6, but you use t=[0,1,2,...]
- The time array doesn't match the actual time since first production
- The curve thinks it's fitting from t=0 but it's actually t=6

**Solution**: Time should be **relative to the segment start**, not absolute.

### Issue 4: Data Preprocessing

From `arps_autofit_csv.py` line 182:
```python
df = df_selected.reset_index(drop=True).iloc[1:]
```

You're **dropping the first row** for noise reduction!

**Impact**:
- If you drop the first row, then use t=[0,1,2,...]
- t=0 corresponds to the **second** data point
- But Qi is fitted to match t=0
- The curve will be offset by one month

---

## 7. Diagnostic Checks

### Check 1: Verify Time Array

```python
print("Time array:", t_act[:5])
print("Rate array:", q_act[:5])
print("Expected q(0):", Qi_fit)
print("Actual first rate:", q_act[0])
```

**Expected**: `q_act[0]` should be very close to `Qi_fit`

### Check 2: Verify Decline Conversion

```python
# For first few months
for i in range(5):
    q_pred = Qi_fit / (1 + b_fit * Dn * (t_act[i] / 12))**(1/b_fit)
    print(f"t={t_act[i]}: q_actual={q_act[i]:.2f}, q_pred={q_pred:.2f}")
```

**Expected**: Predictions should closely match actuals for good fit

### Check 3: Verify Units

```python
print("Dei (effective annual):", Dei_fit)
print("Dn (nominal):", Dn)
print("Time units:", "months" if max(t_act) > 12 else "years")
```

### Check 4: Check Segment Timing

```python
print("Segment start date:", start_date)
print("First data date:", actual_data['Date'].min())
print("Time offset:", (start_date - actual_data['Date'].min()).days / 30)
```

---

## 8. Recommendations

### Immediate Actions

1. **Verify time starts at 0** (you've done this)
2. **Don't drop the first row** if using t=0 indexing
3. **Ensure Qi represents q(0)** not q(1) or q(3)
4. **Check segment timing** - time should be relative to segment start
5. **Verify decline rate units** - must be annual effective rates

### Best Practices

1. **Always plot** actual vs predicted on both linear and log scales
2. **Check residuals** - should be randomly distributed
3. **Validate on holdout data** - fit on 80%, test on 20%
4. **Use modified hyperbolic** - always set a terminal decline
5. **Document assumptions** - time units, rate units, Qi definition

### Alternative Approach

If issues persist, consider:

**Rate-Normalized Time**:
```python
# Instead of calendar time
t_normalized = np.cumsum(1 / q_act)  # Dimensionless time
```

This can be more stable for noisy data.

---

## 9. Mathematical Verification

### Correct Hyperbolic Implementation

```python
def arps_hyperbolic(t_months, Qi, Dei_eff, Def_eff, b):
    """
    ARPS hyperbolic decline with modified tail
    
    Parameters:
    - t_months: Time in months, starting at 0
    - Qi: Initial rate at t=0
    - Dei_eff: Initial effective annual decline rate
    - Def_eff: Terminal effective annual decline rate
    - b: Hyperbolic exponent (0 < b < 1)
    
    Returns:
    - q: Production rate at time t
    """
    # Convert effective to nominal (annual)
    Di_nom = (1/b) * ((1 - Dei_eff)**(-b) - 1)
    Dmin_nom = -np.log(1 - Def_eff)
    
    # Convert to daily for calculation
    Di_day = Di_nom / 365.25
    Dmin_day = Dmin_nom / 365.25
    
    # Time in days
    t_days = t_months * (365.25 / 12)
    
    # Calculate transition time
    t_trans = (1/Dmin_day - 1/Di_day) / b
    
    # Calculate rate
    if t_days <= t_trans:
        # Hyperbolic phase
        q = Qi / (1 + b * Di_day * t_days)**(1/b)
    else:
        # Exponential tail
        q_trans = Qi / (1 + b * Di_day * t_trans)**(1/b)
        q = q_trans * np.exp(-Dmin_day * (t_days - t_trans))
    
    return q
```

### Key Points

1. **Time starts at 0**: First data point is t=0
2. **Qi is q(0)**: Initial rate at time zero
3. **Decline rates are annual**: Converted to daily for calculation
4. **Modified hyperbolic**: Switches to exponential at terminal decline
5. **Consistent units**: All conversions explicit

---

## 10. Conclusion

The ARPS curve fitting issue is likely **multifactorial**:

1. ✅ **Time indexing** - Fixed (t=0 instead of t=1)
2. ❓ **First row dropping** - May cause offset
3. ❓ **Qi definition** - Must be q(0), not q(3)
4. ❓ **Segment timing** - Time must be relative to segment
5. ❓ **Unit consistency** - Verify all rates are annual

**Next Steps**:
1. Run diagnostic checks above
2. Plot actual vs predicted for visual inspection
3. Check if removing `.iloc[1:]` improves fit
4. Verify Qi equals first data point rate
5. Ensure time is relative to segment start, not absolute

The theory is sound, but implementation details matter enormously in decline curve analysis.
