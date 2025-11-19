# Sample Data for Testing

## 📁 Files Created

Two sample CSV files have been generated for testing:

### 1. `sample_production_data.csv`
**Location:** `/Users/vhoisington/Desktop/Project1/Petroleum-main/sample_production_data.csv`

**Contents:**
- 2 wells with synthetic production data
- 3 products per well (OIL, GAS, WATER)
- 22 months of monthly data (Jan 2023 - Oct 2024)
- Total: 132 records

**Format:**
```csv
WellID,Measure,Date,Value,ProducingDays
12345678901,OIL,2023-01-01,208.42,30
12345678901,GAS,2023-01-01,606.63,30
12345678901,WATER,2023-01-01,53.08,30
...
```

**Columns:**
- `WellID`: Unique well identifier (integer)
- `Measure`: Product type (OIL, GAS, or WATER)
- `Date`: Production date (YYYY-MM-DD format)
- `Value`: Production volume (BBL/day for oil/water, MCF/day for gas)
- `ProducingDays`: Days producing in the month (typically 30)

### 2. `sample_well_list.csv`
**Location:** `/Users/vhoisington/Desktop/Project1/Petroleum-main/sample_well_list.csv`

**Contents:**
- List of well/measure combinations to analyze
- 6 combinations (2 wells × 3 products)

**Format:**
```csv
WellID,Measure,LastProdDate,FitMethod
12345678901,GAS,2024-10-01,curve_fit
12345678901,OIL,2024-10-01,curve_fit
...
```

---

## 🎯 How to Use These Files

### Option 1: Use in Streamlit App

1. **Start the app:**
   ```bash
   cd /Users/vhoisington/Desktop/Project1/Petroleum-main
   source venv/bin/activate
   streamlit run streamlit_app.py
   ```

2. **Upload the file:**
   - Go to "📤 Upload Data" page
   - Drag and drop `sample_production_data.csv`
   - Or click "Browse files" and select it

3. **Run analysis:**
   - Go to "📊 Run Analysis" page
   - Click "🚀 Run Analysis"

4. **View results:**
   - Go to "📈 Visualize Results" page
   - Select well and product
   - See the decline curves!

### Option 2: Use in Python/Jupyter

```python
from AnalyticsAndDBScripts.csv_loader import CSVDataLoader

# Load data
loader = CSVDataLoader('sample_production_data.csv')
production_df = loader.load_production_data()
well_list = loader.load_well_list()

print(f"Loaded {len(production_df)} production records")
print(f"Wells: {production_df['WellID'].nunique()}")
```

---

## 📊 Expected Results

When you analyze this sample data, you should see:

**Well 12345678901 - GAS:**
- Qi (Initial Rate): ~17-18 MCF/day
- Dei (Initial Decline): ~20-25% annual
- b-factor: ~0.9
- R²: >0.95 (Excellent fit)

**Well 12345678901 - OIL:**
- Qi (Initial Rate): ~200-210 BBL/day
- Dei (Initial Decline): ~15-20% annual
- b-factor: ~0.8-1.0
- R²: >0.90 (Good fit)

**Well 98765432109:**
- Similar patterns with different rates

---

## 🔄 Regenerate Sample Data

If you want fresh sample data:

```bash
cd /Users/vhoisington/Desktop/Project1/Petroleum-main
source venv/bin/activate
python -c "from AnalyticsAndDBScripts.csv_loader import create_sample_csv_files; create_sample_csv_files()"
```

This will overwrite the existing sample files with new synthetic data.

---

## 📝 Create Your Own Test Data

You can create a CSV file with your own data. Just follow this format:

**Minimum Required Columns:**
```csv
WellID,Measure,Date,Value
12345678901,OIL,2023-01-01,150.5
12345678901,OIL,2023-02-01,145.2
12345678901,OIL,2023-03-01,140.8
...
```

**Requirements:**
- `WellID`: Any integer
- `Measure`: Must be OIL, GAS, or WATER
- `Date`: YYYY-MM-DD format
- `Value`: Positive number (production rate)
- `ProducingDays`: Optional (will be calculated if missing)

**Tips:**
- Include at least 12 months of data per well
- More data = better fits (24+ months recommended)
- Data should show declining trend
- One row per well/product/date combination

---

## 🎨 Data Characteristics

The sample data simulates realistic decline curves:

**OIL Wells:**
- Initial rate: 150-250 BBL/day
- Decline: Hyperbolic with b ~0.8-1.0
- Terminal decline: 8% annual

**GAS Wells:**
- Initial rate: 500-700 MCF/day
- Decline: Hyperbolic with b ~0.9-1.1
- Terminal decline: 6% annual

**WATER Wells:**
- Initial rate: 30-60 BBL/day
- Decline: Similar to oil
- May show slight increase (water cut)

---

## ✅ File Locations

Both files are in your project root:

```
/Users/vhoisington/Desktop/Project1/Petroleum-main/
├── sample_production_data.csv    ← Upload this one!
├── sample_well_list.csv           ← Optional (auto-generated)
└── streamlit_app.py
```

---

## 🚀 Quick Start

**Right now, you can:**

1. Open Finder
2. Navigate to: `/Users/vhoisington/Desktop/Project1/Petroleum-main/`
3. Find `sample_production_data.csv`
4. This is your test file!

**Or download from terminal:**

```bash
# Copy to Desktop for easy access
cp sample_production_data.csv ~/Desktop/
```

Now you have a file on your Desktop ready to upload! 🎉
