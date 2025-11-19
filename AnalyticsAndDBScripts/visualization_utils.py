"""
Visualization utilities for Arps decline curve analysis.

This module provides functions to visualize production data and fitted Arps curves.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import AnalyticsAndDBScripts.prod_fcst_functions as fcst


def plot_decline_curve(
    actual_data: pd.DataFrame,
    result_row: pd.Series,
    forecast_months: int = 24,
    figsize: Tuple[int, int] = (14, 10),
    save_path: Optional[str] = None
):
    """
    Plot Arps decline curve with actual production and forecast.
    
    Args:
        actual_data: DataFrame with columns [Date, Value]
        result_row: Series with fitted parameters [WellID, Measure, Q3, Dei, b_factor, R_squared]
        forecast_months: Number of months to forecast beyond last actual date
        figsize: Figure size (width, height)
        save_path: Optional path to save the figure
        
    Returns:
        matplotlib Figure object
    """
    wellid = int(result_row['WellID'])
    measure = result_row['Measure']
    
    # VALIDATION: Check if Q3 matches first actual data point
    first_actual = actual_data['Value'].iloc[0]
    qi_fit = result_row['Q3']
    error_pct = abs(qi_fit - first_actual) / first_actual * 100
    
    if error_pct > 10:
        import warnings
        warnings.warn(
            f"WARNING: Well {wellid} {measure} - Fitted Qi ({qi_fit:.2f}) differs from "
            f"first actual rate ({first_actual:.2f}) by {error_pct:.1f}%. "
            f"This indicates a fitting issue. The curve may not start at the correct point."
        )
    
    # Generate forecast
    t_months = np.arange(0, len(actual_data) + forecast_months)
    def_val = 0.06 if measure == 'GAS' else 0.08
    
    forecast = fcst.varps_decline(
        wellid, 1,
        result_row['Q3'],
        result_row['Dei'],
        def_val,
        result_row['b_factor'],
        t_months, 0, 0
    )
    
    # Create date range for forecast
    start_date = actual_data['Date'].min()
    forecast_dates = pd.date_range(start=start_date, periods=len(t_months), freq='MS')
    history_end = len(actual_data)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
    
    # Plot 1: Linear scale
    ax1.plot(actual_data['Date'], actual_data['Value'], 'o', 
             label='Actual Production', markersize=8, color='#2E86AB', alpha=0.7)
    ax1.plot(forecast_dates[:history_end], forecast[3][:history_end], '-', 
             label='Arps Fit (History)', linewidth=3, color='#A23B72')
    ax1.plot(forecast_dates[history_end:], forecast[3][history_end:], '--', 
             label='Arps Forecast (Future)', linewidth=3, color='#F18F01', alpha=0.8)
    ax1.axvline(x=actual_data['Date'].max(), color='gray', linestyle=':', linewidth=2, alpha=0.5)
    ax1.text(actual_data['Date'].max(), ax1.get_ylim()[1]*0.95, 'Last Actual', 
             rotation=90, va='top', ha='right', color='gray', fontsize=10)
    
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel(f'{measure} Rate (BBL/day or MCF/day)', fontsize=12)
    ax1.set_title(
        f'Well {wellid} - {measure} Arps Decline Curve\n'
        f'R² = {result_row["R_squared"]:.3f} | Qi = {result_row["Q3"]:.1f} | '
        f'Dei = {result_row["Dei"]:.3f} | b = {result_row["b_factor"]:.3f}', 
        fontsize=14, fontweight='bold'
    )
    ax1.legend(fontsize=11, loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Log scale
    ax2.semilogy(actual_data['Date'], actual_data['Value'], 'o', 
                 label='Actual Production', markersize=8, color='#2E86AB', alpha=0.7)
    ax2.semilogy(forecast_dates[:history_end], forecast[3][:history_end], '-', 
                 label='Arps Fit (History)', linewidth=3, color='#A23B72')
    ax2.semilogy(forecast_dates[history_end:], forecast[3][history_end:], '--', 
                 label='Arps Forecast (Future)', linewidth=3, color='#F18F01', alpha=0.8)
    ax2.axvline(x=actual_data['Date'].max(), color='gray', linestyle=':', linewidth=2, alpha=0.5)
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel(f'{measure} Rate (log scale)', fontsize=12)
    ax2.set_title('Log Scale View - Shows Exponential Decline', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=11, loc='upper right')
    ax2.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'✅ Plot saved to: {save_path}')
    
    return fig


def plot_all_wells(
    csv_loader,
    results_df: pd.DataFrame,
    output_dir: str = '.',
    forecast_months: int = 24
):
    """
    Generate decline curve plots for all wells in results.
    
    Args:
        csv_loader: CSVDataLoader instance
        results_df: DataFrame with fitted parameters
        output_dir: Directory to save plots
        forecast_months: Months to forecast
    """
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(f"Generating plots for {len(results_df)} wells...")
    
    for idx, result_row in results_df.iterrows():
        wellid = int(result_row['WellID'])
        measure = result_row['Measure']
        
        # Get actual production data
        actual_data = csv_loader.get_well_production(
            wellid=wellid,
            measure=measure,
            last_prod_date=pd.Timestamp('2024-10-01'),
            fit_months=60
        )
        
        if actual_data.empty:
            print(f"  ⚠️  Skipping Well {wellid} - {measure}: No data")
            continue
        
        # Generate plot
        save_path = output_path / f'well_{wellid}_{measure}_decline_curve.png'
        plot_decline_curve(actual_data, result_row, forecast_months, save_path=str(save_path))
        print(f"  ✓ Well {wellid} - {measure}")
        plt.close()
    
    print(f"\n✅ All plots saved to: {output_dir}")


def plot_comparison(
    csv_loader,
    results_df: pd.DataFrame,
    wellid: int,
    figsize: Tuple[int, int] = (16, 10)
):
    """
    Plot all three products (OIL, GAS, WATER) for a single well.
    
    Args:
        csv_loader: CSVDataLoader instance
        results_df: DataFrame with fitted parameters
        wellid: Well ID to plot
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    well_results = results_df[results_df['WellID'] == wellid]
    
    if len(well_results) == 0:
        raise ValueError(f"No results found for Well {wellid}")
    
    fig, axes = plt.subplots(3, 1, figsize=figsize)
    fig.suptitle(f'Well {wellid} - All Products', fontsize=16, fontweight='bold')
    
    for idx, (measure, ax) in enumerate(zip(['OIL', 'GAS', 'WATER'], axes)):
        result = well_results[well_results['Measure'] == measure]
        
        if len(result) == 0:
            ax.text(0.5, 0.5, f'No {measure} data', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'{measure} Production')
            continue
        
        result_row = result.iloc[0]
        
        # Get actual data
        actual_data = csv_loader.get_well_production(
            wellid=wellid,
            measure=measure,
            last_prod_date=pd.Timestamp('2024-10-01'),
            fit_months=60
        )
        
        # Generate forecast
        t_months = np.arange(0, len(actual_data) + 24)
        def_val = 0.06 if measure == 'GAS' else 0.08
        
        forecast = fcst.varps_decline(
            wellid, 1,
            result_row['Q3'],
            result_row['Dei'],
            def_val,
            result_row['b_factor'],
            t_months, 0, 0
        )
        
        start_date = actual_data['Date'].min()
        forecast_dates = pd.date_range(start=start_date, periods=len(t_months), freq='MS')
        history_end = len(actual_data)
        
        # Plot
        ax.plot(actual_data['Date'], actual_data['Value'], 'o', 
               label='Actual', markersize=6, alpha=0.7)
        ax.plot(forecast_dates[:history_end], forecast[3][:history_end], '-', 
               label='Fit', linewidth=2)
        ax.plot(forecast_dates[history_end:], forecast[3][history_end:], '--', 
               label='Forecast', linewidth=2, alpha=0.8)
        ax.axvline(x=actual_data['Date'].max(), color='gray', linestyle=':', alpha=0.5)
        
        ax.set_ylabel(f'{measure} Rate', fontsize=11)
        ax.set_title(f'{measure} - R² = {result_row["R_squared"]:.3f}', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    axes[-1].set_xlabel('Date', fontsize=12)
    plt.tight_layout()
    
    return fig


if __name__ == '__main__':
    # Example usage
    from AnalyticsAndDBScripts.csv_loader import CSVDataLoader
    
    print("Loading data...")
    csv_loader = CSVDataLoader('sample_production_data.csv', 'sample_well_list.csv')
    results_df = pd.read_csv('test_results.csv')
    
    print("\nGenerating single well plot...")
    result_row = results_df.iloc[0]
    wellid = int(result_row['WellID'])
    measure = result_row['Measure']
    
    actual_data = csv_loader.get_well_production(
        wellid=wellid,
        measure=measure,
        last_prod_date=pd.Timestamp('2024-10-01'),
        fit_months=60
    )
    
    fig = plot_decline_curve(actual_data, result_row, save_path='example_decline_curve.png')
    plt.show()
    
    print("\n✅ Visualization complete!")
