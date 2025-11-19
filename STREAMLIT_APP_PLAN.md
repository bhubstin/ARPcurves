# Streamlit App Development Plan
## Arps Decline Curve Analysis - Multi-User Web Application

---

## 🎯 Primary Objectives

1. **CSV Upload & Processing**
   - Drag-and-drop file upload
   - Instant validation and preview
   - Support for production data and well list CSVs

2. **Visualized Decline Curves**
   - Interactive plotly charts (zoom, pan, hover)
   - Linear and log scale views
   - Actual vs. fitted vs. forecast

3. **Multi-User Access**
   - Deploy to Streamlit Community Cloud
   - Accessible from any network/computer
   - Each user has isolated session

4. **Interactive Controls**
   - Well/product selection dropdowns
   - Parameter adjustment sliders
   - Real-time re-fitting

---

## 🏗️ Architecture Design

### **Session Management Strategy**

Based on Streamlit best practices, we'll use `st.session_state` to manage:

```python
st.session_state = {
    'uploaded_file': None,           # User's uploaded CSV
    'production_df': None,           # Parsed production data
    'well_list_df': None,            # Generated well list
    'results_df': None,              # Fitted parameters
    'selected_well': None,           # Current well selection
    'selected_measure': None,        # OIL/GAS/WATER
    'custom_params': {},             # User-adjusted parameters
    'analysis_complete': False       # State tracking
}
```

**Why this matters for multi-user:**
- Each user gets their own session_state
- Data is isolated per browser session
- No interference between users
- Automatic cleanup when user closes browser

### **App Structure**

```
streamlit_app.py (main app)
├── Page 1: Upload & Validate
├── Page 2: Run Analysis
├── Page 3: Visualize Results
└── Page 4: Export & Download
```

---

## 📋 Detailed Feature Specifications

### **Page 1: Upload & Validate**

**Components:**
- File uploader widget (drag-and-drop)
- Data preview table (first 20 rows)
- Validation status indicators
- Sample data download button

**Features:**
```python
# File Upload
uploaded_file = st.file_uploader(
    "Upload Production Data CSV",
    type=['csv'],
    help="Required columns: WellID, Measure, Date, Value",
    on_change=validate_and_load_data
)

# Validation Checks
✓ Required columns present
✓ Data types correct
✓ No null values in critical fields
✓ Date format valid
✓ Measure values valid (OIL/GAS/WATER)
✓ Production values > 0

# Visual Feedback
if validation_passed:
    st.success(f"✅ Loaded {len(df)} records for {n_wells} wells")
else:
    st.error("❌ Validation failed: {error_message}")
```

**Toggles/Filters:**
- ☑️ "Include wells with < 6 months data"
- ☑️ "Auto-remove outliers"
- 📅 Date range selector
- 🔢 Minimum production threshold

### **Page 2: Run Analysis**

**Components:**
- Well selection dropdown (searchable)
- Product type selector (OIL/GAS/WATER or ALL)
- Parameter adjustment panel
- "Run Analysis" button
- Progress bar

**Interactive Parameters:**

```python
# Sidebar Controls
with st.sidebar:
    st.header("Analysis Parameters")
    
    # Fitting Method
    fit_method = st.selectbox(
        "Fitting Method",
        ['curve_fit', 'monte_carlo', 'differential_evolution'],
        help="curve_fit is fastest, monte_carlo most robust"
    )
    
    # Decline Parameters (with sliders)
    dei_min = st.slider("Min Initial Decline", 0.0, 1.0, 0.3)
    dei_max = st.slider("Max Initial Decline", 0.0, 1.0, 0.99)
    
    b_factor_min = st.slider("Min b-factor", 0.0, 2.0, 0.5)
    b_factor_max = st.slider("Max b-factor", 0.0, 2.0, 1.5)
    
    # Advanced Options (collapsible)
    with st.expander("Advanced Options"):
        fit_months = st.number_input("Fit Months", 12, 120, 60)
        outlier_removal = st.toggle("Remove Outliers", value=True)
        changepoint_detection = st.toggle("Detect Changepoints", value=True)
```

**Analysis Workflow:**
1. User selects wells
2. Adjusts parameters (optional)
3. Clicks "Run Analysis"
4. Progress bar shows: "Fitting well 1/10..."
5. Results stored in session_state
6. Auto-navigate to visualization page

### **Page 3: Visualize Results**

**Layout:**

```
┌─────────────────────────────────────────────┐
│  Well Selector  │  Product  │  Fit Quality  │
├─────────────────────────────────────────────┤
│                                             │
│         Interactive Decline Curve           │
│         (Plotly - zoom/pan/hover)          │
│                                             │
├─────────────────────────────────────────────┤
│  Fitted Parameters  │  Goodness of Fit     │
│  Qi: 150.5 BBL/d   │  R²: 0.958          │
│  Dei: 0.25         │  RMSE: 2.3          │
│  b: 0.9            │  MAE: 1.8           │
└─────────────────────────────────────────────┘
```

