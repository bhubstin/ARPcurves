# CSV Upload Implementation Guide

## Overview
This guide explains how to add CSV file upload capability as an alternative to SQL database input for the Arps decline curve analysis.

## Current Architecture

### Data Flow (SQL-based)
```
SQL Database → load_data() → Production DataFrame → 
Arps Fitting → Results → SQL Database
```

### Key Functions
- `load_data()` - Queries SQL and returns DataFrame
- `create_statement()` - Builds SQL query for production data
- `auto_forecast()` - Main processing function that calls `load_data()`

## Required CSV File Format

### 1. Production Data CSV
**Filename:** `production_data.csv`

**Required Columns:**
```csv
WellID,Measure,Date,Value,ProducingDays
12345678901,OIL,2023-01-01,150.5,30
12345678901,OIL,2023-02-01,145.2,28
12345678901,GAS,2023-01-01,450.0,30
12345678901,GAS,2023-02-01,425.0,28
12345678901,WATER,2023-01-01,50.0,30
```

**Column Definitions:**
- `WellID` (integer): Unique well identifier (API number)
- `Measure` (string): Product type - "OIL", "GAS", or "WATER"
- `Date` (datetime): Production date (YYYY-MM-DD format)
- `Value` (float): Production volume (BBL for oil/water, MCF for gas)
- `ProducingDays` (integer): Days producing in that month (optional, defaults to 30.42)

**Notes:**
- Values must be > 0
- Dates should be in chronological order per well/measure
- One row per well/measure/date combination

### 2. Well List CSV (Optional)
**Filename:** `well_list.csv`

**Required Columns:**
```csv
WellID,Measure,LastProdDate,FitMethod
12345678901,OIL,2024-10-01,monte_carlo
12345678901,GAS,2024-10-01,curve_fit
98765432109,OIL,2024-09-15,monte_carlo
```

**Column Definitions:**
- `WellID` (integer): Unique well identifier
- `Measure` (string): "OIL", "GAS", or "WATER"
- `LastProdDate` (datetime): Most recent production date
- `FitMethod` (string): "curve_fit", "monte_carlo", or "differential_evolution"

## Implementation Steps

### Step 1: Create CSV Data Loader Module

Create new file: `AnalyticsAndDBScripts/csv_loader.py`

