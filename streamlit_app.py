"""
Arps Decline Curve Analysis - Streamlit Web Application

This app allows users to upload CSV files and perform Arps decline curve analysis
with interactive visualizations and parameter controls.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
import io

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from AnalyticsAndDBScripts.csv_loader import CSVDataLoader
from AnalyticsAndDBScripts.visualization_utils import plot_decline_curve
import AnalyticsAndDBScripts.prod_fcst_functions as fcst
from config.config_loader import get_config

# Page configuration
st.set_page_config(
    page_title="Arps Decline Curve Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables."""
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'production_df' not in st.session_state:
        st.session_state.production_df = None
    if 'well_list_df' not in st.session_state:
        st.session_state.well_list_df = None
    if 'csv_loader' not in st.session_state:
        st.session_state.csv_loader = None
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    if 'data_valid' not in st.session_state:
        st.session_state.data_valid = False
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'selected_well' not in st.session_state:
        st.session_state.selected_well = None
    if 'selected_measure' not in st.session_state:
        st.session_state.selected_measure = None

init_session_state()

# Header
st.markdown('<div class="main-header">📈 Arps Decline Curve Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Upload CSV data and analyze production decline curves</div>', unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("Navigation")

# Use a different key for the radio button
page = st.sidebar.radio(
    "Go to",
    ["📤 Upload Data", "📊 Run Analysis", "📈 Visualize Results", "💾 Export Data"],
    key="page_selector"
)

# Add info section in sidebar
with st.sidebar.expander("ℹ️ About This App"):
    st.write("""
    This application performs Arps decline curve analysis on oil and gas production data.
    
    **Features:**
    - Upload CSV production data
    - Automatic data validation
    - Interactive decline curve fitting
    - Adjustable parameters
    - Export results
    
    **Required CSV Format:**
    - WellID (integer)
    - Measure (OIL/GAS/WATER)
    - Date (YYYY-MM-DD)
    - Value (production volume)
    - ProducingDays (optional)
    """)

with st.sidebar.expander("📥 Download Sample Data"):
    st.write("Download sample CSV files to test the app:")
    
    # Create sample data buttons
    if st.button("Generate Sample Files"):
        from AnalyticsAndDBScripts.csv_loader import create_sample_csv_files
        
        with st.spinner("Creating sample files..."):
            prod_file, well_file = create_sample_csv_files()
            st.success("✅ Sample files created in project directory!")
            st.info(f"📁 {prod_file}\n📁 {well_file}")

# ============================================================================
# PAGE 1: UPLOAD DATA
# ============================================================================

if page == "📤 Upload Data":
    st.header("📤 Upload Production Data")
    
    st.markdown("""
    Upload your production data CSV file. The file should contain historical production data
    for one or more wells.
    """)
    
    # File upload section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv'],
            help="Upload a CSV file with production data",
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            
            # Save to temporary location
            temp_path = Path("temp_production_data.csv")
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            
            try:
                # Load and validate data
                with st.spinner("Loading and validating data..."):
                    csv_loader = CSVDataLoader(str(temp_path))
                    production_df = csv_loader.load_production_data()
                    well_list_df = csv_loader.load_well_list()
                    
                    # Store in session state
                    st.session_state.csv_loader = csv_loader
                    st.session_state.production_df = production_df
                    st.session_state.well_list_df = well_list_df
                    st.session_state.data_valid = True
                
                # Success message
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.success("✅ Data loaded successfully!")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Display summary statistics
                st.subheader("📊 Data Summary")
                
                col_a, col_b, col_c, col_d = st.columns(4)
                
                with col_a:
                    st.metric("Total Records", f"{len(production_df):,}")
                
                with col_b:
                    st.metric("Unique Wells", production_df['WellID'].nunique())
                
                with col_c:
                    st.metric("Date Range", f"{(production_df['Date'].max() - production_df['Date'].min()).days} days")
                
                with col_d:
                    st.metric("Products", production_df['Measure'].nunique())
                
                # Show data preview
                st.subheader("📋 Data Preview")
                st.dataframe(
                    production_df.head(20),
                    use_container_width=True,
                    height=400
                )
                
                # Show measure breakdown
                st.subheader("📈 Production by Measure")
                measure_counts = production_df['Measure'].value_counts()
                
                col_x, col_y = st.columns(2)
                
                with col_x:
                    st.dataframe(measure_counts, use_container_width=True)
                
                with col_y:
                    # Simple bar chart
                    st.bar_chart(measure_counts)
                
                # Data quality checks
                st.subheader("✅ Data Quality Checks")
                
                issues = csv_loader.validate_data_quality()
                
                if issues['errors']:
                    st.error("❌ Errors found:")
                    for error in issues['errors']:
                        st.write(f"- {error}")
                
                if issues['warnings']:
                    st.warning("⚠️ Warnings:")
                    for warning in issues['warnings']:
                        st.write(f"- {warning}")
                
                if not issues['errors'] and not issues['warnings']:
                    st.success("✅ No data quality issues detected!")
                
                if issues['info']:
                    with st.expander("ℹ️ Additional Information"):
                        for info in issues['info']:
                            st.write(f"- {info}")
                
                # Next steps with button
                st.markdown("---")
                st.subheader("✅ Data Ready!")
                st.write("Your data has been validated and is ready for analysis.")
                st.info("👉 Go to **Run Analysis** in the sidebar to fit decline curves.")
                
            except Exception as e:
                st.session_state.data_valid = False
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.error(f"❌ Error loading data: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.write("**Common issues:**")
                st.write("- Missing required columns (WellID, Measure, Date, Value)")
                st.write("- Invalid date format (use YYYY-MM-DD)")
                st.write("- Invalid Measure values (must be OIL, GAS, or WATER)")
                st.write("- Non-numeric values in Value column")
    
    with col2:
        st.info("""
        **Required Columns:**
        - `WellID` (integer)
        - `Measure` (OIL/GAS/WATER)
        - `Date` (YYYY-MM-DD)
        - `Value` (float)
        
        **Optional:**
        - `ProducingDays` (integer)
        """)
        
        st.markdown("---")
        
        st.write("**Example CSV format:**")
        st.code("""
WellID,Measure,Date,Value,ProducingDays
12345678901,OIL,2023-01-01,150.5,30
12345678901,GAS,2023-01-01,450.0,30
12345678901,WATER,2023-01-01,50.0,30
        """, language="csv")

# ============================================================================
# PAGE 2: RUN ANALYSIS
# ============================================================================

elif page == "📊 Run Analysis":
    st.header("📊 Run Arps Analysis")
    
    if not st.session_state.data_valid:
        st.warning("⚠️ Please upload and validate data first!")
        st.info("👈 Go to **Upload Data** page to get started.")
    else:
        # Load configuration
        config_path = Path(__file__).parent / 'config' / 'analytics_config.yaml'
        params_list = get_config('decline_curve', path=str(config_path))
        
        arps_params = next((item for item in params_list if item['name'] == 'arps_parameters'), None)
        bourdet_params = next((item for item in params_list if item['name'] == 'bourdet_outliers'), None)
        changepoint_params = next((item for item in params_list if item['name'] == 'detect_changepoints'), None)
        b_estimate_params = next((item for item in params_list if item['name'] == 'estimate_b'), None)
        smoothing_params = next((item for item in params_list if item['name'] == 'smoothing'), None)
        method_params = next((item for item in params_list if item['name'] == 'method'), None) or {}
        
        # Sidebar controls
        st.sidebar.header("⚙️ Analysis Parameters")
        
        # Fitting method
        fit_method = st.sidebar.selectbox(
            "Fitting Method",
            ['curve_fit', 'monte_carlo', 'differential_evolution'],
            index=0,
            help="curve_fit is fastest, monte_carlo most robust"
        )
        
        st.sidebar.markdown("---")
        
        # Decline parameters
        st.sidebar.subheader("Decline Parameters")
        
        dei_min = st.sidebar.slider(
            "Min Initial Decline",
            0.0, 1.0,
            float(arps_params['initial_decline'].get('min', 0.3)),
            0.01,
            help="Minimum initial decline rate"
        )
        
        dei_max = st.sidebar.slider(
            "Max Initial Decline",
            0.0, 1.0,
            float(arps_params['initial_decline'].get('max', 0.99)),
            0.01,
            help="Maximum initial decline rate"
        )
        
        # Advanced options
        with st.sidebar.expander("🔧 Advanced Options"):
            fit_months = st.number_input(
                "Fit Months",
                min_value=6,
                max_value=120,
                value=60,
                help="Number of months of history to use for fitting"
            )
            
            outlier_removal = st.checkbox(
                "Remove Outliers (Bourdet)",
                value=bourdet_params['setting'],
                help="Use Bourdet derivative to remove outliers"
            )
            
            changepoint_detection = st.checkbox(
                "Detect Changepoints",
                value=changepoint_params['setting'],
                help="Detect production regime changes"
            )
            
            estimate_b = st.checkbox(
                "Estimate b-factor",
                value=b_estimate_params['setting'],
                help="Estimate b-factor from data (vs. using default)"
            )
        
        # Main content area
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 Wells to Analyze")
            
            # Show well list
            well_list_df = st.session_state.well_list_df
            st.dataframe(
                well_list_df[['WellID', 'Measure', 'LastProdDate']],
                use_container_width=True,
                height=300
            )
            
            st.write(f"**Total:** {len(well_list_df)} well/measure combinations")
        
        with col2:
            st.subheader("🎯 Quick Stats")
            
            st.metric("Wells", well_list_df['WellID'].nunique())
            st.metric("Products", well_list_df['Measure'].nunique())
            
            measure_counts = well_list_df['Measure'].value_counts()
            for measure, count in measure_counts.items():
                st.write(f"**{measure}:** {count}")
        
        st.markdown("---")
        
        # Clear cache button if analysis already complete
        if st.session_state.analysis_complete:
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🔄 Re-run Analysis", type="primary", use_container_width=True, key="rerun_btn"):
                    st.session_state.analysis_complete = False
                    st.session_state.results_df = None
                    st.rerun()
            with col_btn2:
                st.info("Click to clear cached results and re-run with updated code")
        
        # Run analysis button
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True, disabled=st.session_state.analysis_complete):
            
            # Import required modules
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "arps_autofit_csv",
                Path(__file__).parent / "play_assesments_tools" / "python files" / "arps_autofit_csv.py"
            )
            arps_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(arps_module)
            
            process_well_csv = arps_module.process_well_csv
            param_df_cols = arps_module.param_df_cols
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            total_wells = len(well_list_df)
            
            for idx, row in well_list_df.iterrows():
                try:
                    # Update progress
                    progress = (idx + 1) / total_wells
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {idx + 1}/{total_wells}: Well {row['WellID']} - {row['Measure']}")
                    
                    # Process well
                    result = process_well_csv(
                        wellid=row['WellID'],
                        measure=row['Measure'],
                        last_prod_date=row['LastProdDate'],
                        csv_loader=st.session_state.csv_loader,
                        fit_method=fit_method
                    )
                    results.append(result)
                    
                except Exception as e:
                    st.warning(f"⚠️ Well {row['WellID']} - {row['Measure']}: {str(e)}")
                    continue
            
            # Create results DataFrame
            results_df = pd.DataFrame(results, columns=param_df_cols)
            
            # Store in session state
            st.session_state.results_df = results_df
            st.session_state.analysis_complete = True
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
            # Success message
            st.success(f"✅ Analysis complete! Processed {len(results_df)} wells.")
            
            # Show summary
            st.subheader("📊 Results Summary")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric("Total Fits", len(results_df))
            
            with col_b:
                good_fits = (results_df['R_squared'] > 0.8).sum()
                st.metric("Good Fits (R²>0.8)", good_fits)
            
            with col_c:
                avg_r2 = results_df['R_squared'].mean()
                st.metric("Avg R²", f"{avg_r2:.3f}")
            
            with col_d:
                st.metric("Fit Method", fit_method)
            
            # Show results table
            st.subheader("📋 Fitted Parameters")
            display_cols = ['WellID', 'Measure', 'Q3', 'Dei', 'b_factor', 'R_squared']
            display_df = results_df[display_cols].copy()
            display_df['Dei'] = display_df['Dei'].apply(lambda x: f"{x:.3f}")
            display_df['b_factor'] = display_df['b_factor'].apply(lambda x: f"{x:.3f}")
            display_df['R_squared'] = display_df['R_squared'].apply(lambda x: f"{x:.3f}")
            display_df['Q3'] = display_df['Q3'].apply(lambda x: f"{x:.1f}")
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400
            )
            
            # Next step
            st.markdown("---")
            st.info("👉 Go to **Visualize Results** in the sidebar to see decline curves.")
        
        # Show existing results if available
        elif st.session_state.analysis_complete:
            st.info("✅ Analysis already complete. Results available in **Visualize Results** page.")
            
            results_df = st.session_state.results_df
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Total Fits", len(results_df))
            
            with col_b:
                good_fits = (results_df['R_squared'] > 0.8).sum()
                st.metric("Good Fits (R²>0.8)", good_fits)
            
            with col_c:
                avg_r2 = results_df['R_squared'].mean()
                st.metric("Avg R²", f"{avg_r2:.3f}")

