import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Reg SHO Locate Analysis",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Strict Corporate CSS: No emojis, standard fonts, high legibility
st.markdown("""
<style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #333;
        background-color: #ffffff;
    }
    h1, h2, h3 {
        font-weight: 600;
        color: #0f172a;
        letter-spacing: -0.5px;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border: 1px solid #e9ecef;
        border-radius: 4px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #0f172a;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #64748b;
        font-weight: 500;
    }
    /* Table Styling */
    div[data-testid="stDataFrame"] {
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. REGULATORY & LOGIC HELPER FUNCTIONS ---

def get_sec_headers():
    """Returns compliant headers for SEC EDGAR requests."""
    return {'User-Agent': 'ComplianceMonitor/1.0 (legal_compliance@fund.com)'}

def fetch_sec_cik(ticker):
    """Verifies existence of the issuer in the SEC database."""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=get_sec_headers(), timeout=5)
        data = response.json()
        for entry in data.values():
            if entry['ticker'] == ticker.upper():
                return str(entry['cik_str']).zfill(10)
        return None
    except:
        return None

def classify_counterparty(name):
    """
    Classifies holders to assess 'Stickiness' of capital.
    Beneficial Owners (Pensions) are preferred over Intermediaries for MSLA stability.
    """
    name_str = str(name).upper()
    
    # Priority 1: Beneficial Owners (Sticky Capital)
    beneficial_keywords = [
        'PENSION', 'RETIREMENT', 'TEACHERS', 'SYSTEM', 'TRUST', 
        'UNIVERSITY', 'ENDOWMENT', 'BOARD', 'STATE OF', 'FOUNDATION'
    ]
    
    # Priority 2: Aggregators (Variable Liquidity)
    aggregator_keywords = ['VANGUARD', 'BLACKROCK', 'STATE STREET', 'FIDELITY', 'CAPITAL', 'GROUP']
    
    if any(k in name_str for k in beneficial_keywords):
        return "Class A: Beneficial Owner (Pension/Endowment)"
    elif any(k in name_str for k in aggregator_keywords):
        return "Class B: Asset Aggregator"
    else:
        return "Class C: General Asset Manager"

# --- 3. UI: SECTION 1 - CONTEXT & INPUT ---

st.title("Regulation SHO Rule 203(b)(1) Analysis Tool")
st.markdown("---")

st.subheader("1. Locate Parameters")
col1, col2 = st.columns([1, 2])

with col1:
    ticker = st.text_input("Issuer Ticker Symbol", value="NVDA").upper()
    
with col2:
    st.write("") # Layout spacer
    st.write("") 
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik:
            st.markdown(f"**EDGAR Verification:** Confirmed (CIK: {cik})")
        else:
            st.markdown("**ED