```python
import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import warnings

class CSVDataLoader:
    """
    Handles loading production data from CSV files instead of SQL database.
    """
    
    def __init__(self, production_csv_path: str, well_list_csv_path: Optional[str] = None):
        """
        Initialize CSV data loader.
        
        Args:
            production_csv_path: Path to production data CSV
            well_list_csv_path: Optional path to well list CSV
        """
        self.production_csv_path = production_csv_path
        self.well_list_csv_path = well_list_csv_path
        self._production_df = None
        self._well_list_df = None
        
    def load_production_data(self) -> pd.DataFrame:
        """Load and validate production data from CSV."""
        if self._production_df is None:
            df = pd.read_csv(self.production_csv_path)
            
            # Validate required columns
            required_cols = ['WellID', 'Measure', 'Date', 'Value']
            missing = set(required_cols) - set(df.columns)
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            # Convert data types
            df['WellID'] = df['WellID'].astype(np.int64)
            df['Date'] = pd.to_datetime(df['Date'])
            df['Value'] = df['Value'].astype(float)
            
            # Add ProducingDays if not present
            if 'ProducingDays' not in df.columns:
                df['ProducingDays'] = 30.42
            else:
                df['ProducingDays'] = df['ProducingDays'].fillna(30.42)
            
            # Validate Measure values
            valid_measures = {'OIL', 'GAS', 'WATER'}
            invalid = set(df['Measure'].unique()) - valid_measures
            if invalid:
                raise ValueError(f"Invalid Measure values: {invalid}. Must be OIL, GAS, or WATER")
            
            # Filter out invalid values
            df = df[df['Value'] > 0].copy()
            
            # Sort by WellID, Measure, Date
            df = df.sort_values(['WellID', 'Measure', 'Date']).reset_index(drop=True)
            
            self._production_df = df
            
        return self._production_df
    
    def load_well_list(self) -> pd.DataFrame:
        """Load well list from CSV or generate from production data."""
        if self._well_list_df is None:
            if self.well_list_csv_path:
                df = pd.read_csv(self.well_list_csv_path)
                df['WellID'] = df['WellID'].astype(np.int64)
                df['LastProdDate'] = pd.to_datetime(df['LastProdDate'])
                
                # Set default FitMethod if not present
                if 'FitMethod' not in df.columns:
                    df['FitMethod'] = 'curve_fit'
            else:
                # Generate well list from production data
                prod_df = self.load_production_data()
                df = prod_df.groupby(['WellID', 'Measure']).agg({
                    'Date': 'max'
                }).reset_index()
                df.rename(columns={'Date': 'LastProdDate'}, inplace=True)
                df['FitMethod'] = 'curve_fit'
            
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
        Mimics the SQL query behavior.
        
        Args:
            wellid: Well ID
            measure: Product type (OIL, GAS, WATER)
            last_prod_date: Last production date
            fit_months: Number of months to include
            cadence: Data cadence (MONTHLY or DAILY)
            
        Returns:
            DataFrame with columns: WellID, Measure, Date, Value
        """
        prod_df = self.load_production_data()
        
        # Filter for specific well and measure
        mask = (
            (prod_df['WellID'] == wellid) &
            (prod_df['Measure'] == measure)
        )
        
        # Filter by date range
        cutoff_date = last_prod_date - pd.DateOffset(months=fit_months)
        mask &= (prod_df['Date'] >= cutoff_date)
        
        result = prod_df[mask].copy()
        
        # Calculate rate (Value / ProducingDays)
        divisor = 1.0 if cadence == 'DAILY' else 30.42
        result['Value'] = result['Value'] / result['ProducingDays'].replace(0, divisor)
        
        # Select and order columns to match SQL output
        result = result[['WellID', 'Measure', 'Date', 'Value']].sort_values('Date')
        
        return result.reset_index(drop=True)
```

### Step 2: Modify `arps_autofit.py` to Support CSV

Add these functions to `play_assesments_tools/python files/arps_autofit.py`:

```python
# Add at top of file
from AnalyticsAndDBScripts.csv_loader import CSVDataLoader

# Add new function to load data from CSV
def load_data_from_csv(csv_loader, wellid, measure, last_prod_date, fit_months=60):
    """
    Load production data from CSV instead of SQL.
    
    Args:
        csv_loader: CSVDataLoader instance
        wellid: Well ID
        measure: Product type
        last_prod_date: Last production date
        fit_months: Number of months to include
        
    Returns:
        DataFrame with production data
    """
    return csv_loader.get_well_production(
        wellid=wellid,
        measure=measure,
        last_prod_date=last_prod_date,
        fit_months=fit_months
    )

# Modify auto_forecast to accept data_source parameter
def auto_forecast_csv(
        wellid, 
        measure, 
        last_prod_date,
        csv_loader,  # NEW: CSV loader instance
        value_col, 
        bourdet_params, 
        changepoint_params, 
        b_estimate_params, 
        dei_dict1, 
        default_b_dict, 
        method, 
        use_advi, 
        smoothing_factor,
        save_trace
    ):
    """
    Modified version of auto_forecast that uses CSV data instead of SQL.
    """
    # Load production data from CSV
    prod_df = load_data_from_csv(csv_loader, wellid, measure, last_prod_date, fit_months=fit_months)

    # Check if prod_df is empty
    if prod_df.empty:
        return [wellid, measure, 0, 'no_data', np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, None]
    
    # Rest of the function remains the same as auto_forecast()
    # ... (copy the rest of auto_forecast logic here)
```

### Step 3: Create Jupyter Notebook for CSV-based Analysis

Create: `play_assesments_tools/Jupyter Notebooks/arps_autofit_csv.ipynb`