# ============================================================================
# PAGE 3: VISUALIZE RESULTS
# ============================================================================

elif page == "📈 Visualize Results":
    st.header("📈 Visualize Decline Curves")
    
    if not st.session_state.analysis_complete:
        st.warning("⚠️ Please run analysis first!")
        st.info("👈 Go to **Run Analysis** page to fit decline curves.")
    else:
        results_df = st.session_state.results_df
        csv_loader = st.session_state.csv_loader
        
        # Sidebar controls
        st.sidebar.header("🎯 Select Well")
        
        # Well selection
        unique_wells = results_df['WellID'].unique()
        selected_well = st.sidebar.selectbox(
            "Well ID",
            unique_wells,
            key="viz_well_select"
        )
        
        # Filter results for selected well
        well_results = results_df[results_df['WellID'] == selected_well]
        
        # Measure selection
        available_measures = well_results['Measure'].unique()
        selected_measure = st.sidebar.selectbox(
            "Product",
            available_measures,
            key="viz_measure_select"
        )
        
        st.sidebar.markdown("---")
        
        # Chart options
        st.sidebar.subheader("📊 Chart Options")
        
        show_forecast = st.sidebar.checkbox("Show Forecast", value=True)
        forecast_months = st.sidebar.slider("Forecast Months", 6, 60, 24)
        
        chart_scale = st.sidebar.radio(
            "Scale",
            ["Linear", "Log", "Both"],
            index=2
        )
        
        # Get result for selected well/measure
        result_row = well_results[well_results['Measure'] == selected_measure].iloc[0]
        
        # Get actual production data
        actual_data = csv_loader.get_well_production(
            wellid=int(selected_well),
            measure=selected_measure,
            last_prod_date=result_row['StartDate'],
            fit_months=120
        )
        
        # Display metrics
        st.subheader(f"📊 Well {selected_well} - {selected_measure}")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Qi (Initial Rate)", f"{result_row['Q3']:.1f}")
        
        with col2:
            st.metric("Dei (Initial Decline)", f"{result_row['Dei']:.1%}")
        
        with col3:
            st.metric("b-factor", f"{result_row['b_factor']:.3f}")
        
        with col4:
            st.metric("R²", f"{result_row['R_squared']:.3f}")
        
        with col5:
            quality = "Excellent" if result_row['R_squared'] > 0.9 else "Good" if result_row['R_squared'] > 0.8 else "Fair"
            st.metric("Fit Quality", quality)
        
        st.markdown("---")
        
        # Generate forecast
        t_months = np.arange(0, len(actual_data) + forecast_months)
        def_val = 0.06 if selected_measure == 'GAS' else 0.08
        
        forecast = fcst.varps_decline(
            int(selected_well), 1,
            result_row['Q3'],
            result_row['Dei'],
            def_val,
            result_row['b_factor'],
            t_months, 0, 0
        )
        
        # Create date range for forecast - convert to list for Plotly compatibility
        start_date = actual_data['Date'].min()
        forecast_dates = pd.date_range(start=start_date, periods=len(t_months), freq='MS').tolist()
        history_end = len(actual_data)
        
        # Convert actual dates to list as well for consistency
        actual_dates = actual_data['Date'].tolist()
        
        # Create interactive Plotly chart
        if chart_scale in ["Linear", "Both"]:
            st.subheader("📈 Linear Scale")
            
            fig_linear = go.Figure()
            
            # Actual production
            fig_linear.add_trace(go.Scatter(
                x=actual_data['Date'],
                y=actual_data['Value'],
                mode='markers',
                name='Actual Production',
                marker=dict(size=8, color='#2E86AB', opacity=0.7),
                hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
            ))
            
            # Fitted curve
            fig_linear.add_trace(go.Scatter(
                x=forecast_dates[:history_end],
                y=forecast[3][:history_end],
                mode='lines',
                name='Arps Fit (History)',
                line=dict(width=3, color='#A23B72'),
                hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
            ))
            
            # Forecast
            if show_forecast:
                fig_linear.add_trace(go.Scatter(
                    x=forecast_dates[history_end:],
                    y=forecast[3][history_end:],
                    mode='lines',
                    name='Arps Forecast (Future)',
                    line=dict(width=3, color='#F18F01', dash='dash'),
                    hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
                ))
            
            fig_linear.update_layout(
                title=f"Well {selected_well} - {selected_measure} Decline Curve",
                xaxis_title="Date",
                yaxis_title=f"{selected_measure} Rate (BBL/day or MCF/day)",
                hovermode='x unified',
                height=500,
                showlegend=True,
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
            )
            
            st.plotly_chart(fig_linear, use_container_width=True)
        
        if chart_scale in ["Log", "Both"]:
            st.subheader("📈 Log Scale")
            
            fig_log = go.Figure()
            
            # Actual production
            fig_log.add_trace(go.Scatter(
                x=actual_data['Date'],
                y=actual_data['Value'],
                mode='markers',
                name='Actual Production',
                marker=dict(size=8, color='#2E86AB', opacity=0.7),
                hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
            ))
            
            # Fitted curve
            fig_log.add_trace(go.Scatter(
                x=forecast_dates[:history_end],
                y=forecast[3][:history_end],
                mode='lines',
                name='Arps Fit (History)',
                line=dict(width=3, color='#A23B72'),
                hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
            ))
            
            # Forecast
            if show_forecast:
                fig_log.add_trace(go.Scatter(
                    x=forecast_dates[history_end:],
                    y=forecast[3][history_end:],
                    mode='lines',
                    name='Arps Forecast (Future)',
                    line=dict(width=3, color='#F18F01', dash='dash'),
                    hovertemplate='Date: %{x}<br>Rate: %{y:.1f}<extra></extra>'
                ))
            
            fig_log.update_layout(
                title=f"Well {selected_well} - {selected_measure} Decline Curve (Log Scale)",
                xaxis_title="Date",
                yaxis_title=f"{selected_measure} Rate (log scale)",
                yaxis_type="log",
                hovermode='x unified',
                height=500,
                showlegend=True,
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
            )
            
            st.plotly_chart(fig_log, use_container_width=True)
        
        # Show data table
        with st.expander("📋 View Production Data"):
            st.dataframe(actual_data, use_container_width=True, height=300)
        
        # Show all results for this well
        with st.expander("📊 All Products for This Well"):
            st.dataframe(
                well_results[['Measure', 'Q3', 'Dei', 'b_factor', 'R_squared', 'RMSE']].round(3),
                use_container_width=True
            )
        
        # Next step
        st.markdown("---")
        st.info("👉 Go to **Export Data** in the sidebar to download results.")

