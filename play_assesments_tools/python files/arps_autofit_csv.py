"""
Arps Decline Curve Fitting - CSV Version

This script performs Arps decline curve analysis using CSV files instead of SQL database.
It's a simplified version of arps_autofit.py that works with local CSV data.
"""

import os
import sys
import pandas as pd
import numpy as np
import warnings
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from AnalyticsAndDBScripts.csv_loader import CSVDataLoader
from config.config_loader import get_config
import AnalyticsAndDBScripts.prod_fcst_functions as fcst
import AnalyticsAndDBScripts.arps_validation as arps_val
import warnings

warnings.filterwarnings('ignore')

# Determine config path
script_dir = Path(__file__).parent.parent.parent
config_path = script_dir / 'config' / 'analytics_config.yaml'

# Load configuration parameters
params_list = get_config('decline_curve', path=str(config_path))

arps_params = next((item for item in params_list if item['name'] == 'arps_parameters'), None)
bourdet_params = next((item for item in params_list if item['name'] == 'bourdet_outliers'), None)
changepoint_params = next((item for item in params_list if item['name'] == 'detect_changepoints'), None)
b_estimate_params = next((item for item in params_list if item['name'] == 'estimate_b'), None)
smoothing_params = next((item for item in params_list if item['name'] == 'smoothing'), None)
method_params = next((item for item in params_list if item['name'] == 'method'), None) or {}

# Extract parameters
value_col = 'Value'
fit_segment = changepoint_params['fit_segment']
general_params = method_params.get('general', {}) or {}
mc_config = method_params.get('monte_carlo', {}) or {}

trials = general_params.get('trials', 3000)
use_advi = bool(mc_config.get('use_advi', False))
save_trace = bool(mc_config.get('save_trace', False))
fit_months = general_params.get('fit_months', 120)

# Decline parameters
def_dict = arps_params['terminal_decline']
dei_dict1 = arps_params['initial_decline']
min_q_dict = arps_params['abandonment_rate']
default_b_dict = arps_params['b_factor']

# Output columns
param_df_cols = [
    'WellID', 'Measure', 'fit_months', 'fit_type', 'fit_segment', 'StartDate', 
    'StartMonth', 'Q_guess', 'Q3', 'Dei', 'b_factor', 'R_squared', 'RMSE', 'MAE'
]


def calc_months_producing(group):
    """Add MonthsProducing column to production data."""
    min_date = group['Date'].min()
    group['MonthsProducing'] = group['Date'].map(lambda x: fcst.MonthDiff(min_date, x))
    return group


