"""
Test script for aggregate ARPS analysis functionality.
Validates that the aggregate analysis correctly averages production and fits curves.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from AnalyticsAndDBScripts.csv_loader import CSVDataLoader

print("=" * 80)
print("AGGREGATE ARPS ANALYSIS - VALIDATION TEST")
print("=" * 80)
print()

# Load data
print("Step 1: Loading sample data...")
csv_loader = CSVDataLoader('sample_production_data.csv', 'sample_well_list.csv')
prod_df = csv_loader.load_production_data()
well_list_df = csv_loader.load_well_list()

print(f"✅ Loaded {len(prod_df)} production records")
print(f"✅ Loaded {len(well_list_df)} well/measure combinations")
print(f"   Wells: {prod_df['WellID'].nunique()}")
print(f"   Measures: {list(prod_df['Measure'].unique())}")
print()

# Test aggregate analysis
print("Step 2: Testing aggregate analysis function...")
print()

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "arps_autofit_csv",
    Path(__file__).parent / "play_assesments_tools" / "python files" / "arps_autofit_csv.py"
)
arps_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arps_module)

fit_aggregate_arps_curve = arps_module.fit_aggregate_arps_curve

# Test for OIL
print("Testing OIL aggregate analysis...")
result_oil, agg_df_oil = fit_aggregate_arps_curve(
    measure='OIL',
    b_dict=arps_module.default_b_dict['OIL'],
    dei_dict=arps_module.dei_dict1,
    def_dict=arps_module.def_dict,
    min_q_dict=arps_module.min_q_dict,
    prod_df_all_wells=prod_df,
    value_col='Value',
    method='curve_fit',
    trials=1000,
    smoothing_factor=2
)

if result_oil is not None:
    print("✅ OIL aggregate analysis successful!")
    print(f"   WellID: {result_oil[0]}")
    print(f"   Measure: {result_oil[1]}")
    print(f"   Data points: {result_oil[2]}")
    print(f"   Qi: {result_oil[8]:.2f}")
    print(f"   Dei: {result_oil[9]:.3f}")
    print(f"   b-factor: {result_oil[10]:.3f}")
    print(f"   R²: {result_oil[11]:.3f}")
    print()
    
    # Validate aggregated data
    print("   Aggregated data summary:")
    print(f"   - Months: {len(agg_df_oil)}")
    print(f"   - Avg production range: {agg_df_oil['avg_production'].min():.2f} to {agg_df_oil['avg_production'].max():.2f}")
    print(f"   - Wells per month: {agg_df_oil['well_count'].iloc[0]}")
    print()
else:
    print("❌ OIL aggregate analysis failed")
    print()

# Test for GAS
print("Testing GAS aggregate analysis...")
result_gas, agg_df_gas = fit_aggregate_arps_curve(
    measure='GAS',
    b_dict=arps_module.default_b_dict['GAS'],
    dei_dict=arps_module.dei_dict1,
    def_dict=arps_module.def_dict,
    min_q_dict=arps_module.min_q_dict,
    prod_df_all_wells=prod_df,
    value_col='Value',
    method='curve_fit',
    trials=1000,
    smoothing_factor=2
)

if result_gas is not None:
    print("✅ GAS aggregate analysis successful!")
    print(f"   WellID: {result_gas[0]}")
    print(f"   Measure: {result_gas[1]}")
    print(f"   Data points: {result_gas[2]}")
    print(f"   Qi: {result_gas[8]:.2f}")
    print(f"   Dei: {result_gas[9]:.3f}")
    print(f"   b-factor: {result_gas[10]:.3f}")
    print(f"   R²: {result_gas[11]:.3f}")
    print()
    
    # Validate aggregated data
    print("   Aggregated data summary:")
    print(f"   - Months: {len(agg_df_gas)}")
    print(f"   - Avg production range: {agg_df_gas['avg_production'].min():.2f} to {agg_df_gas['avg_production'].max():.2f}")
    print(f"   - Wells per month: {agg_df_gas['well_count'].iloc[0]}")
    print()
else:
    print("❌ GAS aggregate analysis failed")
    print()

# Validation checks
print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

checks_passed = 0
total_checks = 6

# Check 1: Results exist
if result_oil is not None and result_gas is not None:
    print("✅ Both OIL and GAS analyses completed")
    checks_passed += 1
else:
    print("❌ One or more analyses failed")

# Check 2: WellID is AGGREGATE
if result_oil and result_oil[0] == 'AGGREGATE':
    print("✅ WellID correctly set to 'AGGREGATE'")
    checks_passed += 1
else:
    print("❌ WellID not set to 'AGGREGATE'")

# Check 3: R² values are reasonable
if result_oil and result_gas and result_oil[11] > 0.5 and result_gas[11] > 0.5:
    print(f"✅ R² values are reasonable (OIL: {result_oil[11]:.3f}, GAS: {result_gas[11]:.3f})")
    checks_passed += 1
else:
    print("❌ R² values are too low")

# Check 4: Aggregated data has correct structure
if agg_df_oil is not None and 'avg_production' in agg_df_oil.columns and 'well_count' in agg_df_oil.columns:
    print("✅ Aggregated data has correct structure")
    checks_passed += 1
else:
    print("❌ Aggregated data structure incorrect")

# Check 5: Number of data points matches expected
expected_months = 24  # 20 wells with 24 months each
if agg_df_oil is not None and len(agg_df_oil) == expected_months:
    print(f"✅ Aggregated data has expected {expected_months} months")
    checks_passed += 1
else:
    actual = len(agg_df_oil) if agg_df_oil is not None else 0
    print(f"❌ Aggregated data has {actual} months, expected {expected_months}")

# Check 6: Predicted values exist
if agg_df_oil is not None and 'predicted' in agg_df_oil.columns:
    print("✅ Predicted values calculated")
    checks_passed += 1
else:
    print("❌ Predicted values missing")

print()
print(f"FINAL SCORE: {checks_passed}/{total_checks} checks passed")
print()

if checks_passed == total_checks:
    print("🎉 ALL VALIDATION CHECKS PASSED!")
    print("   Aggregate analysis is working correctly.")
elif checks_passed >= total_checks * 0.7:
    print("⚠️  MOST CHECKS PASSED")
    print("   Aggregate analysis is mostly working but needs review.")
else:
    print("❌ VALIDATION FAILED")
    print("   Aggregate analysis needs debugging.")

print("=" * 80)