# ============================================================================
# PAGE 4: EXPORT DATA
# ============================================================================

elif page == "💾 Export Data":
    st.header("💾 Export Results")
    
    if not st.session_state.analysis_complete:
        st.warning("⚠️ No results to export yet!")
        st.info("👈 Run analysis first to generate results.")
    else:
        results_df = st.session_state.results_df
        
        st.subheader("📊 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📥 Fitted Parameters")
            st.write("Download all fitted Arps parameters")
            
            # Convert to CSV
            csv = results_df.to_csv(index=False)
            
            st.download_button(
                label="Download Results CSV",
                data=csv,
                file_name="arps_fitted_parameters.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.markdown("### 📈 Forecast Data")
            st.write("Download forecast production data")
            
            # Generate forecast data for all wells
            forecast_data = []
            
            for _, row in results_df.iterrows():
                wellid = int(row['WellID'])
                measure = row['Measure']
                
                # Generate 60-month forecast
                t_months = np.arange(0, 61)
                def_val = 0.06 if measure == 'GAS' else 0.08
                
                forecast = fcst.varps_decline(
                    wellid, 1,
                    row['Q3'],
                    row['Dei'],
                    def_val,
                    row['b_factor'],
                    t_months, 0, 0
                )
                
                # Create DataFrame
                for i in range(len(t_months)):
                    forecast_data.append({
                        'WellID': wellid,
                        'Measure': measure,
                        'Month': int(t_months[i]),
                        'Rate': float(forecast[3][i]),
                        'Cumulative': float(forecast[5][i])
                    })
            
            forecast_df = pd.DataFrame(forecast_data)
            forecast_csv = forecast_df.to_csv(index=False)
            
            st.download_button(
                label="Download Forecast CSV",
                data=forecast_csv,
                file_name="arps_forecast_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col3:
            st.markdown("### 📊 Summary Report")
            st.write("Download analysis summary")
            
            # Create summary report
            summary_lines = []
            summary_lines.append("ARPS DECLINE CURVE ANALYSIS SUMMARY")
            summary_lines.append("=" * 50)
            summary_lines.append(f"\nAnalysis Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
            summary_lines.append(f"\nTotal Wells Analyzed: {results_df['WellID'].nunique()}")
            summary_lines.append(f"Total Fits: {len(results_df)}")
            summary_lines.append(f"\nFit Quality:")
            summary_lines.append(f"  Excellent (R² > 0.9): {(results_df['R_squared'] > 0.9).sum()}")
            summary_lines.append(f"  Good (R² > 0.8): {(results_df['R_squared'] > 0.8).sum()}")
            summary_lines.append(f"  Fair (R² > 0.7): {(results_df['R_squared'] > 0.7).sum()}")
            summary_lines.append(f"\nAverage R²: {results_df['R_squared'].mean():.3f}")
            summary_lines.append(f"Min R²: {results_df['R_squared'].min():.3f}")
            summary_lines.append(f"Max R²: {results_df['R_squared'].max():.3f}")
            summary_lines.append(f"\nBy Product:")
            
            for measure in ['OIL', 'GAS', 'WATER']:
                subset = results_df[results_df['Measure'] == measure]
                if len(subset) > 0:
                    summary_lines.append(f"\n{measure}:")
                    summary_lines.append(f"  Count: {len(subset)}")
                    summary_lines.append(f"  Avg R²: {subset['R_squared'].mean():.3f}")
                    summary_lines.append(f"  Avg Qi: {subset['Q3'].mean():.1f}")
                    summary_lines.append(f"  Avg Dei: {subset['Dei'].mean():.3f}")
                    summary_lines.append(f"  Avg b-factor: {subset['b_factor'].mean():.3f}")
            
            summary_text = "\n".join(summary_lines)
            
            st.download_button(
                label="Download Summary TXT",
                data=summary_text,
                file_name="arps_analysis_summary.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.markdown("---")
        
        # Preview section
        st.subheader("📋 Data Preview")
        
        tab1, tab2 = st.tabs(["Fitted Parameters", "Forecast Sample"])
        
        with tab1:
            st.dataframe(results_df, use_container_width=True, height=400)
        
        with tab2:
            # Show forecast for first well
            sample_well = results_df.iloc[0]
            wellid = int(sample_well['WellID'])
            measure = sample_well['Measure']
            
            t_months = np.arange(0, 61)
            def_val = 0.06 if measure == 'GAS' else 0.08
            
            forecast = fcst.varps_decline(
                wellid, 1,
                sample_well['Q3'],
                sample_well['Dei'],
                def_val,
                sample_well['b_factor'],
                t_months, 0, 0
            )
            
            sample_forecast_df = pd.DataFrame({
                'Month': t_months,
                'Rate': forecast[3],
                'Cumulative': forecast[5]
            })
            
            st.write(f"**Sample:** Well {wellid} - {measure}")
            st.dataframe(sample_forecast_df.head(24), use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    Built with Streamlit | Arps Decline Curve Analysis
</div>
""", unsafe_allow_html=True)
