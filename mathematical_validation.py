"""
Mathematical Validation of ARPS Decline Curve Implementation
Based on fundamental ARPS theory and equations
"""

import numpy as np
import pandas as pd
import sys
sys.path.append('/Users/vhoisington/Desktop/Project1/Petroleum-main')
import AnalyticsAndDBScripts.prod_fcst_functions as fcst
import warnings
warnings.filterwarnings('ignore')

def validate_arps_fundamentals(qi, dei, def_val, b, t_months):
    """
    Validate ARPS implementation against fundamental mathematical properties
    
    Based on Arps (1945) decline equations:
    - Hyperbolic: q(t) = Qi / (1 + b * Di * t)^(1/b)
    - At t=0: q(0) must equal Qi
    - Decline rate must decrease over time (for hyperbolic)
    - Modified hyperbolic switches to exponential at terminal decline
    """
    
    print("="*70)
    print("MATHEMATICAL VALIDATION OF ARPS IMPLEMENTATION")
    print("="*70)
    
    # Generate decline curve
    results = fcst.varps_decline(1, 1, qi, dei, def_val, b, t_months, 0, 0)
    uid, phase, t_out, q_out, de_out, np_out = results
    
    print(f"\nInput Parameters:")
    print(f"  Qi (initial rate): {qi:.2f}")
    print(f"  Dei (initial effective decline): {dei:.4f} ({dei*100:.2f}%/year)")
    print(f"  Def (terminal decline): {def_val:.4f} ({def_val*100:.2f}%/year)")
    print(f"  b-factor: {b:.4f}")
    print(f"  Time points: {len(t_months)}")
    
    # TEST 1: Verify q(0) = Qi
    print("\n" + "-"*70)
    print("TEST 1: Initial Rate Validation")
    print("-"*70)
    q_at_t0 = q_out[0] if len(q_out) > 0 else None
    t_at_0 = t_out[0] if len(t_out) > 0 else None
    
    print(f"Expected: q(0) = Qi = {qi:.4f}")
    print(f"Actual:   q({t_at_0}) = {q_at_t0:.4f}")
    
    error_pct = abs(q_at_t0 - qi) / qi * 100
    print(f"Error: {error_pct:.6f}%")
    
    if error_pct < 0.01:
        print("✓ PASS: q(0) = Qi (within 0.01%)")
        test1_pass = True
    else:
        print("✗ FAIL: q(0) ≠ Qi")
        test1_pass = False
    
    # TEST 2: Verify decline rate behavior
    print("\n" + "-"*70)
    print("TEST 2: Decline Rate Behavior")
    print("-"*70)
    
    # Calculate nominal decline from effective
    if b > 0:
        dn_initial = (1/b) * ((1 - dei)**(-b) - 1)
    else:
        dn_initial = -np.log(1 - dei)
    
    print(f"Initial nominal decline (Di): {dn_initial:.4f}")
    print(f"Initial effective decline (Dei): {dei:.4f}")
    print(f"Terminal effective decline (Def): {def_val:.4f}")
    
    # Check first few decline rates
    print(f"\nDecline rate progression:")
    print(f"{'Month':<8} {'Rate':<12} {'Eff Decline':<15} {'Expected':<15}")
    print("-"*70)
    
    test2_pass = True
    for i in range(min(5, len(t_out))):
        # Expected decline rate at time t for hyperbolic
        t_years = t_out[i] / 12
        if b > 0 and b != 1:
            dn_t = dn_initial / (1 + b * dn_initial * t_years)
            de_expected = 1 - (1 / ((dn_t * b) + 1))**(1/b)
        elif b == 1:  # Harmonic
            dn_t = dn_initial / (1 + dn_initial * t_years)
            de_expected = 1 - (1 / (dn_t + 1))
        else:  # Exponential
            de_expected = dei
        
        print(f"{t_out[i]:<8.0f} {q_out[i]:<12.2f} {de_out[i]:<15.4f} {de_expected:<15.4f}")
        
        # Verify decline rate is decreasing (for hyperbolic)
        if i > 0 and b > 0:
            if de_out[i] > de_out[i-1]:
                print(f"  ✗ WARNING: Decline rate increased at month {t_out[i]}")
                test2_pass = False
    
    if test2_pass:
        print("✓ PASS: Decline rates behave correctly")
    
    # TEST 3: Verify hyperbolic equation at specific points
    print("\n" + "-"*70)
    print("TEST 3: Hyperbolic Equation Verification")
    print("-"*70)
    print("Verifying: q(t) = Qi / (1 + b * Di * t)^(1/b)")
    
    test3_pass = True
    test_points = [0, 1, 6, 12] if len(t_out) >= 12 else [0, 1]
    
    for t_month in test_points:
        if t_month >= len(t_out):
            continue
            
        idx = t_month
        t_years = t_month / 12
        
        # Calculate expected rate using ARPS equation
        if b > 0:
            q_expected = qi / (1 + b * dn_initial * t_years)**(1/b)
        else:
            q_expected = qi * np.exp(-dn_initial * t_years)
        
        q_actual = q_out[idx]
        error = abs(q_actual - q_expected) / q_expected * 100
        
        print(f"t={t_month:2d} months: Expected={q_expected:8.2f}, Actual={q_actual:8.2f}, Error={error:6.3f}%")
        
        if error > 1.0:  # Allow 1% tolerance
            test3_pass = False
    
    if test3_pass:
        print("✓ PASS: Hyperbolic equation verified")
    else:
        print("✗ FAIL: Hyperbolic equation mismatch")
    
    # TEST 4: Verify cumulative production
    print("\n" + "-"*70)
    print("TEST 4: Cumulative Production Validation")
    print("-"*70)
    
    # Calculate cumulative using trapezoidal integration
    if len(t_out) > 1:
        # Convert months to days for integration
        t_days = t_out * (365.25 / 12)
        cum_trapz = np.trapz(q_out, t_days)
        
        cum_arps = np_out[-1] if len(np_out) > 0 else 0
        
        print(f"Cumulative (ARPS function): {cum_arps:,.0f}")
        print(f"Cumulative (trapezoidal):   {cum_trapz:,.0f}")
        
        error_cum = abs(cum_arps - cum_trapz) / cum_arps * 100 if cum_arps > 0 else 0
        print(f"Difference: {error_cum:.2f}%")
        
        if error_cum < 5.0:  # Allow 5% tolerance for numerical integration
            print("✓ PASS: Cumulative production reasonable")
            test4_pass = True
        else:
            print("✗ FAIL: Cumulative production mismatch")
            test4_pass = False
    else:
        test4_pass = True
    
    # TEST 5: Verify modified hyperbolic transition
    print("\n" + "-"*70)
    print("TEST 5: Modified Hyperbolic Transition")
    print("-"*70)
    
    # Find where decline switches to exponential
    transition_idx = None
    for i in range(len(de_out)):
        if np.isclose(de_out[i], def_val, rtol=0.01):
            transition_idx = i
            break
    
    if transition_idx is not None:
        print(f"Transition to exponential at month {t_out[transition_idx]:.0f}")
        print(f"Rate at transition: {q_out[transition_idx]:.2f}")
        print(f"Decline at transition: {de_out[transition_idx]:.4f}")
        
        # After transition, decline should be constant
        if transition_idx < len(de_out) - 1:
            decline_after = de_out[transition_idx:]
            decline_constant = np.allclose(decline_after, def_val, rtol=0.01)
            
            if decline_constant:
                print("✓ PASS: Decline constant after transition")
                test5_pass = True
            else:
                print("✗ FAIL: Decline not constant after transition")
                test5_pass = False
        else:
            test5_pass = True
    else:
        print("No transition to exponential (decline stays above terminal)")
        test5_pass = True
    
    # TEST 6: Verify time consistency
    print("\n" + "-"*70)
    print("TEST 6: Time Array Consistency")
    print("-"*70)
    
    print(f"Input time array: {t_months[:5]}... (first 5)")
    print(f"Output time array: {t_out[:5]}... (first 5)")
    
    time_match = np.allclose(t_months, t_out)
    
    if time_match:
        print("✓ PASS: Time arrays match")
        test6_pass = True
    else:
        print("✗ FAIL: Time arrays don't match")
        test6_pass = False
    
    # SUMMARY
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    tests = {
        "Initial Rate (q(0) = Qi)": test1_pass,
        "Decline Rate Behavior": test2_pass,
        "Hyperbolic Equation": test3_pass,
        "Cumulative Production": test4_pass,
        "Modified Hyperbolic": test5_pass,
        "Time Consistency": test6_pass
    }
    
    for test_name, passed in tests.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:<30} {status}")
    
    all_pass = all(tests.values())
    
    print("="*70)
    if all_pass:
        print("✓✓✓ ALL TESTS PASSED - ARPS IMPLEMENTATION IS CORRECT ✓✓✓")
    else:
        print("✗✗✗ SOME TESTS FAILED - REVIEW IMPLEMENTATION ✗✗✗")
    print("="*70)
    
    return all_pass, tests


