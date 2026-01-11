import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- 1. CONFIGURATION & TERMINAL STYLING ---
st.set_page_config(
    page_title="Militia Alpha: Direct Borrow Targeter",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the "Militia" Aesthetic (Dark, Sharp, Professional)
st.markdown("""
<style>
    /* Global Font */
    body { font-family: 'IBM Plex Mono', monospace; }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #4CAF50; /* Terminal Green */
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #fafafa;
        font-weight: 700;
    }
    
    /* Custom divider */
    hr { border-top: 1px solid #333; }
    
    /* Table headers */
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

# --- 2. FIRST PRINCIPLES HELPER FUNCTIONS ---

def get_sec_headers():
    """
    SEC requires a User-Agent with an email. 
    Demonstrates knowledge of API etiquette.
    """
    return {'User-Agent': 'MilitiaApplicant/1.0 (apply@virginia.edu)'}

def fetch_sec_cik(ticker):
    """
    Validates the entity against the SEC official database.
    Proves we verify 'Fundamental Validity' before processing.
    """
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
    """
    ALGORITHM: Identify 'Sticky Capital' vs 'Aggregators'.
    We want direct access to the balance sheet (Pensions/Endowments) 
    to bypass the Prime Broker fee stack.
    """
    name_upper = name.upper()
    
    # Tier 1: The "Source" (Pensions, Endowments, Sovereign Wealth)
    # These are the entities we want to sign an MSLA with directly.
    tier_1_keywords = [
        'PENSION', 'RETIREMENT', 'TEACHERS', 'SYSTEM', 
        'TRUST', 'UNIVERSITY', 'ENDOWMENT', 'BOARD of'
    ]
    
    # Tier 2: The "Aggregators" (Passive Funds)
    # They lend, but usually through an agent (adding a layer of fees).
    tier_2_keywords = ['VANGUARD', 'BLACKROCK', 'STATE STREET', 'FIDELITY', 'CAPITAL GROUP'] 
    
    if any(k in name_upper for k in tier_1_keywords):
        return "Tier 1: DIRECT SOURCE (High Priority)"
    elif any(k in name_upper for k in tier_2_keywords):
        return "Tier 2: Aggregator (Agent Lended)"
    else:
        return "Tier 3: Standard Asset Mgr"

# --- 3. SIDEBAR: THE LEGAL "WHY" ---
with st.sidebar:
    st.title("⚖️ Legal Engineering")
    st.info("**Objective:** Bypass Prime Broker Spread (50-300bps) on hard-to-borrow assets.")
    
    st.markdown("### Statutory Basis")
    st.markdown("""
    **Reg SHO Rule 203(b)(1)**
    *Broker-dealer must have reasonable grounds to believe the security can be borrowed.*
    
    **The Loophole:**
    A **"Bona Fide Arrangement"** with a direct lender satisfies this requirement without a Prime Broker "Locate" or the associated fees.
    """)
    
    st.divider()
    st.markdown("### The Workflow")
    st.markdown("""
    1. **Identify** Institutional Holders (13F).
    2. **Filter** for Sticky Capital (Pensions).
    3. **Execute** Direct MSLA.
    4. **Log** inventory as Reg SHO compliant.
    """)
    st.caption("Built by Ryan Crowley - UVA Law '26")

# --- 4. MAIN APPLICATION ---

st.title("🛡️ Reg SHO Direct Borrow Targeter")
st.markdown("##### Operationalizing Rule 203(b)(1) to cut out middlemen.")
st.divider()

# Input Section
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    ticker = st.text_input("Target Ticker Symbol", value="GME").upper()
with col2:
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik:
            st.success(f"SEC Entity Verified: CIK {cik}")
        else:
            st.warning("Ticker validation pending...")

# Run Analysis
if st.button("INITIATE TARGETING SEQUENCE", type="primary"):
    try:
        with st.spinner(f"Scraping 13F Data and calculating borrow costs for {ticker}..."):
            
            # 1. Get Data
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            
            # Get Current Price for Savings Calculation
            try:
                current_price = stock.fast_info['last_price']
            except:
                current_price = 10.00 # Fallback for safety
            
            if holders is None or holders.