def apply_bourdet_outliers(group, date_col, value_col):
    """Remove outliers from production data using Bourdet derivative."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        x = group[date_col].values
        y = group[value_col].values
        y_new, x_new = fcst.bourdet_outliers(
            y, 
            x, 
            L=bourdet_params['smoothing_factor'], 
            xlog=False, 
            ylog=True, 
            z_threshold=bourdet_params['z_threshold'], 
            min_array_size=bourdet_params['min_array_size']
        )
        mask = group[date_col].isin(x_new)
        group = group.loc[mask].copy()
        group.loc[:, value_col] = y_new
    return group


def create_b_dict(b_low, b_avg, b_high, min_b=0.5, max_b=1.4):
    """Create b-factor dictionary from estimated values."""
    b_low = max(b_low if pd.notnull(b_low) else min_b, min_b)
    b_high = min(max(b_high if pd.notnull(b_high) else max_b, b_low * 1.1), max_b)
    
    if pd.isnull(b_avg) or b_avg < b_low or b_avg > b_high:
        b_avg = (b_low + b_high) / 2
    
    return {
        'min': round(b_low, 4),
        'guess': round(b_avg, 4),
        'max': round(b_high, 4)
    }


def fit_arps_curve(
    property_id, 
    phase, 
    b_dict, 
    dei_dict, 
    def_dict, 
    min_q_dict, 
    prod_df_cleaned, 
    value_col, 
    method='curve_fit', 
    trials=1000, 
    fit_segment='all', 
    smoothing_factor=2
):
    """
    Fit Arps decline curve to production data.
    
    Args:
        property_id: Well ID
        phase: Product type (OIL, GAS, WATER)
        b_dict: b-factor bounds and guess
        dei_dict: Initial decline rate bounds
        def_dict: Terminal decline rates by phase
        min_q_dict: Abandonment rates by phase
        prod_df_cleaned: Production DataFrame
        value_col: Column name for production values
        method: Fitting method
        trials: Number of iterations for optimization
        fit_segment: Which segment to fit
        smoothing_factor: Smoothing iterations
        
    Returns:
        List with fitted parameters and goodness of fit metrics
    """
    
    def dict_coalesce(dei_dict, def_dict):
        return dei_dict.get('min', def_dict[phase])

    # Filter data for this well/phase
    df = prod_df_cleaned[
        (prod_df_cleaned['WellID'] == property_id) & 
        (prod_df_cleaned[value_col] > 0) &
        (prod_df_cleaned['Measure'] == phase)
    ].sort_values(by='Date')

    df['month_int'] = df['Date'].rank(method='dense', ascending=True)
    min_length = 12

    # Select segment
    if len(df) <= min_length:
        df_selected = df
    else:
        unique_segments = sorted(df['segment'].unique())
        df_selected = pd.DataFrame()
        
        if fit_segment == 'first':
            segment_index = 0
            df_selected = df[df['segment'] == unique_segments[segment_index]]
            
            while len(df_selected) < min_length and segment_index + 1 < len(unique_segments):
                segment_index += 1
                next_segment_df = df[df['segment'] == unique_segments[segment_index]]
                df_selected = pd.concat([df_selected, next_segment_df])
            
        elif fit_segment == 'last':
            segment_index = len(unique_segments) - 1
            df_selected = df[df['segment'] == unique_segments[segment_index]]
            
            while len(df_selected) < min_length and segment_index - 1 >= 0:
                segment_index -= 1
                prev_segment_df = df[df['segment'] == unique_segments[segment_index]]
                df_selected = pd.concat([prev_segment_df, df_selected])
                
        if len(df_selected) < min_length:
            df_selected = df

    # Prepare fitting data (DO NOT drop first row - it's t=0!)
    df = df_selected.reset_index(drop=True)

    # Prepare fitting data
    arr_length = len(df)
    # CRITICAL: Time must start at 0 for ARPS equations
    # t=0 corresponds to the FIRST data point, where q(0) = Qi
    t_act = df['Date'].rank(method='min', ascending=True).to_numpy() - 1
    q_act = df[value_col].to_numpy()
    start_date = df['Date'].min()
    start_month = df['month_int'].min()
    # Qi should be the rate at t=0 (first point), not the maximum
    Qi_guess = q_act[0]  # Rate at first data point (t=0)
    Dei_init = dei_dict['guess']
    Dei_min = dict_coalesce(dei_dict, def_dict)
    Dei_max = dei_dict['max']
    b_guess = b_dict['guess']

    b_min = min(b_dict['min'], b_dict['max'])
    b_max = max(b_dict['min'], b_dict['max'])

    def auto_fit1(method=method):
        # CRITICAL: Qi should be FIXED at first data point, not optimized
        # Optimizing Qi violates ARPS theory: q(0) must equal the first actual rate
        bounds = ((Dei_min, b_min), (Dei_max, b_max))
        initial_guess = [Dei_init, b_guess]
        config_optimize_dei_b = {
            'optimize': ['Dei', 'b'],
            'fixed': {'Qi': Qi_guess, 'Def': def_dict[phase]}
        }
        result = fcst.perform_curve_fit(
            t_act, q_act, initial_guess, bounds, 
            config_optimize_dei_b, method=method, trials=trials
        )
        # Handle different return formats
        if isinstance(result, tuple):
            optimized_params = result[0] if len(result) > 1 else result
        else:
            optimized_params = result
        Dei_fit, b_fit = optimized_params
        qi_fit = Qi_guess  # Qi is fixed, not optimized
        q_pred = fcst.varps_decline(1, 1, qi_fit, Dei_fit, def_dict[phase], b_fit, t_act, 0, 0)[3]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            r_squared, rmse, mae = fcst.calc_goodness_of_fit(q_act, q_pred)
        
        # COMPREHENSIVE VALIDATION: Validate ARPS curve fit
        validation_results = arps_val.validate_arps_fit(
            t_act, q_act, q_pred, qi_fit, Dei_fit, b_fit, def_dict[phase],
            well_id=property_id, phase=phase, strict_mode=False
        )

        return [
            property_id, phase, arr_length, 'auto_fit_1', fit_segment, start_date, start_month, 
            Qi_guess, qi_fit, Dei_fit, b_fit, r_squared, rmse, mae
        ]
    
    def auto_fit2(method=method):
        initial_guess = [Dei_init]
        bounds = ((Dei_min, Dei_max))
        config_optimize_dei = {
            'optimize': ['Dei'],
            'fixed': {'Qi': Qi_guess, 'b': b_guess, 'Def': def_dict[phase]}
        }
        result = fcst.perform_curve_fit(
            t_act, q_act, initial_guess, bounds, 
            config_optimize_dei, method=method, trials=trials
        )
        # Handle different return formats
        if isinstance(result, tuple):
            optimized_params = result[0] if len(result) > 1 else result
        else:
            optimized_params = result
        Dei_fit = optimized_params[0]
        q_pred = fcst.varps_decline(1, 1, Qi_guess, Dei_fit, def_dict[phase], b_dict['guess'], t_act, 0, 0)[3]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            r_squared, rmse, mae = fcst.calc_goodness_of_fit(q_act, q_pred)
        
        # COMPREHENSIVE VALIDATION: Validate ARPS curve fit
        validation_results = arps_val.validate_arps_fit(
            t_act, q_act, q_pred, Qi_guess, Dei_fit, b_dict['guess'], def_dict[phase],
            well_id=property_id, phase=phase, strict_mode=False
        )

        return [
            property_id, phase, arr_length, 'auto_fit_2', fit_segment, start_date, start_month, 
            Qi_guess, Qi_guess, Dei_fit, b_guess, r_squared, rmse, mae
        ]
    
    def auto_fit3():      
        return [
            property_id, phase, arr_length, 'auto_fit_3', fit_segment, start_date, start_month, 
            Qi_guess, Qi_guess, max(Dei_init, def_dict[phase]), b_guess, np.nan, np.nan, np.nan
        ]
    
    # Select fitting strategy based on data quality
    if (Qi_guess < min_q_dict[phase]) or (arr_length < 3.0):
        result = auto_fit3()
    elif arr_length < 7.0:
        try:
            result = auto_fit2()
        except Exception as e:
            print(f"  Failed auto_fit2 with error {e}, falling back to auto_fit3")
            result = auto_fit3()
    else:
        # Apply smoothing
        q_act_series = pd.Series(q_act)
        if smoothing_factor > 0:
            for i in range(smoothing_factor):
                q_act_series = q_act_series.rolling(window=3, min_periods=1).mean()
        
        q_act = q_act_series.to_numpy()
        # CRITICAL: Qi must be the FIRST smoothed value, not the maximum
        # This ensures q(0) = Qi as required by ARPS theory
        Qi_guess = q_act[0]
        
        try:
            result = auto_fit1()
        except Exception as e1:
            try:
                print(f"  Failed auto_fit1 with error {e1}, trying auto_fit2")
                result = auto_fit2()
            except Exception as e2:
                print(f"  Failed auto_fit2 with error {e2}, falling back to auto_fit3")
                result = auto_fit3()
    
    return result


def fit_aggregate_arps_curve(
    measure,
    b_dict,
    dei_dict,
    def_dict,
    min_q_dict,
    prod_df_all_wells,
    value_col,
    method='curve_fit',
    trials=1000,
    smoothing_factor=2
):
    """
    Fit Arps decline curve to AGGREGATED production from multiple wells.
    
    This creates a "type curve" by averaging production across all wells
    by time period, then fitting one ARPS curve to the averaged data.
    
    Args:
        measure: Product type (OIL, GAS, WATER)
        b_dict: b-factor bounds and guess
        dei_dict: Initial decline rate bounds
        def_dict: Terminal decline rates by phase
        min_q_dict: Abandonment rates by phase
        prod_df_all_wells: Production DataFrame with ALL wells
        value_col: Column name for production values
        method: Fitting method
        trials: Number of iterations for optimization
        smoothing_factor: Smoothing iterations
        
    Returns:
        Tuple: (result_list, aggregated_df)
            - result_list: Fitted parameters and metrics
            - aggregated_df: DataFrame with averaged production by month
    """
    
    def dict_coalesce(dei_dict, def_dict):
        return dei_dict.get('min', def_dict[measure])
    
    # Filter for this measure only
    df = prod_df_all_wells[
        (prod_df_all_wells[value_col] > 0) &
        (prod_df_all_wells['Measure'] == measure)
    ].copy()
    
    if df.empty:
        return None, None
    
    # Normalize time: assign month index starting from earliest date across all wells
    min_date = df['Date'].min()
    df['months_from_start'] = ((df['Date'] - min_date).dt.days / 30.42).astype(int)
    
    # Average production across all wells for each month
    # This is the key step for type curve analysis
    aggregated = df.groupby('months_from_start').agg({
        value_col: 'mean',  # Average production
        'WellID': 'count'   # Number of wells contributing
    }).reset_index()
    
    aggregated.rename(columns={
        value_col: 'avg_production',
        'WellID': 'well_count'
    }, inplace=True)
    
    # Prepare fitting data
    t_act = aggregated['months_from_start'].to_numpy()
    q_act = aggregated['avg_production'].to_numpy()
    arr_length = len(t_act)
    
    if arr_length < 3:
        return None, aggregated
    
    # Apply smoothing
    if smoothing_factor > 0:
        q_act_series = pd.Series(q_act)
        for i in range(smoothing_factor):
            q_act_series = q_act_series.rolling(window=3, min_periods=1).mean()
        q_act = q_act_series.to_numpy()
    
    # Qi is the first averaged production value
    Qi_guess = q_act[0]
    Dei_init = dei_dict['guess']
    Dei_min = dict_coalesce(dei_dict, def_dict)
    Dei_max = dei_dict['max']
    b_guess = b_dict['guess']
    b_min = min(b_dict['min'], b_dict['max'])
    b_max = max(b_dict['min'], b_dict['max'])
    
    # Fit ARPS curve to aggregated data
    try:
        bounds = ((Dei_min, b_min), (Dei_max, b_max))
        initial_guess = [Dei_init, b_guess]
        config_optimize_dei_b = {
            'optimize': ['Dei', 'b'],
            'fixed': {'Qi': Qi_guess, 'Def': def_dict[measure]}
        }
        result = fcst.perform_curve_fit(
            t_act, q_act, initial_guess, bounds,
            config_optimize_dei_b, method=method, trials=trials
        )
        
        # Handle different return formats
        if isinstance(result, tuple):
            optimized_params = result[0] if len(result) > 1 else result
        else:
            optimized_params = result
        
        Dei_fit, b_fit = optimized_params
        qi_fit = Qi_guess
        
        # CRITICAL ASSERTION: Verify Qi was not accidentally optimized
        assert qi_fit == Qi_guess, f"CRITICAL ERROR: Qi was modified! Expected {Qi_guess}, got {qi_fit}"
        
        # Calculate predicted values
        q_pred = fcst.varps_decline(1, 1, qi_fit, Dei_fit, def_dict[measure], b_fit, t_act, 0, 0)[3]
        
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            r_squared, rmse, mae = fcst.calc_goodness_of_fit(q_act, q_pred)
        
        # CRITICAL VALIDATION: Ensure ARPS curve is correct
        import AnalyticsAndDBScripts.arps_validation as arps_val
        validation_results = arps_val.validate_arps_fit(
            t_act, q_act, q_pred, qi_fit, Dei_fit, b_fit, def_dict[measure],
            well_id='AGGREGATE', phase=measure, strict_mode=False
        )
        
        # Check for critical validation failures
        if not validation_results['tests'].get('time_starts_at_zero', True):
            print(f"  ⚠️  VALIDATION WARNING: Time array does not start at zero for {measure}")
        
        first_point_test = validation_results['tests'].get('first_point_alignment', {})
        if isinstance(first_point_test, dict) and not first_point_test.get('pass', True):
            error_pct = first_point_test.get('error_pct', 0)
            print(f"  ⚠️  VALIDATION WARNING: First point mismatch for {measure}: {error_pct:.1f}% error")
            print(f"      q_actual(0)={first_point_test.get('q_actual_0', 0):.2f}, "
                  f"q_pred(0)={first_point_test.get('q_pred_0', 0):.2f}, "
                  f"Qi_fit={first_point_test.get('qi_fit', 0):.2f}")
        
        # Store aggregated data for visualization
        aggregated['predicted'] = q_pred
        
        result_list = [
            'AGGREGATE', measure, arr_length, 'aggregate_fit', 'all',
            min_date, 0, Qi_guess, qi_fit, Dei_fit, b_fit, r_squared, rmse, mae
        ]
        
        return result_list, aggregated
        
    except Exception as e:
        print(f"  Failed aggregate fit with error: {e}")
        return None, aggregated


def process_well_csv(
    wellid, 
    measure, 
    last_prod_date, 
    csv_loader,
    fit_method='curve_fit'
):
    """
    Process a single well using CSV data.
    
    Args:
        wellid: Well ID
        measure: Product type
        last_prod_date: Last production date
        csv_loader: CSVDataLoader instance
        fit_method: Fitting method to use
        
    Returns:
        List with fitted parameters
    """
    print(f"Processing Well {wellid} - {measure}...")
    
    # Load production data
    prod_df = csv_loader.get_well_production(
        wellid=wellid,
        measure=measure,
        last_prod_date=last_prod_date,
        fit_months=fit_months
    )

    if prod_df.empty:
        print(f"  No data found")
        return [wellid, measure, 0, 'no_data', np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
    
    # Add MonthsProducing column
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        prod_df = prod_df.groupby(['WellID', 'Measure']).apply(calc_months_producing)
        prod_df.reset_index(inplace=True, drop=True)
    
    # Apply Bourdet outliers
    if bourdet_params['setting']:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            grouped = prod_df.groupby(['WellID', 'Measure'])
            prod_df_cleaned = grouped.apply(apply_bourdet_outliers, 'MonthsProducing', value_col)
            prod_df_cleaned.reset_index(inplace=True, drop=True)
    else:
        prod_df_cleaned = prod_df.copy()

    # Detect changepoints
    if changepoint_params['setting']:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            cp_penalty = changepoint_params['penalty']
            prod_df_cleaned = prod_df_cleaned.groupby(['WellID']).apply(
                fcst.detect_changepoints, 'WellID', value_col, 'Date', cp_penalty
            )
            prod_df_cleaned.reset_index(inplace=True, drop=True)
    else:
        prod_df_cleaned['segment'] = 0

    # Estimate b factor
    if b_estimate_params['setting']:
        try:
            results = fcst.b_factor_diagnostics(prod_df_cleaned, value_col, 'MonthsProducing')
            b_dict = create_b_dict(results['b_low'], results['b_avg'], results['b_high'])
        except Exception:
            b_dict = default_b_dict[measure]
    else:
        b_dict = default_b_dict[measure]

    # Fit Arps curve
    result = fit_arps_curve(
        wellid, measure, b_dict, dei_dict1, def_dict, min_q_dict, 
        prod_df_cleaned, value_col, fit_method, trials, fit_segment, 
        smoothing_params['factor']
    )

    r2_val = result[11]
    r2_str = f"{r2_val:.3f}" if pd.notnull(r2_val) else "N/A"
    print(f"  ✓ Completed: R²={r2_str}")
    return result


def main(production_csv, well_list_csv=None, output_csv='arps_results_csv.csv'):
    """
    Main function to process wells from CSV files.
    
    Args:
        production_csv: Path to production data CSV
        well_list_csv: Optional path to well list CSV
        output_csv: Path for output results CSV
    """
    print("=" * 80)
    print("Arps Decline Curve Analysis - CSV Mode")
    print("=" * 80)
    
    # Initialize CSV loader
    print(f"\nInitializing CSV loader...")
    csv_loader = CSVDataLoader(production_csv, well_list_csv)
    
    # Load well list
    well_list_df = csv_loader.load_well_list()
    print(f"\nProcessing {len(well_list_df)} well/measure combinations...")
    
    # Process each well
    results = []
    for idx, row in well_list_df.iterrows():
        try:
            result = process_well_csv(
                wellid=row['WellID'],
                measure=row['Measure'],
                last_prod_date=row['LastProdDate'],
                csv_loader=csv_loader,
                fit_method=row.get('FitMethod', 'curve_fit')
            )
            results.append(result)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(results, columns=param_df_cols)
    
    # Save results
    results_df.to_csv(output_csv, index=False)
    print(f"\n{'=' * 80}")
    print(f"✅ Analysis complete!")
    print(f"   Processed: {len(results_df)} wells")
    print(f"   Successful fits: {(results_df['R_squared'] > 0.5).sum()}")
    print(f"   Results saved to: {output_csv}")
    print(f"{'=' * 80}")
    
    return results_df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Arps Decline Curve Analysis from CSV')
    parser.add_argument('production_csv', help='Path to production data CSV')
    parser.add_argument('--well-list', help='Optional path to well list CSV')
    parser.add_argument('--output', default='arps_results_csv.csv', help='Output CSV path')
    
    args = parser.parse_args()
    
    main(args.production_csv, args.well_list, args.output)
