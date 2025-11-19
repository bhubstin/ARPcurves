"""
CSV Data Loader for Arps Decline Curve Analysis

This module provides functionality to load production data from CSV files
as an alternative to SQL database queries.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import warnings
from pathlib import Path


class CSVDataLoader:
    """
    Handles loading production data from CSV files instead of SQL database.
    
    This class mimics the behavior of SQL queries used in the original
    arps_autofit.py script, allowing users to work with CSV files instead
    of requiring a database connection.
    """
    
    def __init__(self, production_csv_path: str, well_list_csv_path: Optional[str] = None):
        """
        Initialize CSV data loader.
        
        Args:
            production_csv_path: Path to production data CSV file
            well_list_csv_path: Optional path to well list CSV file
            
        Raises:
            FileNotFoundError: If production CSV file doesn't exist
        """
        self.production_csv_path = Path(production_csv_path)
        self.well_list_csv_path = Path(well_list_csv_path) if well_list_csv_path else None
        
        if not self.production_csv_path.exists():
            raise FileNotFoundError(f"Production CSV not found: {production_csv_path}")
        
        if self.well_list_csv_path and not self.well_list_csv_path.exists():
            raise FileNotFoundError(f"Well list CSV not found: {well_list_csv_path}")
        
        self._production_df = None
        self._well_list_df = None
        
    def load_production_data(self) -> pd.DataFrame:
        """
        Load and validate production data from CSV.
        
        Returns:
            DataFrame with columns: WellID, Measure, Date, Value, ProducingDays
            
        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        if self._production_df is None:
            print(f"Loading production data from {self.production_csv_path}...")
            df = pd.read_csv(self.production_csv_path)
            
            # Validate required columns
            required_cols = ['WellID', 'Measure', 'Date', 'Value']
            missing = set(required_cols) - set(df.columns)
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            print(f"  Found {len(df)} records")
            
            # Convert data types
            df['WellID'] = df['WellID'].astype(np.int64)
            df['Date'] = pd.to_datetime(df['Date'])
            df['Value'] = df['Value'].astype(float)
            
            # Add ProducingDays if not present
            if 'ProducingDays' not in df.columns:
                print("  ProducingDays column not found, using default value of 30.42")
                df['ProducingDays'] = 30.42
            else:
                df['ProducingDays'] = df['ProducingDays'].fillna(30.42)
            
            # Validate Measure values
            valid_measures = {'OIL', 'GAS', 'WATER'}
            invalid = set(df['Measure'].unique()) - valid_measures
            if invalid:
                raise ValueError(
                    f"Invalid Measure values: {invalid}. "
                    f"Must be one of: {valid_measures}"
                )
            
            # Filter out invalid values
            initial_count = len(df)
            df = df[df['Value'] > 0].copy()
            removed = initial_count - len(df)
            if removed > 0:
                print(f"  Removed {removed} records with Value <= 0")
            
            # Check for null values
            null_counts = df[required_cols].isnull().sum()
            if null_counts.any():
                print(f"  Warning: Found null values:\n{null_counts[null_counts > 0]}")
                df = df.dropna(subset=required_cols)
                print(f"  Removed rows with nulls, {len(df)} records remaining")
            
            # Sort by WellID, Measure, Date
            df = df.sort_values(['WellID', 'Measure', 'Date']).reset_index(drop=True)
            
            # Summary statistics
            print(f"  Final dataset: {len(df)} records")
            print(f"  Wells: {df['WellID'].nunique()}")
            print(f"  Date range: {df['Date'].min()} to {df['Date'].max()}")
            print(f"  Measures: {df['Measure'].value_counts().to_dict()}")
            
            self._production_df = df
            
        return self._production_df
    
    def load_well_list(self) -> pd.DataFrame:
        """
        Load well list from CSV or generate from production data.
        
        If well_list_csv_path was not provided, this generates a well list
        from the production data automatically.
        
        Returns:
            DataFrame with columns: WellID, Measure, LastProdDate, FitMethod
        """
        if self._well_list_df is None:
            if self.well_list_csv_path:
                print(f"Loading well list from {self.well_list_csv_path}...")
                df = pd.read_csv(self.well_list_csv_path)
                
                # Validate required columns
                required_cols = ['WellID', 'Measure']
                missing = set(required_cols) - set(df.columns)
                if missing:
                    raise ValueError(f"Missing required columns in well list: {missing}")
                
                df['WellID'] = df['WellID'].astype(np.int64)
                
                # Handle LastProdDate
                if 'LastProdDate' in df.columns:
                    df['LastProdDate'] = pd.to_datetime(df['LastProdDate'])
                else:
                    print("  LastProdDate not found, will derive from production data")
                    prod_df = self.load_production_data()
                    last_dates = prod_df.groupby(['WellID', 'Measure'])['Date'].max().reset_index()
                    last_dates.rename(columns={'Date': 'LastProdDate'}, inplace=True)
                    df = df.merge(last_dates, on=['WellID', 'Measure'], how='left')
                
                # Set default FitMethod if not present
                if 'FitMethod' not in df.columns:
                    print("  FitMethod not found, using default 'curve_fit'")
                    df['FitMethod'] = 'curve_fit'
                else:
                    df['FitMethod'] = df['FitMethod'].fillna('curve_fit')
            else:
                print("No well list provided, generating from production data...")
                # Generate well list from production data
                prod_df = self.load_production_data()
                df = prod_df.groupby(['WellID', 'Measure']).agg({
                    'Date': 'max'
                }).reset_index()
                df.rename(columns={'Date': 'LastProdDate'}, inplace=True)
                df['FitMethod'] = 'curve_fit'
            
            print(f"  Loaded {len(df)} well/measure combinations")
            
            self._well_list_df = df
            
        return self._well_list_df
    
    def get_well_production(
        self, 
        wellid: int, 
        measure: str, 
        last_prod_date: pd.Timestamp,
        fit_months: int = 60,
        cadence: str = 'MONTHLY'
    ) -> pd.DataFrame:
        """
        Get production data for a specific well/measure combination.
        
        This method mimics the SQL query behavior from create_statement() in
        the original arps_autofit.py script.
        
        Args:
            wellid: Well ID (integer)
            measure: Product type - 'OIL', 'GAS', or 'WATER'
            last_prod_date: Last production date for the well
            fit_months: Number of months to include (default 60)
            cadence: Data cadence - 'MONTHLY' or 'DAILY' (default 'MONTHLY')
            
        Returns:
            DataFrame with columns: WellID, Measure, Date, Value
            Value is normalized to rate (per day)
            
        Raises:
            ValueError: If measure is invalid
        """
        if measure not in ['OIL', 'GAS', 'WATER']:
            raise ValueError(f"Invalid measure: {measure}. Must be OIL, GAS, or WATER")
        
        prod_df = self.load_production_data()
        
        # Filter for specific well and measure
        mask = (
            (prod_df['WellID'] == wellid) &
            (prod_df['Measure'] == measure)
        )
        
        # Filter by date range (fit_months before last_prod_date)
        cutoff_date = last_prod_date - pd.DateOffset(months=fit_months)
        mask &= (prod_df['Date'] >= cutoff_date) & (prod_df['Date'] <= last_prod_date)
        
        result = prod_df[mask].copy()
        
        if result.empty:
            return result[['WellID', 'Measure', 'Date', 'Value']]
        
        # Calculate rate (Value / ProducingDays)
        # This mimics the SQL query: Value / COALESCE(NULLIF(ProducingDays, 0), divisor)
        divisor = 1.0 if cadence == 'DAILY' else 30.42
        result['Value'] = result['Value'] / result['ProducingDays'].replace(0, divisor)
        
        # Select and order columns to match SQL output
        result = result[['WellID', 'Measure', 'Date', 'Value']].sort_values('Date')
        
        return result.reset_index(drop=True)
    
    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics for the loaded production data.
        
        Returns:
            Dictionary with summary statistics
        """
        prod_df = self.load_production_data()
        well_list_df = self.load_well_list()
        
        stats = {
            'total_records': len(prod_df),
            'total_wells': prod_df['WellID'].nunique(),
            'total_well_measure_combos': len(well_list_df),
            'date_range': {
                'min': prod_df['Date'].min(),
                'max': prod_df['Date'].max()
            },
            'measures': prod_df['Measure'].value_counts().to_dict(),
            'wells_by_measure': prod_df.groupby('Measure')['WellID'].nunique().to_dict()
        }
        
        return stats
    
    def validate_data_quality(self) -> Dict:
        """
        Perform data quality checks on the production data.
        
        Returns:
            Dictionary with validation results and warnings
        """
        prod_df = self.load_production_data()
        
        issues = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Check for duplicate records
        duplicates = prod_df.duplicated(subset=['WellID', 'Measure', 'Date']).sum()
        if duplicates > 0:
            issues['warnings'].append(f"Found {duplicates} duplicate records (same WellID/Measure/Date)")
        
        # Check for gaps in production data
        for (wellid, measure), group in prod_df.groupby(['WellID', 'Measure']):
            dates = group['Date'].sort_values()
            if len(dates) > 1:
                gaps = (dates.diff() > pd.Timedelta(days=45)).sum()  # More than 1.5 months
                if gaps > 0:
                    issues['info'].append(f"Well {wellid} {measure}: {gaps} gaps > 45 days in production")
        
        # Check for outliers in production values
        for measure in ['OIL', 'GAS', 'WATER']:
            measure_data = prod_df[prod_df['Measure'] == measure]['Value']
            if len(measure_data) > 0:
                q99 = measure_data.quantile(0.99)
                outliers = (measure_data > q99 * 10).sum()  # 10x the 99th percentile
                if outliers > 0:
                    issues['warnings'].append(
                        f"{measure}: {outliers} records with extremely high values (>10x P99)"
                    )
        
        return issues


def create_sample_csv_files(output_dir: str = '.'):
    """
    Create sample CSV files for testing.
    
    Args:
        output_dir: Directory to save sample files (default: current directory)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Sample production data
    dates = pd.date_range('2023-01-01', '2024-10-01', freq='MS')
    
    production_data = []
    for wellid in [12345678901, 98765432109]:
        for i, date in enumerate(dates):
            # Simulate declining production
            oil_rate = 200 * np.exp(-0.03 * i) + np.random.normal(0, 5)
            gas_rate = 600 * np.exp(-0.025 * i) + np.random.normal(0, 15)
            water_rate = 50 * (1 + 0.02 * i) + np.random.normal(0, 2)
            
            production_data.extend([
                {
                    'WellID': wellid,
                    'Measure': 'OIL',
                    'Date': date,
                    'Value': max(1, oil_rate),
                    'ProducingDays': 30
                },
                {
                    'WellID': wellid,
                    'Measure': 'GAS',
                    'Date': date,
                    'Value': max(1, gas_rate),
                    'ProducingDays': 30
                },
                {
                    'WellID': wellid,
                    'Measure': 'WATER',
                    'Date': date,
                    'Value': max(0, water_rate),
                    'ProducingDays': 30
                }
            ])
    
    prod_df = pd.DataFrame(production_data)
    prod_file = output_path / 'sample_production_data.csv'
    prod_df.to_csv(prod_file, index=False)
    print(f"Created sample production data: {prod_file}")
    
    # Sample well list
    well_list_data = [
        {'WellID': 12345678901, 'Measure': 'OIL', 'LastProdDate': '2024-10-01', 'FitMethod': 'monte_carlo'},
        {'WellID': 12345678901, 'Measure': 'GAS', 'LastProdDate': '2024-10-01', 'FitMethod': 'curve_fit'},
        {'WellID': 98765432109, 'Measure': 'OIL', 'LastProdDate': '2024-10-01', 'FitMethod': 'curve_fit'},
        {'WellID': 98765432109, 'Measure': 'GAS', 'LastProdDate': '2024-10-01', 'FitMethod': 'curve_fit'},
    ]
    
    well_df = pd.DataFrame(well_list_data)
    well_file = output_path / 'sample_well_list.csv'
    well_df.to_csv(well_file, index=False)
    print(f"Created sample well list: {well_file}")
    
    return prod_file, well_file


if __name__ == '__main__':
    # Test the module
    print("Creating sample CSV files...")
    prod_file, well_file = create_sample_csv_files()
    
    print("\nTesting CSVDataLoader...")
    loader = CSVDataLoader(str(prod_file), str(well_file))
    
    print("\nLoading production data...")
    prod_df = loader.load_production_data()
    
    print("\nLoading well list...")
    well_list = loader.load_well_list()
    
    print("\nGetting production for specific well...")
    well_prod = loader.get_well_production(
        wellid=12345678901,
        measure='OIL',
        last_prod_date=pd.Timestamp('2024-10-01'),
        fit_months=12
    )
    print(f"Retrieved {len(well_prod)} records")
    print(well_prod.head())
    
    print("\nSummary statistics:")
    stats = loader.get_summary_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nData quality validation:")
    issues = loader.validate_data_quality()
    for level, messages in issues.items():
        if messages:
            print(f"  {level.upper()}:")
            for msg in messages:
                print(f"    - {msg}")
    
    print("\n✅ CSV loader module test complete!")