def validate_fitted_curve(df_well, qi_fit, dei_fit, b_fit, def_val=0.06):
    """
    Validate a fitted ARPS curve against actual production data
    """
    
    print("\n\n" + "="*70)
    print("FITTED CURVE VALIDATION")
    print("="*70)
    
    # Prepare data
    t_act = df_well['Date'].rank(method='min', ascending=True).to_numpy() - 1
    q_act = df_well['Value'].to_numpy()
    
    # Generate predictions
    q_pred = fcst.varps_decline(1, 1, qi_fit, dei_fit, def_val, b_fit, t_act, 0, 0)[3]
    
    print(f"\nFitted Parameters:")
    print(f"  Qi: {qi_fit:.2f}")
    print(f"  Dei: {dei_fit:.4f}")
    print(f"  b: {b_fit:.4f}")
    
    # TEST 1: First point validation
    print("\n" + "-"*70)
    print("TEST 1: First Point Alignment")
    print("-"*70)
    
    error_first = abs(q_pred[0] - q_act[0]) / q_act[0] * 100
    print(f"q_actual[0]: {q_act[0]:.2f}")
    print(f"q_pred[0]:   {q_pred[0]:.2f}")
    print(f"Error:       {error_first:.2f}%")
    
    if error_first < 10:
        print("✓ PASS: First point within 10%")
        test1 = True
    else:
        print("✗ FAIL: First point error > 10%")
        test1 = False
    
    # TEST 2: Residual analysis
    print("\n" + "-"*70)
    print("TEST 2: Residual Analysis")
    print("-"*70)
    
    residuals = q_act - q_pred
    mean_residual = np.mean(residuals)
    std_residual = np.std(residuals)
    
    print(f"Mean residual:   {mean_residual:.4f}")
    print(f"Std residual:    {std_residual:.4f}")
    print(f"Max residual:    {np.max(np.abs(residuals)):.4f}")
    
    # Check for systematic bias
    if abs(mean_residual) < std_residual * 0.5:
        print("✓ PASS: No systematic bias detected")
        test2 = True
    else:
        print("✗ WARNING: Possible systematic bias")
        test2 = False
    
    # TEST 3: Goodness of fit
    print("\n" + "-"*70)
    print("TEST 3: Goodness of Fit Metrics")
    print("-"*70)
    
    r2, rmse, mae = fcst.calc_goodness_of_fit(q_act, q_pred)
    
    print(f"R²:   {r2:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    
    if r2 > 0.85:
        print("✓ PASS: R² > 0.85 (good fit)")
        test3 = True
    elif r2 > 0.70:
        print("⚠ ACCEPTABLE: R² > 0.70 (acceptable fit)")
        test3 = True
    else:
        print("✗ FAIL: R² < 0.70 (poor fit)")
        test3 = False
    
    # TEST 4: Decline trend validation
    print("\n" + "-"*70)
    print("TEST 4: Decline Trend Validation")
    print("-"*70)
    
    # Check if predicted rates are generally declining
    declining = True
    for i in range(1, len(q_pred)):
        if q_pred[i] > q_pred[i-1] * 1.05:  # Allow 5% increase for noise
            declining = False
            print(f"✗ Rate increased at month {t_act[i]}: {q_pred[i-1]:.2f} → {q_pred[i]:.2f}")
            break
    
    if declining:
        print("✓ PASS: Predicted rates show declining trend")
        test4 = True
    else:
        print("✗ FAIL: Predicted rates not consistently declining")
        test4 = False
    
    print("\n" + "="*70)
    print("FITTED CURVE VALIDATION SUMMARY")
    print("="*70)
    
    tests = {
        "First Point Alignment": test1,
        "Residual Analysis": test2,
        "Goodness of Fit": test3,
        "Decline Trend": test4
    }
    
    for test_name, passed in tests.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:<30} {status}")
    
    all_pass = all(tests.values())
    print("="*70)
    
    return all_pass, tests, r2, rmse


