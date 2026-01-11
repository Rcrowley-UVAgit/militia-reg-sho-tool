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

st.markdown("""
<style>
    body { font-family: 'IBM Plex Mono', monospace; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #4CAF50; }
    h1, h2, h3 { color: #fafafa; font-weight: 700; }
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

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
    # --- FIX 1: SAFETY CAST ---
    # Convert to string immediately to prevent 'Timestamp' errors
    name_str = str(name).upper()
    
    tier_1 = ['PENSION', 'RETIREMENT', 'TEACHERS', 'SYSTEM', 'TRUST', 'UNIVERSITY', 'ENDOWMENT']
    tier_2 = ['VANGUARD', 'BLACKROCK', 'STATE STREET', 'FIDELITY']
    
    if any(k in name_str for k in tier_1):
        return "Tier 1: DIRECT SOURCE (High Priority)"
    elif any(k in name_str for k in tier_2):
        return "Tier 2: Aggregator (Agent Lended)"
    else:
        return "Tier 3: Standard Asset Mgr"

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Legal Engineering")
    st.info("**Objective:** Bypass Prime Broker Spread (50-300bps)")
    st.markdown("""
    **Reg SHO Rule 203(b)(1)**
    *Broker-dealer must have reasonable grounds to believe the security can be borrowed.*
    
    **The Loophole:**
    A **"Bona Fide Arrangement"** with a direct lender satisfies this.
    """)
    st.caption("Built by Ryan Crowley - UVA Law '26")

# --- 4. MAIN APPLICATION ---
st.title("🛡️ Reg SHO Direct Borrow Targeter")
st.markdown("##### Operationalizing Rule 203(b)(1) to cut out middlemen.")
st.divider()

col1, col2 = st.columns([1, 2])
with col1:
    ticker = st.text_input("Target Ticker Symbol", value="GME").upper()
with col2:
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik:
            st.success(f"SEC Verified: CIK {cik}")
        else:
            st.warning("Validating Ticker...")

if st.button("INITIATE TARGETING SEQUENCE", type="primary"):
    try:
        with st.spinner(f"Scraping 13F Data for {ticker}..."):
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            
            # Safe Price Fetch
            try:
                current_price = stock.fast_info['last_price']
            except:
                current_price = 10.00

            if holders is None or holders.empty:
                st.error(f"No data found for {ticker}.")
            else:
                # --- FIX 2: SMART COLUMN MAPPING ---
                # Don't guess column order. Find the 'Holder' column dynamically.
                holders = holders.copy()
                
                # Check current columns
                cols = holders.columns.tolist()
                
                # Heuristic: Find the column that is likely the Name (Object/String) vs Date
                holder_col = None
                shares_col = None
                
                for c in cols:
                    c_lower = str(c).lower()
                    if "holder" in c_lower:
                        holder_col = c
                    elif "share" in c_lower:
                        shares_col = c
                
                # Fallback: If no column named "Holder", look for first string column
                if not holder_col:
                    obj_cols = holders.select_dtypes(include=['object']).columns
                    if len(obj_cols) > 0:
                        holder_col = obj_cols[0]
                    else:
                        # Worst case: Assume col 1 if col 0 is date
                        holder_col = holders.columns[1]

                # Ensure we have a shares column
                if not shares_col:
                     # Look for numeric column
                     num_cols = holders.select_dtypes(include=['int64', 'float64']).columns
                     if len(num_cols) > 0:
                         shares_col = num_cols[0]
                     else:
                         shares_col = holders.columns[2]

                # Standardize DataFrame
                df_clean = pd.DataFrame()
                df_clean['Holder'] = holders[holder_col]
                df_clean['Shares'] = holders[shares_col]
                
                # Score Lenders (Safe Function)
                df_clean['Lending Tier'] = df_clean['Holder'].apply(score_lender_quality)
                
                # Sort
                df_clean = df_clean.sort_values(by=['Lending Tier', 'Shares'], ascending=[True, False])
                
                # Metrics
                total_shares = df_clean['Shares'].sum()
                market_val = total_shares * current_price
                daily_savings = (market_val * 0.02) / 360
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Float Located", f"{total_shares:,.0f}")
                m2.metric("Market Value", f"${market_val/1_000_000:,.1f}M")
                m3.metric("Est. Daily Savings", f"${daily_savings:,.2f}")

                st.subheader("🎯 Prioritized Lending Targets")
                st.dataframe(
                    df_clean[['Holder', 'Lending Tier', 'Shares']], 
                    use_container_width=True, 
                    hide_index=True
                )

                # Execution
                st.divider()
                st.header("⚡ Execution: MSLA Outreach")
                target = st.selectbox("Select Counterparty", df_clean['Holder'].tolist())
                
                email = f"""
To: General Counsel, {target}
Re: Direct Stock Borrow ({ticker}) - Reg SHO Rule 203(b)(1) Bona Fide Arrangement

We have identified {target} as a holder of {ticker}. We propose a direct Master Securities Lending Agreement (MSLA) to bypass prime broker spreads.

- Collateral: 102% Cash
- Compliance: Reg SHO 203(b)(1) Direct Locate
"""
                st.text_area("Draft Correspondence", value=email, height=200)

                # Log
                st.divider()
                tz = pytz.timezone('US/Eastern')
                log = f"""
[LOG: {datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")}]
TARGET: {target}
STATUTE: 17 CFR § 242.203(b)(1)(i)
STATUS: PENDING MSLA
"""
                st.code(log)

    except Exception as e:
        st.error(f"Error: {e}")