```python
# Cell 1: Imports
import pandas as pd
import numpy as np
from AnalyticsAndDBScripts.csv_loader import CSVDataLoader
from config.config_loader import get_config
import AnalyticsAndDBScripts.prod_fcst_functions as fcst
import warnings

warnings.filterwarnings('ignore')

# Cell 2: Configuration
# Load parameters from config
params_list = get_config('decline_curve')
arps_params = next((item for item in params_list if item['name'] == 'arps_parameters'), None)
bourdet_params = next((item for item in params_list if item['name'] == 'bourdet_outliers'), None)
changepoint_params = next((item for item in params_list if item['name'] == 'detect_changepoints'), None)
b_estimate_params = next((item for item in params_list if item['name'] == 'estimate_b'), None)
smoothing_params = next((item for item in params_list if item['name'] == 'smoothing'), None)
method_params = next((item for item in params_list if item['name'] == 'method'), None)

# Define parameters
value_col = 'Value'
fit_method = 'monte_carlo'
trials = method_params['trials']
fit_months = method_params['general']['fit_months']

# Load decline parameters
def_dict = arps_params['terminal_decline']
dei_dict1 = arps_params['initial_decline']
min_q_dict = arps_params['abandonment_rate']
default_b_dict = arps_params['b_factor']

# Cell 3: Load CSV Data
# Specify CSV file paths
production_csv = '/path/to/production_data.csv'
well_list_csv = '/path/to/well_list.csv'  # Optional

# Initialize CSV loader
csv_loader = CSVDataLoader(
    production_csv_path=production_csv,
    well_list_csv_path=well_list_csv
)

# Load well list
well_list_df = csv_loader.load_well_list()
print(f"Loaded {len(well_list_df)} well/measure combinations")
print(well_list_df.head())

# Cell 4: Process Wells
results = []

for idx, row in well_list_df.iterrows():
    wellid = row['WellID']
    measure = row['Measure']
    last_prod_date = row['LastProdDate']
    
    print(f"Processing Well {wellid} - {measure}...")
    
    try:
        # Get production data
        prod_df = csv_loader.get_well_production(
            wellid=wellid,
            measure=measure,
            last_prod_date=last_prod_date,
            fit_months=fit_months
        )
        
        if prod_df.empty:
            print(f"  No data found")
            continue
        
        # Add months producing
        min_date = prod_df['Date'].min()
        prod_df['MonthsProducing'] = prod_df['Date'].apply(
            lambda x: fcst.MonthDiff(min_date, x)
        )
        
        # Apply outlier removal if enabled
        if bourdet_params['setting']:
            x = prod_df['MonthsProducing'].values
            y = prod_df[value_col].values
            y_new, x_new = fcst.bourdet_outliers(
                y, x, 
                L=bourdet_params['smoothing_factor'],
                xlog=False, 
                ylog=True,
                z_threshold=bourdet_params['z_threshold'],
                min_array_size=bourdet_params['min_array_size']
            )
            prod_df = prod_df[prod_df['MonthsProducing'].isin(x_new)].copy()
            prod_df[value_col] = y_new
        
        # Fit Arps curve
        # ... (implement fitting logic similar to auto_forecast)
        
        print(f"  Successfully processed")
        
    except Exception as e:
        print(f"  Error: {e}")
        continue

# Cell 5: Export Results
results_df = pd.DataFrame(results)
results_df.to_csv('arps_results.csv', index=False)
print(f"Exported {len(results_df)} results to arps_results.csv")
```

### Step 4: Create Streamlit Web App for CSV Upload

Create: `play_assesments_tools/streamlit_csv_app.py`

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from AnalyticsAndDBScripts.csv_loader import CSVDataLoader
from config.config_loader import get_config
import AnalyticsAndDBScripts.prod_fcst_functions as fcst

st.set_page_config(page_title="Arps Decline Curve Analysis", layout="wide")

st.title("🛢️ Arps Decline Curve Analysis - CSV Upload")

# Sidebar for file upload
st.sidebar.header("Upload Data")
production_file = st.sidebar.file_uploader("Production Data CSV", type=['csv'])
well_list_file = st.sidebar.file_uploader("Well List CSV (Optional)", type=['csv'])