def main():
    """Run comprehensive mathematical validation"""
    
    # Test 1: Validate ARPS function with known parameters
    print("\n" + "#"*70)
    print("# PART 1: VALIDATE ARPS FUNCTION IMPLEMENTATION")
    print("#"*70)
    
    # Use typical parameters
    qi = 600.0
    dei = 0.15  # 15% annual effective decline
    def_val = 0.06  # 6% terminal decline
    b = 0.9
    t_months = np.arange(0, 60)  # 5 years
    
    func_pass, func_tests = validate_arps_fundamentals(qi, dei, def_val, b, t_months)
    
    # Test 2: Validate fitted curve on real data
    print("\n\n" + "#"*70)
    print("# PART 2: VALIDATE FITTED CURVE ON REAL DATA")
    print("#"*70)
    
    # Load sample data
    df = pd.read_csv('sample_production_data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    well_id = 12345678901
    measure = 'GAS'
    
    df_well = df[(df['WellID'] == well_id) & (df['Measure'] == measure)].copy()
    df_well = df_well.sort_values('Date').reset_index(drop=True)
    
    # Fit curve with NEW method
    t_act = df_well['Date'].rank(method='min', ascending=True).to_numpy() - 1
    q_act = df_well['Value'].to_numpy()
    
    Qi_guess = q_act[0]
    Dei_guess = 0.15
    b_guess = 0.9
    
    bounds = ((Qi_guess*0.9, 0.05, 0.5), (Qi_guess*1.1, 0.30, 1.0))
    initial_guess = [Qi_guess, Dei_guess, b_guess]
    config = {'optimize': ['Qi', 'Dei', 'b'], 'fixed': {'Def': def_val}}
    
    result = fcst.perform_curve_fit(t_act, q_act, initial_guess, bounds, config, method='curve_fit')
    if isinstance(result, tuple) and len(result) > 1:
        qi_fit, dei_fit, b_fit = result[0]
    else:
        qi_fit, dei_fit, b_fit = result
    
    fit_pass, fit_tests, r2, rmse = validate_fitted_curve(df_well, qi_fit, dei_fit, b_fit, def_val)
    
    # Final summary
    print("\n\n" + "#"*70)
    print("# OVERALL VALIDATION SUMMARY")
    print("#"*70)
    
    print(f"\nARPS Function Implementation: {'✓ PASS' if func_pass else '✗ FAIL'}")
    print(f"Fitted Curve Validation:      {'✓ PASS' if fit_pass else '✗ FAIL'}")
    
    if func_pass and fit_pass:
        print("\n" + "="*70)
        print("✓✓✓ MATHEMATICAL VALIDATION COMPLETE - ALL TESTS PASSED ✓✓✓")
        print("="*70)
        print("\nThe ARPS decline curve implementation is mathematically correct")
        print("and properly fitted to the production data.")
    else:
        print("\n" + "="*70)
        print("✗✗✗ VALIDATION FAILED - REVIEW REQUIRED ✗✗✗")
        print("="*70)


if __name__ == "__main__":
    main()