**Interactive Features:**

```python
# Plotly Chart (interactive by default)
import plotly.graph_objects as go

fig = go.Figure()

# Actual production
fig.add_trace(go.Scatter(
    x=dates, y=actual_values,
    mode='markers',
    name='Actual',
    hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
))

# Fitted curve
fig.add_trace(go.Scatter(
    x=dates, y=fitted_values,
    mode='lines',
    name='Arps Fit',
    line=dict(width=3)
))

# Forecast
fig.add_trace(go.Scatter(
    x=forecast_dates, y=forecast_values,
    mode='lines',
    name='Forecast',
    line=dict(dash='dash')
))

# Interactive controls
fig.update_layout(
    hovermode='x unified',
    dragmode='zoom',
    xaxis=dict(rangeslider=dict(visible=True))
)

st.plotly_chart(fig, use_container_width=True)
```

**Toggles:**
- ☑️ Show/hide forecast
- ☑️ Linear vs. Log scale
- ☑️ Show confidence intervals (if monte_carlo)
- 📊 Chart type: Line / Scatter / Both
- 🎨 Color scheme selector

**Comparison Features:**
- Side-by-side comparison (2-4 wells)
- Overlay multiple products
- Normalize to initial rate

### **Page 4: Export & Download**

**Download Options:**

```python
col1, col2, col3 = st.columns(3)

with col1:
    # Download fitted parameters
    csv = results_df.to_csv(index=False)
    st.download_button(
        "📥 Download Results CSV",
        csv,
        "arps_results.csv",
        "text/csv"
    )

with col2:
    # Download forecast data
    forecast_csv = forecast_df.to_csv(index=False)
    st.download_button(
        "📥 Download Forecast CSV",
        forecast_csv,
        "forecast_data.csv",
        "text/csv"
    )

with col3:
    # Download chart as image
    st.download_button(
        "📥 Download Chart (PNG)",
        chart_bytes,
        "decline_curve.png",
        "image/png"
    )
```

**Report Generation:**
- PDF report with all charts
- Summary statistics table
- Parameter comparison table

---

## 🚀 Deployment Strategy

### **Phase 1: Local Development** (Week 1)
```bash
# Install Streamlit
pip install streamlit plotly

# Run locally
streamlit run streamlit_app.py

# Access at http://localhost:8501
```

### **Phase 2: GitHub Setup** (Week 1)
```bash
# Create GitHub repo
git init
git add .
git commit -m "Initial Streamlit app"
git remote add origin https://github.com/yourusername/arps-analyzer.git
git push -u origin main
```

**Required Files:**
```
repo/
├── streamlit_app.py           # Main app
├── requirements.txt           # Dependencies
├── .streamlit/
│   └── config.toml           # App configuration
├── AnalyticsAndDBScripts/    # Your existing modules
├── config/
│   └── analytics_config.yaml
└── README.md
```

### **Phase 3: Streamlit Cloud Deployment** (Week 1)

**Steps:**
1. Go to https://share.streamlit.io
2. Click "New app"
3. Connect GitHub account
4. Select your repository
5. Set main file: `streamlit_app.py`
6. Click "Deploy"

**Result:**
- Public URL: `https://arps-analyzer.streamlit.app`
- Auto-updates when you push to GitHub
- Free SSL certificate
- Automatic scaling

### **Access Control Options**

**Option A: Public (Free)**
- Anyone with link can access
- No authentication
- Good for: Demos, public tools

**Option B: Email Invites (Free)**
- Invite specific email addresses
- Users need Google/GitHub account
- Good for: Small teams (< 20 people)

**Option C: Password Protection (Requires custom code)**
```python
import streamlit_authenticator as stauth

# Add simple password protection
def check_password():
    def password_entered():
        if st.session_state["password"] == "your_password":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", 
                     on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", 
                     on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if check_password():
    # Show main app
    main_app()
```

---

## 🔧 Technical Implementation Details

### **File Upload Best Practices**

```python
def handle_file_upload(uploaded_file):
    """
    Process uploaded file with proper session state management.
    Each user gets isolated data storage.
    """
    if uploaded_file is not None:
        # Store file in session state
        st.session_state.uploaded_file = uploaded_file
        
        # Read and validate
        try:
            df = pd.read_csv(uploaded_file)
            
            # Validate
            errors = validate_production_data(df)
            
            if not errors:
                st.session_state.production_df = df
                st.session_state.data_valid = True
                st.success(f"✅ Loaded {len(df)} records")
            else:
                st.error(f"❌ Validation errors: {errors}")
                st.session_state.data_valid = False
                
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            st.session_state.data_valid = False
```

### **Performance Optimization**

