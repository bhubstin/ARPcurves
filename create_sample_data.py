"""
Create clean sample data for ARPS decline curve analysis
20 wells, 24 months each
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("Creating sample data...")
print()

# Set seed for reproducibility
np.random.seed(42)

def generate_arps(qi, dei, b, months, noise=0.015):
    """Generate ARPS hyperbolic decline with noise"""
    t = np.arange(months)
    di_monthly = dei / 12
    q = qi / (1 + b * di_monthly * t) ** (1/b)
    noise_vals = np.random.normal(0, noise, months)
    q = q * (1 + noise_vals)
    return np.maximum(q, 0.1)

# Generate 20 wells
data = []
start_date = datetime(2022, 1, 1)
months = 24

for well_num in range(20):
    wellid = 10000000000 + well_num * 111111111
    
    # Vary parameters for each well
    well_type = np.random.choice(['high', 'medium', 'low'], p=[0.4, 0.4, 0.2])
    
    if well_type == 'high':
        oil_qi = np.random.uniform(400, 600)
        oil_dei = np.random.uniform(0.60, 0.75)
        oil_b = np.random.uniform(1.1, 1.4)
    elif well_type == 'medium':
        oil_qi = np.random.uniform(250, 400)
        oil_dei = np.random.uniform(0.45, 0.60)
        oil_b = np.random.uniform(0.9, 1.2)
    else:
        oil_qi = np.random.uniform(150, 250)
        oil_dei = np.random.uniform(0.20, 0.40)
        oil_b = np.random.uniform(0.5, 0.9)
    
    gas_qi = oil_qi * np.random.uniform(3.5, 4.5)
    gas_dei = oil_dei * np.random.uniform(0.85, 0.95)
    gas_b = oil_b * np.random.uniform(0.9, 1.0)
    
    water_qi = np.random.uniform(40, 120)
    
    # Generate production
    oil_prod = generate_arps(oil_qi, oil_dei, oil_b, months)
    gas_prod = generate_arps(gas_qi, gas_dei, gas_b, months)
    water_prod = water_qi * (1 + 0.01 * np.arange(months))
    water_prod = water_prod * (1 + np.random.normal(0, 0.02, months))
    
    # Create records
    for i in range(months):
        date = (start_date + timedelta(days=30*i)).strftime('%Y-%m-%d')
        
        data.append({
            'WellID': wellid,
            'Measure': 'OIL',
            'Date': date,
            'Value': round(oil_prod[i], 2),
            'ProducingDays': 30
        })
        
        data.append({
            'WellID': wellid,
            'Measure': 'GAS',
            'Date': date,
            'Value': round(gas_prod[i], 2),
            'ProducingDays': 30
        })
        
        data.append({
            'WellID': wellid,
            'Measure': 'WATER',
            'Date': date,
            'Value': round(water_prod[i], 2),
            'ProducingDays': 30
        })

# Create DataFrame with exact column order
df = pd.DataFrame(data, columns=['WellID', 'Measure', 'Date', 'Value', 'ProducingDays'])

# Save production data
df.to_csv('sample_production_data.csv', index=False)
print(f"✅ Created sample_production_data.csv")
print(f"   Columns: {list(df.columns)}")
print(f"   Records: {len(df)}")
print(f"   Wells: {df['WellID'].nunique()}")
print()

# Create well list
wells = []
last_date = df['Date'].max()
for wellid in df['WellID'].unique():
    wells.append({
        'WellID': wellid,
        'Measure': 'OIL',
        'LastProdDate': last_date
    })
    wells.append({
        'WellID': wellid,
        'Measure': 'GAS',
        'LastProdDate': last_date
    })

well_df = pd.DataFrame(wells, columns=['WellID', 'Measure', 'LastProdDate'])
well_df.to_csv('sample_well_list.csv', index=False)
print(f"✅ Created sample_well_list.csv")
print(f"   Columns: {list(well_df.columns)}")
print(f"   Records: {len(well_df)}")
print()

# Verify the files
print("Verifying files...")
test_df = pd.read_csv('sample_production_data.csv')
print(f"Production data columns: {list(test_df.columns)}")
print(f"First row:\n{test_df.iloc[0]}")
print()

test_well = pd.read_csv('sample_well_list.csv')
print(f"Well list columns: {list(test_well.columns)}")
print(f"First row:\n{test_well.iloc[0]}")
print()

print("✅ All files created successfully!")
