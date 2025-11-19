# 🚀 Streamlit Cloud Deployment Guide

## Prerequisites
- GitHub account
- Streamlit Cloud account (free at https://share.streamlit.io)

## Step-by-Step Deployment

### 1. Push Code to GitHub

```bash
cd /Users/vhoisington/Desktop/Project1/Petroleum-main

# Initialize git if not already done
git init

# Add all files
git add streamlit_app.py
git add requirements_streamlit.txt
git add AnalyticsAndDBScripts/
git add play_assesments_tools/
git add config/
git add .streamlit/

# Commit
git commit -m "Deploy Arps Decline Curve Analyzer to Streamlit Cloud"

# Create a new repository on GitHub (github.com/new)
# Then link it:
git remote add origin https://github.com/YOUR_USERNAME/arps-analyzer.git
git branch -M main
git push -u origin main
```

### 2. Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repository: `YOUR_USERNAME/arps-analyzer`
4. Set these values:
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **Python version**: 3.11 (or 3.10)
   - **Requirements file**: `requirements_streamlit.txt`
5. Click "Deploy!"

### 3. Wait for Deployment (2-5 minutes)

Streamlit Cloud will:
- Clone your repository
- Install dependencies from `requirements_streamlit.txt`
- Start your app
- Provide a public URL like: `https://your-username-arps-analyzer.streamlit.app`

### 4. Share the URL

Once deployed, share the URL with anyone! They can:
- Upload their own CSV files
- Run decline curve analysis
- Visualize results
- Export fitted parameters

## 📝 Important Notes

### File Structure Required for Deployment
```
Petroleum-main/
├── streamlit_app.py                    # Main app file
├── requirements_streamlit.txt          # Dependencies
├── AnalyticsAndDBScripts/
│   ├── csv_loader.py
│   └── prod_fcst_functions.py
├── play_assesments_tools/
│   └── python files/
│       └── arps_autofit_csv.py
└── config/
    ├── config_loader.py
    └── analytics_config.yaml
```

### Troubleshooting

**If deployment fails:**

1. **Check logs** in Streamlit Cloud dashboard
2. **Common issues:**
   - Missing dependencies in `requirements_streamlit.txt`
   - File path issues (use relative paths)
   - Python version incompatibility

3. **Fix and redeploy:**
   ```bash
   git add .
   git commit -m "Fix deployment issue"
   git push
   ```
   Streamlit Cloud will auto-redeploy on push!

### Alternative: Quick Network Sharing (Local)

If you just want to share on your local network temporarily:

```bash
# Find your local IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# Run Streamlit with network access
streamlit run streamlit_app.py --server.address 0.0.0.0
```

Then share: `http://YOUR_LOCAL_IP:8501` with others on the same network.

## 🎉 Success!

Your app is now live and accessible from anywhere in the world!

**Features Available to All Users:**
- ✅ Upload production CSV data
- ✅ Automatic data validation
- ✅ Arps decline curve fitting
- ✅ Interactive visualizations
- ✅ Export results as CSV
- ✅ Multi-user support (each session isolated)
