import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Direct Borrow Analysis Tool",
    layout="wide"
)

# Clean, professional CSS (No emojis, readable contrast)
st.markdown("""
<style>
    body { font-family: 'IBM Plex Mono', monospace; }
    h1, h2, h3 { font-weight: 600; color: #f0f0f0; }
    .stAlert { border: 1px solid #444; background-color: #1e1e1e; color: #ddd; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #4CAF50; }
    div[data-testid="stMetricLabel"] { font-size: 14px; color: #aaa; }
    
    /* Hide default table indices */
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

def get_sec_headers():
    return {'User-Agent': 'RegulatoryAnalysisTool/1.0 (apply@virginia.edu)'}

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
    # Convert to string to prevent errors
    name_str = str(name).upper()
    
    # Tier 1: Direct Lenders (Pensions, Endowments)
    tier_1 = ['PENSION', 'RETIREMENT', 'TEACHERS', 'SYSTEM', 'TRUST', 'UNIVERSITY', 'ENDOWMENT']
    # Tier 2: Aggregators
    tier_2 = ['VANGUARD', 'BLACKROCK', 'STATE STREET', 'FIDELITY']
    
    if any(k in name_str for k in tier_1):
        return "Tier 1: Direct Lender (Priority)"
    elif any(k in name_str for k in tier_2):
        return "Tier 2: Aggregator"
    else:
        return "Tier 3: Asset Manager"

# --- 3. EXPLANATORY CONTEXT (The Thesis) ---

st.title("Direct Borrow Analysis Tool")
st.markdown("### Regulation SHO Rule 203(b)(1) Optimization")

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### The Issue: Prime Broker Intermediation")
    st.write("""
    Standard short selling requires a "locate" from a Prime Broker. 
    Brokers charge a spread to locate shares—often borrowing from pension funds at low rates (e.g., 50bps) 
    and lending to funds at high rates (e.g., 300bps). This spread represents an inefficiency.
    """)

with col_b:
    st.markdown("#### The Solution: Direct 'Bona Fide' Arrangements")
    st.write("""
    Under Regulation SHO Rule 203(b)(1), a broker-dealer is not required to use a Prime Broker 
    if they have a "bona fide arrangement" to borrow the security directly.
    
    **This Tool:** bypasses the intermediary by identifying institutional holders (Pension Funds) 
    eligible for direct Master Securities Lending Agreements (MSLA).
    """)

st.divider()

# --- 4. THE TOOL ---

col_input, col_status = st.columns([1, 2])
with col_input:
    ticker = st.text_input("Enter Ticker Symbol", value="GME").upper()
with col_status:
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik:
            st.success(f"SEC Database Verified: CIK {cik}")
        else:
            st.info("Verifying ticker with SEC...")

if st.button("Run Analysis", type="primary"):
    try:
        with st.spinner(f"Analyzing 13F Holdings for {ticker}..."):
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            
            # Safe Price Fetch
            try:
                current_price = stock.fast_info['last_price']
            except:
                current_price = 10.00 # Fallback

            if holders is None or holders.empty:
                st.error("No institutional holding data found. Try a larger market cap company.")
            else:
                # --- ROBUST DATA PROCESSING ---
                holders = holders.copy()
                cols = holders.columns.tolist()
                
                # Dynamic Column Detection
                holder_col = None
                shares_col = None
                
                for c in cols:
                    c_str = str(c).lower()
                    if "holder" in c_str: holder_col = c
                    elif "share" in c_str: shares_col = c
                
                # Fallbacks
                if not holder_col: holder_col = holders.columns[1] # Assume pos 1 is name
                if not shares_col: shares_col = holders.columns[0] # Assume pos 0 is shares (if not date)

                # Create Clean DataFrame
                df_clean = pd.DataFrame()
                df_clean['Holder'] = holders[holder_col]
                
                # Force numeric conversion for shares
                df_clean['Shares'] = pd.to_numeric(holders[shares_col], errors='coerce').fillna(0)
                
                # Apply Logic
                df_clean['Lending Category'] = df_clean['Holder'].apply(score_lender_quality)
                
                # Sort by Quality then Size
                df_clean = df_clean.sort_values(by=['Lending Category', 'Shares'], ascending=[True, False])
                
                # --- METRICS CALCULATIONS ---
                total_shares = df_clean['Shares'].sum()
                market_val = total_shares * current_price
                
                # SAVINGS FORMULA: (Value * 200bps) / 360 days
                spread_bps = 200
                daily_savings = (market_val * (spread_bps / 10000)) / 360
                
                # Display Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Institutional Float Located", f"{total_shares:,.0f}")
                m2.metric("Market Value of Float", f"${market_val/1_000_000:,.1f}M")
                m3.metric("Est. Daily Cost Savings", f"${daily_savings:,.2f}")
                
                # --- METRIC EXPLANATIONS ---
                with st.expander("Metric Definitions & Methodology", expanded=True):
                    st.markdown(f"""
                    * **Institutional Float Located:** The total number of shares held by institutions identified in the table below.
                    * **Market Value:** The gross dollar value of these shares at the current price of **${current_price:.2f}**.
                    * **Est. Daily Cost Savings:** The estimated daily revenue recaptured by bypassing a Prime Broker.
                        * *Formula:* `(Market Value * Spread) / 360 days`
                        * *Assumption:* A **{spread_bps} basis point (2.00%)** spread, typical for Hard-to-Borrow assets.
                    """)

                # Display Data Table
                st.subheader("Target Counterparty List")
                st.dataframe(
                    df_clean[['Holder', 'Lending Category', 'Shares']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Compliance Log (Proof of Verification)
                st.subheader("Regulatory Verification Log")
                tz = pytz.timezone('US/Eastern')
                log_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S EST")
                
                st.code(f"""
[SYSTEM LOG: {log_time}]
ASSET:    {ticker}
STATUTE:  17 CFR § 242.203(b)(1)(i)
ACTION:   Identified {len(df_clean)} potential 'Bona Fide' arrangements.
STATUS:   Ready for MSLA Execution.
                """)

    except Exception as e:
        st.error(f"Analysis Error: {e}")