```python
# Cache expensive operations
@st.cache_data
def load_and_validate_csv(file_bytes):
    """Cache CSV parsing per unique file."""
    df = pd.read_csv(io.BytesIO(file_bytes))
    return df

@st.cache_data
def fit_arps_curve(well_data_hash, params):
    """Cache fitting results per well/params combination."""
    # Expensive Arps fitting here
    return results

# Use st.spinner for long operations
with st.spinner('Fitting decline curves...'):
    results = fit_all_wells(data)
```

### **Multi-User Considerations**

**Session Isolation:**
- ✅ Each browser tab = separate session
- ✅ Data stored in session_state (not global)
- ✅ No database needed for basic use
- ✅ Automatic cleanup on session end

**Scalability:**
- Free tier: ~1GB RAM per app
- Handles ~10-20 concurrent users
- For more users: Upgrade to paid tier or self-host

**Data Privacy:**
- User data never leaves their session
- No permanent storage (unless you add it)
- Files not saved to server
- HTTPS encryption by default

---

## 📊 UI/UX Design Principles

### **Layout Strategy**

```python
# Use columns for side-by-side controls
col1, col2, col3 = st.columns([2, 1, 1])

# Use tabs for different views
tab1, tab2, tab3 = st.tabs(["📈 Chart", "📋 Data", "⚙️ Settings"])

# Use expanders for advanced options
with st.expander("Advanced Parameters"):
    # Less common options here
    pass

# Use sidebar for persistent controls
with st.sidebar:
    # Navigation, filters, settings
    pass
```

### **Visual Hierarchy**

```
┌─────────────────────────────────────────┐
│  LOGO    Arps Decline Curve Analyzer   │ ← Header
├─────────────────────────────────────────┤
│ Sidebar  │  Main Content Area           │
│          │                              │
│ • Upload │  ┌────────────────────────┐ │
│ • Wells  │  │                        │ │
│ • Params │  │    Primary Chart       │ │
│ • Export │  │                        │ │
│          │  └────────────────────────┘ │
│          │                              │
│          │  [Metrics] [Metrics] [...]  │
└─────────────────────────────────────────┘
```

### **Color Scheme**

```python
# Use consistent colors
COLORS = {
    'actual': '#2E86AB',      # Blue
    'fitted': '#A23B72',      # Purple
    'forecast': '#F18F01',    # Orange
    'success': '#06A77D',     # Green
    'error': '#D62246',       # Red
    'neutral': '#6C757D'      # Gray
}
```

---

## 🧪 Testing Plan

### **Local Testing Checklist**

- [ ] Upload valid CSV → Success
- [ ] Upload invalid CSV → Clear error message
- [ ] Select well → Chart updates
- [ ] Adjust parameters → Results change
- [ ] Download results → File downloads correctly
- [ ] Multiple tabs → Sessions isolated
- [ ] Refresh page → State preserved (if desired)

### **Multi-User Testing**

- [ ] Open app in 2 browsers → Independent sessions
- [ ] Upload different files → No interference
- [ ] Concurrent analysis → Both complete successfully

---

## 📦 Deliverables

### **Code Files**
1. `streamlit_app.py` - Main application (500-700 lines)
2. `requirements.txt` - Dependencies
3. `.streamlit/config.toml` - App configuration
4. `README.md` - Deployment instructions

### **Documentation**
1. User guide (how to use the app)
2. Deployment guide (how to deploy)
3. Troubleshooting guide

### **Features**
- ✅ CSV upload with validation
- ✅ Interactive decline curve visualization
- ✅ Parameter adjustment controls
- ✅ Multi-well comparison
- ✅ Results export (CSV, PNG, PDF)
- ✅ Multi-user support
- ✅ Mobile-responsive design

---

## ⏱️ Development Timeline

### **Phase 1: Core Features** (2-3 hours)
- File upload and validation
- Basic Arps fitting
- Simple chart display
- Results table

### **Phase 2: Interactivity** (1-2 hours)
- Parameter sliders
- Well selection
- Interactive plotly charts
- Real-time updates

### **Phase 3: Polish** (1 hour)
- UI/UX improvements
- Error handling
- Loading states
- Help text and tooltips

### **Phase 4: Deployment** (30 minutes)
- GitHub setup
- Streamlit Cloud deployment
- Testing and verification

**Total: 4-6 hours**

---

## 🚀 Next Steps

1. **Approve this plan** - Any changes needed?
2. **Start development** - I'll build the app
3. **Local testing** - You test on your machine
4. **Deploy to cloud** - Make it accessible to others
5. **Share link** - Colleagues can access from anywhere

---

## 💡 Future Enhancements (Optional)

- 🔐 User authentication (password protection)
- 💾 Database integration (save results)
- 📧 Email reports
- 🤖 Batch processing (upload multiple files)
- 📊 Dashboard view (all wells at once)
- 🔔 Notifications (analysis complete)
- 📱 Mobile app version
- 🌐 Multi-language support

---

**Ready to proceed?** Let me know if you want to adjust anything in this plan, or I can start building immediately!