if production_file:
    # Save uploaded file temporarily
    with open('/tmp/production_data.csv', 'wb') as f:
        f.write(production_file.getbuffer())
    
    well_list_path = None
    if well_list_file:
        with open('/tmp/well_list.csv', 'wb') as f:
            f.write(well_list_file.getbuffer())
        well_list_path = '/tmp/well_list.csv'
    
    # Initialize loader
    csv_loader = CSVDataLoader(
        production_csv_path='/tmp/production_data.csv',
        well_list_csv_path=well_list_path
    )
    
    # Load data
    try:
        prod_df = csv_loader.load_production_data()
        well_list_df = csv_loader.load_well_list()
        
        st.success(f"✅ Loaded {len(prod_df)} production records for {len(well_list_df)} wells")
        
        # Display summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Wells", well_list_df['WellID'].nunique())
        with col2:
            st.metric("Date Range", f"{prod_df['Date'].min().date()} to {prod_df['Date'].max().date()}")
        with col3:
            st.metric("Total Records", len(prod_df))
        
        # Well selection
        st.header("Select Well for Analysis")
        selected_well = st.selectbox("Well ID", well_list_df['WellID'].unique())
        selected_measure = st.selectbox("Product", ['OIL', 'GAS', 'WATER'])
        
        if st.button("Run Arps Analysis"):
            with st.spinner("Fitting decline curve..."):
                # Get well data
                well_data = well_list_df[
                    (well_list_df['WellID'] == selected_well) &
                    (well_list_df['Measure'] == selected_measure)
                ].iloc[0]
                
                prod_data = csv_loader.get_well_production(
                    wellid=selected_well,
                    measure=selected_measure,
                    last_prod_date=well_data['LastProdDate'],
                    fit_months=60
                )
                
                # Display production plot
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=prod_data['Date'],
                    y=prod_data['Value'],
                    mode='markers',
                    name='Actual Production'
                ))
                fig.update_layout(
                    title=f"Well {selected_well} - {selected_measure} Production",
                    xaxis_title="Date",
                    yaxis_title="Rate (BBL/day or MCF/day)"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # TODO: Add Arps fitting and forecast plotting
                st.info("Arps fitting functionality to be implemented")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
else:
    st.info("👈 Please upload a production data CSV file to begin")
    
    # Show example format
    st.header("Expected CSV Format")
    example_df = pd.DataFrame({
        'WellID': [12345678901, 12345678901, 12345678901],
        'Measure': ['OIL', 'OIL', 'OIL'],
        'Date': ['2023-01-01', '2023-02-01', '2023-03-01'],
        'Value': [150.5, 145.2, 140.8],
        'ProducingDays': [30, 28, 31]
    })
    st.dataframe(example_df)
```

## Usage Instructions

### Option 1: Jupyter Notebook
1. Prepare CSV files in the required format
2. Open `arps_autofit_csv.ipynb` in JupyterLab
3. Update file paths in Cell 3
4. Run all cells
5. Results exported to `arps_results.csv`

### Option 2: Streamlit Web App
1. Run: `streamlit run play_assesments_tools/streamlit_csv_app.py`
2. Upload CSV files via sidebar
3. Select well and product type
4. Click "Run Arps Analysis"
5. View results and download forecasts

### Option 3: Python Script
```python
from AnalyticsAndDBScripts.csv_loader import CSVDataLoader

# Initialize
loader = CSVDataLoader('production_data.csv', 'well_list.csv')

# Get data for specific well
prod_df = loader.get_well_production(
    wellid=12345678901,
    measure='OIL',
    last_prod_date=pd.Timestamp('2024-10-01'),
    fit_months=60
)

# Process with existing functions
# ... (use existing Arps fitting functions)
```

## Benefits of CSV Approach

1. **No Database Required** - Works offline with local files
2. **Easy Data Preparation** - Export from Excel, other databases, or data providers
3. **Version Control** - CSV files can be tracked in Git
4. **Portable** - Share data files easily
5. **Testing** - Create small test datasets quickly
6. **Integration** - Easy to integrate with other tools/workflows

## Migration Path

1. **Phase 1**: Implement CSV loader module (backward compatible)
2. **Phase 2**: Add CSV support to notebooks
3. **Phase 3**: Create Streamlit app for non-technical users
4. **Phase 4**: Add data validation and error handling
5. **Phase 5**: Support hybrid mode (SQL + CSV)

## Next Steps

1. Create `csv_loader.py` module
2. Test with sample CSV data
3. Create example CSV templates
4. Update documentation
5. Add unit tests for CSV loading
