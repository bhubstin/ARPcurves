"""
Visual Validation of ARPS Curve Fitting Fixes
Compares OLD method (wrong) vs NEW method (correct)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
sys.path.append('/Users/vhoisington/Desktop/Project1/Petroleum-main')
import AnalyticsAndDBScripts.prod_fcst_functions as fcst
import warnings
warnings.filterwarnings('ignore')

# Set plot style
plt.style.use('seaborn-v0_8-darkgrid')

def fit_arps_old_method(df_well, def_val=0.06):
    """OLD METHOD (WRONG): Drops first row, uses max as Qi"""
    # Drop first row (OLD METHOD)
    df_fit = df_well.iloc[1:].reset_index(drop=True)
    
    t_act = df_fit['Date'].rank(method='min', ascending=True).to_numpy() - 1
    q_act = df_fit['Value'].to_numpy()
    
    Qi_guess = np.max(q_act)  # OLD: use max
    Dei_guess = 0.15
    b_guess = 0.9
    
    print("\n" + "="*60)
    print("OLD METHOD (WRONG):")
    print("="*60)
    print(f"First row dropped: YES")
    print(f"Time array starts at: {t_act[0]}")
    print(f"Qi_guess: {Qi_guess:.2f} (maximum of data)")
    print(f"First actual rate used: {q_act[0]:.2f}")
    print(f"Original first rate (dropped): {df_well['Value'].iloc[0]:.2f}")
    
    bounds = ((Qi_guess*0.9, 0.05, 0.5), (Qi_guess*1.1, 0.30, 1.0))
    initial_guess = [Qi_guess, Dei_guess, b_guess]
    config = {'optimize': ['Qi', 'Dei', 'b'], 'fixed': {'Def': def_val}}
    
    result = fcst.perform_curve_fit(t_act, q_act, initial_guess, bounds, config, method='curve_fit')
    # Handle different return formats (OLD METHOD)
    if isinstance(result, tuple) and len(result) > 1:
        qi_fit, dei_fit, b_fit = result[0]
    else:
        qi_fit, dei_fit, b_fit = result
    
    q_pred = fcst.varps_decline(1, 1, qi_fit, dei_fit, def_val, b_fit, t_act, 0, 0)[3]
    r2, rmse, mae = fcst.calc_goodness_of_fit(q_act, q_pred)
    
    print(f"\nFitted Parameters:")
    print(f"  Qi: {qi_fit:.2f}")
    print(f"  Dei: {dei_fit:.4f}")
    print(f"  b: {b_fit:.4f}")
    print(f"\nGoodness of Fit:")
    print(f"  R²: {r2:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  MAE: {mae:.4f}")
    
    return {
        't_act': t_act, 'q_act': q_act, 'q_pred': q_pred,
        'qi': qi_fit, 'dei': dei_fit, 'b': b_fit,
        'r2': r2, 'rmse': rmse, 'mae': mae
    }

def fit_arps_new_method(df_well, def_val=0.06):
    """NEW METHOD (CORRECT): Keeps all rows, uses first point as Qi"""
    # Keep all rows (NEW METHOD)
    df_fit = df_well.reset_index(drop=True)
    
    t_act = df_fit['Date'].rank(method='min', ascending=True).to_numpy() - 1
    q_act = df_fit['Value'].to_numpy()
    
    Qi_guess = q_act[0]  # NEW: use first point
    Dei_guess = 0.15
    b_guess = 0.9
    
    print("\n" + "="*60)
    print("NEW METHOD (CORRECT):")
    print("="*60)
    print(f"First row dropped: NO")
    print(f"Time array starts at: {t_act[0]}")
    print(f"Qi_guess: {Qi_guess:.2f} (first data point)")
    print(f"First actual rate used: {q_act[0]:.2f}")
    print(f"✓ Qi_guess == first rate: {np.isclose(Qi_guess, q_act[0])}")
    
    bounds = ((Qi_guess*0.9, 0.05, 0.5), (Qi_guess*1.1, 0.30, 1.0))
    initial_guess = [Qi_guess, Dei_guess, b_guess]
    config = {'optimize': ['Qi', 'Dei', 'b'], 'fixed': {'Def': def_val}}
    
    result = fcst.perform_curve_fit(t_act, q_act, initial_guess, bounds, config, method='curve_fit')
    # Handle different return formats (NEW METHOD)
    if isinstance(result, tuple) and len(result) > 1:
        qi_fit, dei_fit, b_fit = result[0]
    else:
        qi_fit, dei_fit, b_fit = result
    
    q_pred = fcst.varps_decline(1, 1, qi_fit, dei_fit, def_val, b_fit, t_act, 0, 0)[3]
    r2, rmse, mae = fcst.calc_goodness_of_fit(q_act, q_pred)
    
    print(f"\nFitted Parameters:")
    print(f"  Qi: {qi_fit:.2f}")
    print(f"  Dei: {dei_fit:.4f}")
    print(f"  b: {b_fit:.4f}")
    print(f"\nGoodness of Fit:")
    print(f"  R²: {r2:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  MAE: {mae:.4f}")
    
    # Validation check
    qi_error = abs(q_pred[0] - q_act[0]) / q_act[0] * 100
    print(f"\n✓ Validation: q_pred[0]={q_pred[0]:.2f}, q_act[0]={q_act[0]:.2f}, error={qi_error:.1f}%")
    
    return {
        't_act': t_act, 'q_act': q_act, 'q_pred': q_pred,
        'qi': qi_fit, 'dei': dei_fit, 'b': b_fit,
        'r2': r2, 'rmse': rmse, 'mae': mae
    }

def create_visualizations(df_well, old_result, new_result):
    """Create comprehensive visualizations"""
    
    # Get all actual data
    t_all = df_well['Date'].rank(method='min', ascending=True).to_numpy() - 1
    q_all = df_well['Value'].to_numpy()
    
    # Generate forecast (24 months ahead)
    t_forecast = np.arange(0, len(df_well) + 24)
    q_forecast_old = fcst.varps_decline(1, 1, old_result['qi'], old_result['dei'], 0.06, old_result['b'], t_forecast, 0, 0)[3]
    q_forecast_new = fcst.varps_decline(1, 1, new_result['qi'], new_result['dei'], 0.06, new_result['b'], t_forecast, 0, 0)[3]
    
    # Create figure with 4 subplots
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25)
    
    # 1. OLD METHOD - Linear
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(t_all, q_all, 'o', color='black', markersize=8, label='All Actual Data', alpha=0.7, zorder=3)
    ax1.plot(old_result['t_act'], old_result['q_act'], 's', color='red', markersize=7, 
             label='Used in Fit (1st dropped)', alpha=0.8, zorder=4)
    ax1.plot(t_forecast, q_forecast_old, '-', color='red', linewidth=2.5, 
             label=f'OLD Fit (R²={old_result["r2"]:.3f})', alpha=0.8)
    ax1.axvline(x=len(df_well)-1, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax1.set_xlabel('Time (months)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Production Rate', fontsize=12, fontweight='bold')
    ax1.set_title('OLD METHOD - Linear Scale\\n(First row dropped, t=0 is 2nd point)', 
                  fontsize=14, fontweight='bold', color='darkred')
    ax1.legend(fontsize=10, loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 2. OLD METHOD - Log
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.semilogy(t_all, q_all, 'o', color='black', markersize=8, label='All Actual Data', alpha=0.7, zorder=3)
    ax2.semilogy(old_result['t_act'], old_result['q_act'], 's', color='red', markersize=7, 
                 label='Used in Fit', alpha=0.8, zorder=4)
    ax2.semilogy(t_forecast, q_forecast_old, '-', color='red', linewidth=2.5, alpha=0.8)
    ax2.axvline(x=len(df_well)-1, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax2.set_xlabel('Time (months)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Production Rate (log)', fontsize=12, fontweight='bold')
    ax2.set_title('OLD METHOD - Log Scale', fontsize=14, fontweight='bold', color='darkred')
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, alpha=0.3, which='both')
    
    # 3. NEW METHOD - Linear
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(t_all, q_all, 'o', color='black', markersize=8, label='All Actual Data', alpha=0.7, zorder=3)
    ax3.plot(new_result['t_act'], new_result['q_act'], 's', color='green', markersize=7, 
             label='Used in Fit (all points)', alpha=0.8, zorder=4)
    ax3.plot(t_forecast, q_forecast_new, '-', color='green', linewidth=2.5, 
             label=f'NEW Fit (R²={new_result["r2"]:.3f})', alpha=0.8)
    ax3.plot(0, q_all[0], '*', color='blue', markersize=20, label='First Point (t=0)', zorder=5)
    ax3.axvline(x=len(df_well)-1, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax3.set_xlabel('Time (months)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Production Rate', fontsize=12, fontweight='bold')
    ax3.set_title('NEW METHOD - Linear Scale\\n(All rows kept, t=0 is 1st point)', 
                  fontsize=14, fontweight='bold', color='darkgreen')
    ax3.legend(fontsize=10, loc='best')
    ax3.grid(True, alpha=0.3)
    
    # 4. NEW METHOD - Log
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.semilogy(t_all, q_all, 'o', color='black', markersize=8, label='All Actual Data', alpha=0.7, zorder=3)
    ax4.semilogy(new_result['t_act'], new_result['q_act'], 's', color='green', markersize=7, 
                 label='Used in Fit', alpha=0.8, zorder=4)
    ax4.semilogy(t_forecast, q_forecast_new, '-', color='green', linewidth=2.5, alpha=0.8)
    ax4.semilogy(0, q_all[0], '*', color='blue', markersize=20, label='First Point (t=0)', zorder=5)
    ax4.axvline(x=len(df_well)-1, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax4.set_xlabel('Time (months)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Production Rate (log)', fontsize=12, fontweight='bold')
    ax4.set_title('NEW METHOD - Log Scale', fontsize=14, fontweight='bold', color='darkgreen')
    ax4.legend(fontsize=10, loc='best')
    ax4.grid(True, alpha=0.3, which='both')
    
    # 5. OVERLAY COMPARISON - Linear
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.plot(t_all, q_all, 'o', color='black', markersize=10, label='Actual Data', alpha=0.7, zorder=3)
    ax5.plot(t_forecast, q_forecast_old, '-', color='red', linewidth=3, 
             label=f'OLD (R²={old_result["r2"]:.3f})', alpha=0.6)
    ax5.plot(t_forecast, q_forecast_new, '-', color='green', linewidth=3, 
             label=f'NEW (R²={new_result["r2"]:.3f})', alpha=0.6)
    ax5.plot(0, q_all[0], '*', color='blue', markersize=20, label='First Point', zorder=5)
    ax5.axvline(x=len(df_well)-1, color='gray', linestyle='--', alpha=0.5, linewidth=2, label='Forecast Start')
    ax5.set_xlabel('Time (months)', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Production Rate', fontsize=12, fontweight='bold')
    ax5.set_title('COMPARISON - Linear Scale', fontsize=14, fontweight='bold')
    ax5.legend(fontsize=11, loc='best')
    ax5.grid(True, alpha=0.3)
    
    # 6. OVERLAY COMPARISON - Log
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.semilogy(t_all, q_all, 'o', color='black', markersize=10, label='Actual Data', alpha=0.7, zorder=3)
    ax6.semilogy(t_forecast, q_forecast_old, '-', color='red', linewidth=3, 
                 label=f'OLD Method', alpha=0.6)
    ax6.semilogy(t_forecast, q_forecast_new, '-', color='green', linewidth=3, 
                 label=f'NEW Method', alpha=0.6)
    ax6.semilogy(0, q_all[0], '*', color='blue', markersize=20, label='First Point', zorder=5)
    ax6.axvline(x=len(df_well)-1, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax6.set_xlabel('Time (months)', fontsize=12, fontweight='bold')
    ax6.set_ylabel('Production Rate (log)', fontsize=12, fontweight='bold')
    ax6.set_title('COMPARISON - Log Scale', fontsize=14, fontweight='bold')
    ax6.legend(fontsize=11, loc='best')
    ax6.grid(True, alpha=0.3, which='both')
    
    plt.suptitle('ARPS Curve Fitting Validation: OLD vs NEW Method', 
                 fontsize=18, fontweight='bold', y=0.995)
    
    plt.savefig('arps_validation_complete.png', dpi=150, bbox_inches='tight')
    print("\n✓ Saved visualization as 'arps_validation_complete.png'")
    plt.show()

def main():
    print("="*60)
    print("ARPS CURVE FITTING - VISUAL VALIDATION")
    print("="*60)
    
    # Load data
    df = pd.read_csv('sample_production_data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filter for one well
    well_id = 12345678901
    measure = 'GAS'
    
    df_well = df[(df['WellID'] == well_id) & (df['Measure'] == measure)].copy()
    df_well = df_well.sort_values('Date').reset_index(drop=True)
    
    print(f"\nWell ID: {well_id}")
    print(f"Measure: {measure}")
    print(f"Data points: {len(df_well)}")
    print(f"Date range: {df_well['Date'].min().date()} to {df_well['Date'].max().date()}")
    print(f"First rate: {df_well['Value'].iloc[0]:.2f}")
    print(f"Max rate: {df_well['Value'].max():.2f}")
    
    # Fit both methods
    old_result = fit_arps_old_method(df_well)
    new_result = fit_arps_new_method(df_well)
    
    # Print comparison
    print("\n" + "="*60)
    print("IMPROVEMENT SUMMARY:")
    print("="*60)
    print(f"R² improvement:   {new_result['r2'] - old_result['r2']:+.4f}  ({(new_result['r2'] - old_result['r2'])/old_result['r2']*100:+.1f}%)")
    print(f"RMSE improvement: {old_result['rmse'] - new_result['rmse']:+.4f}  ({(old_result['rmse'] - new_result['rmse'])/old_result['rmse']*100:+.1f}%)")
    print(f"MAE improvement:  {old_result['mae'] - new_result['mae']:+.4f}  ({(old_result['mae'] - new_result['mae'])/old_result['mae']*100:+.1f}%)")
    
    # Create visualizations
    create_visualizations(df_well, old_result, new_result)
    
    print("\n" + "="*60)
    print("✓ VALIDATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
