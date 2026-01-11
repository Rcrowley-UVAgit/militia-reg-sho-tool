import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- CONFIGURATION ---
st.set_page_config(page_title="Militia Alpha: Direct Borrow Targeter", layout="wide")

st.markdown("""
<style>
    .reportview-container {background: #0e1117;}
    .metric-card {background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #ff4b4b;}
    h1, h2, h3 {font-family: 'Helvetica Neue', sans-serif; font-weight: 600;}
    .stButton>button {width: 100%; border-radius: 0px; font-weight: bold; border: 1px solid #ff4b4b;}
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def get_sec_headers():
    return {'User-Agent': 'MilitiaApplicant/1.0 (apply@virginia.edu)'}

def fetch_sec_cik(ticker):
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=get_sec_headers())
        data = response.json()
        for entry in data.values():
            if entry['ticker'] == ticker.upper():
                return str(entry['cik_str']).zfill(10)
        return None
    except:
        return None

def score_lender_quality(name):
    name_str = str(name).upper()
    
    tier_1_keywords = ['PENSION', 'RETIREMENT', 'TEACHERS', 'SYSTEM', 'TRUST', 'UNIVERSITY', 'ENDOWMENT']
    tier_2_keywords = ['VANGUARD', 'BLACKROCK', 'STATE STREET', 'FIDELITY']
    
    if any(k in name_str for k in tier_1_keywords):
        return "Tier 1: Sticky/Direct (High Priority)"
    elif any(k in name_str for k in tier_2_keywords):
        return "Tier 2: Passive Aggregator"
    else:
        return "Tier 3: Standard Asset Mgr"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚖️ Legal Engineering")
    st.info("**Objective:** Bypass Prime Broker Spread (50-300bps)")
    st.markdown("### Statutory Basis")
    st.markdown("""
    **Reg SHO Rule 203(b)(1)**
    *Broker-dealer must have reasonable grounds to believe the security can be borrowed.*
    **The Loophole:**
    A "Bona Fide Arrangement" with a direct lender satisfies this requirement without a Prime Broker "Locate."
    """)
    st.divider()
    st.markdown("### Process")
    st.markdown("""
    1. **Identify** Institutional Holders (13F).
    2. **Filter** for Pensions/Trusts.
    3. **Execute** MSLA.
    4. **Log** compliant locate.
    """)
    st.caption("Built by Ryan Crowley - UVA Law '26")

# --- MAIN APP ---
st.title("🛡️ Reg SHO Direct Borrow Targeter")
st.markdown("### Operational Tool: Locate & Compliance Automation")

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    ticker = st.text_input("Target Ticker", value="GME").upper()
with col2:
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik:
            st.success(f"SEC Verified: CIK {cik}")
        else:
            st.warning("Ticker not found in SEC database")

if st.button("RUN ANALYSIS"):
    try:
        with st.spinner(f"Querying 13F Data for {ticker}..."):
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            
            if holders is None or holders.empty:
                st.error("No institutional holding data found. Try a larger cap ticker.")
            else:
                # --- DATA CLEANING PIPELINE ---
                holders = holders.iloc[:, :5]
                holders.columns = ['Holder', 'Shares', 'Date Reported', '% Out', 'Value']
                
                # FIX 1: Force Holder to String
                holders['Holder'] = holders['Holder'].astype(str)
                
                # FIX 2: Force Shares to Number (This fixes the 's' error)
                holders['Shares'] = pd.to_numeric(holders['Shares'], errors='coerce').fillna(0)

                # Filter and Score
                holders['Lending Tier'] = holders['Holder'].apply(score_lender_quality)
                total_shares = holders['Shares'].sum()
                
                # --- DASHBOARD ---
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Float Found", f"{total_shares:,.0f}")
                m2
