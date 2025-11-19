# CSV Upload Feature - Quick Start Guide

## Overview

The PlayInsight Suite now supports **CSV file input** as an alternative to SQL database connections. This allows you to perform Arps decline curve analysis using local CSV files.

## ✅ What's Been Implemented

### 1. **CSV Data Loader Module** (`AnalyticsAndDBScripts/csv_loader.py`)
- Loads production data from CSV files
- Validates data format and quality
- Mimics SQL query behavior for compatibility
- Generates sample data for testing

### 2. **CSV-Based Arps Fitting Script** (`play_assesments_tools/python files/arps_autofit_csv.py`)
- Command-line tool for batch processing
- Uses same decline curve algorithms as SQL version
- Outputs results to CSV

### 3. **Jupyter Notebook Example** (`play_assesments_tools/Jupyter Notebooks/arps_csv_example.ipynb`)
- Interactive tutorial
- Data visualization
- Step-by-step analysis workflow

## 📋 Required CSV Format

### Production Data CSV

**Filename:** `production_data.csv`

**Required Columns:**
- `WellID` (integer): Unique well identifier (API number)
- `Measure` (string): "OIL", "GAS", or "WATER"
- `Date` (datetime): Production date (YYYY-MM-DD)
- `Value` (float): Production volume (BBL or MCF)
- `ProducingDays` (integer, optional): Days producing (defaults to 30.42)

**Example:**
```csv
WellID,Measure,Date,Value,ProducingDays
12345678901,OIL,2023-01-01,150.5,30
12345678901,GAS,2023-01-01,450.0,30
12345678901,WATER,2023-01-01,50.0,30
```

### Well List CSV (Optional)

**Filename:** `well_list.csv`

**Columns:**
- `WellID` (integer)
- `Measure` (string)
- `LastProdDate` (datetime, optional)
- `FitMethod` (string, optional): "curve_fit", "monte_carlo", or "differential_evolution"

If not provided, the system will automatically generate a well list from the production data.

## 🚀 Quick Start

### Option 1: Command Line

```bash
# Navigate to project directory
cd /path/to/Petroleum-main

# Activate virtual environment
source venv/bin/activate

# Run analysis
python "play_assesments_tools/python files/arps_autofit_csv.py" \
    production_data.csv \
    --well-list well_list.csv \
    --output results.csv
```

### Option 2: Python Script

```python
from AnalyticsAndDBScripts.csv_loader import CSVDataLoader

# Initialize loader
loader = CSVDataLoader('production_data.csv', 'well_list.csv')

# Load data
prod_df = loader.load_production_data()
well_list = loader.load_well_list()

# Get data for specific well
well_prod = loader.get_well_production(
    wellid=12345678901,
    measure='OIL',
    last_prod_date=pd.Timestamp('2024-10-01'),
    fit_months=60
)
```

### Option 3: Jupyter Notebook

1. Open JupyterLab: `jupyter lab`
2. Navigate to `play_assesments_tools/Jupyter Notebooks/arps_csv_example.ipynb`
3. Run all cells

## 📊 Sample Data

Generate sample CSV files for testing:

```python
from AnalyticsAndDBScripts.csv_loader import create_sample_csv_files

# Creates sample_production_data.csv and sample_well_list.csv
prod_file, well_file = create_sample_csv_files()
```

Or run the CSV loader module directly:

```bash
python AnalyticsAndDBScripts/csv_loader.py
```

## ✅ Validation Results

The CSV implementation has been tested and validated:

- ✅ **CSV loader module**: Successfully loads and validates data
- ✅ **Arps fitting**: Achieves R² > 0.94 on test data
- ✅ **Sample data**: 2 wells, 3 products each, 22 months of history
- ✅ **Output format**: Compatible with existing workflows

### Test Results

```
Processing 6 well/measure combinations...
Processing Well 12345678901 - GAS...  ✓ Completed: R²=0.958
Processing Well 12345678901 - OIL...  ✓ Completed: R²=0.962
Processing Well 12345678901 - WATER... ✓ Completed: R²=0.977
Processing Well 98765432109 - GAS...  ✓ Completed: R²=0.969
Processing Well 98765432109 - OIL...  ✓ Completed: R²=0.985
Processing Well 98765432109 - WATER... ✓ Completed: R²=0.949

✅ Analysis complete!
   Processed: 6 wells
   Successful fits: 6
```

## 📁 Output Format

Results are saved to CSV with the following columns:

- `WellID`: Well identifier
- `Measure`: Product type
- `fit_months`: Months of data used
- `fit_type`: Fitting method used
- `fit_segment`: Segment fitted
- `StartDate`: Start date of fit
- `StartMonth`: Start month integer
- `Q_guess`: Initial rate guess
- `Q3`: Fitted initial rate
- `Dei`: Initial decline rate
- `b_factor`: Hyperbolic exponent
- `R_squared`: Goodness of fit
- `RMSE`: Root mean squared error
- `MAE`: Mean absolute error

## 🔧 Configuration

Decline curve parameters are read from `config/analytics_config.yaml`:

```yaml
decline_curve:
  - name: arps_parameters
    terminal_decline:
      OIL: 0.08
      GAS: 0.06
      WATER: 0.08
    initial_decline:
      guess: 0.5
      max: 0.99
    b_factor:
      OIL:
        min: 0.7
        guess: 1.0
        max: 1.2
```

## 🎯 Use Cases

1. **Offline Analysis**: Work without database connection
2. **Data from External Sources**: Import from Excel, other databases, or data providers
3. **Testing**: Create small test datasets quickly
4. **Sharing**: Easily share data files with colleagues
5. **Version Control**: Track data changes in Git

## 🔄 Migration from SQL

To migrate from SQL-based workflow:

1. **Export production data** from your database to CSV
2. **Export well list** (optional)
3. **Run CSV-based analysis** using the same configuration
4. **Compare results** to validate

The CSV version uses the same algorithms and configuration as the SQL version, ensuring consistent results.

## 📚 Additional Resources

- **Implementation Guide**: `CSV_UPLOAD_IMPLEMENTATION_GUIDE.md`
- **Jupyter Notebook**: `play_assesments_tools/Jupyter Notebooks/arps_csv_example.ipynb`
- **CSV Loader Module**: `AnalyticsAndDBScripts/csv_loader.py`
- **Fitting Script**: `play_assesments_tools/python files/arps_autofit_csv.py`

## 🐛 Troubleshooting

### "Module not found" errors

Install required dependencies:
```bash
pip install pandas numpy scipy scikit-learn ruptures petbox-dca statsmodels pytensor pymc
```

### "Config file not found"

The script looks for `config/analytics_config.yaml` relative to the project root. Ensure you're running from the correct directory.

### Data validation errors

Check that your CSV has:
- Required columns (WellID, Measure, Date, Value)
- Valid Measure values (OIL, GAS, WATER)
- Positive production values
- Proper date format (YYYY-MM-DD)

## 💡 Tips

1. **Start small**: Test with sample data before processing large datasets
2. **Check data quality**: Use `csv_loader.validate_data_quality()` to identify issues
3. **Visualize first**: Plot production data before fitting to identify anomalies
4. **Adjust parameters**: Tune decline parameters in config file for your field
5. **Save results**: Keep fitted parameters for future forecasting

## 🎉 Success!

You now have a fully functional CSV-based Arps decline curve analysis system that works independently of any database!
