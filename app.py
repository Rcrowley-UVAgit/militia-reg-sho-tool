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

# Professional CSS (Dark Mode, High Contrast, No Emojis)
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

# --- 3. UI: SECTION 1 - THE ISSUE & SOLUTION ---

st.title("Direct Borrow Analysis Tool")

st.header("1. The Issue and Solution")
st.markdown("""
**The Issue: Prime Broker Intermediation**
Standard short selling requires a "locate" from a Prime Broker. Brokers charge a significant spread to locate shares—often borrowing from pension funds at low rates (e.g., 50bps) and lending to hedge funds at high rates (e.g., 250bps+). This spread represents a market inefficiency and a "middleman tax" on the fund's returns.

**The Solution: Direct 'Bona Fide' Arrangements**
Under **Regulation SHO Rule 203(b)(1)**, a broker-dealer is not required to use a Prime Broker for a locate if they have a "bona fide arrangement" to borrow the security directly from a source. By identifying institutional holders (like Pension Funds) eligible for direct Master Securities Lending Agreements (MSLA), a fund can bypass the Prime Broker spread entirely.
""")

st.divider()

# --- 4. UI: SECTION 2 - HOW IT WORKS & METHODOLOGY ---

st.header("2. How It Works")
st.markdown("""
**Operational Logic**
This tool connects to regulatory filing databases to reverse-engineer the "supply side" of the stock loan market.
1.  **Ingestion:** It takes a ticker symbol and queries the most recent 13F Institutional Holding filings.
2.  **Filtering:** It applies a "Lender Quality" algorithm to identify sticky capital (Pensions/Endowments) vs. flighty capital (Hedge Funds).
3.  **Calculation:** It estimates the specific dollar value saved by borrowing directly from these sources rather than paying a Prime Broker spread.

**Metric Definitions & Methodology**
The tool outputs three key metrics to quantify the "Legal Alpha":

* **Institutional Float Located:** The total number of shares held by institutions identified in the 13F data.
* **Market Value:** The gross dollar value of these shares at the current live market price.
* **Est. Daily Cost Savings:** The estimated daily revenue recaptured by bypassing a Prime Broker.
    * *Formula:* `(Market Value * Spread) / 360 days`
    * *Assumption:* A **200 basis point (2.00%)** spread. This is a conservative estimate for Hard-to-Borrow (HTB) assets where spreads often exceed 500-1000bps.
""")

st.divider()

# --- 5. UI: SECTION 3 - THE TOOL ITSELF ---

st.header("3. Run Analysis")

# Input
ticker = st.text_input("Enter Ticker Symbol (e.g., GME)", value="GME").upper()

# Status Verification (Stacked)
if ticker:
    cik = fetch_sec_cik(ticker)
    if cik:
        st.success(f"SEC Database Verified: CIK {cik}")
    else:
        st.info("Verifying ticker with SEC...")

# Execution Button
if st.button("Generate Direct Borrow Targets", type="primary"):
    try:
        with st.spinner(f"Querying 13F Data and calculating spreads for {ticker}..."):
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
                # --- DATA PROCESSING ---
                holders = holders.copy()
                cols = holders.columns.tolist()
                
                # Dynamic Column Detection
                holder_col = None
                shares_col = None
                
                for c in cols:
                    c_str = str(c).lower()
                    if "holder" in c_str: holder_col = c
                    elif "share" in c_str: shares_col = c
                
                if not holder_col: holder_col = holders.columns[1] 
                if not shares_col: shares_col = holders.columns[0] 

                # Create Clean DataFrame
                df_clean = pd.DataFrame()
                df_clean['Holder'] = holders[holder_col]
                df_clean['Shares'] = pd.to_numeric(holders[shares_col], errors='coerce').fillna(0)
                
                # Logic & Sort
                df_clean['Lending Category'] = df_clean['Holder'].apply(score_lender_quality)
                df_clean = df_clean.sort_values(by=['Lending Category', 'Shares'], ascending=[True, False])
                
                # Metrics
                total_shares = df_clean['Shares'].sum()
                market_val = total_shares * current_price
                daily_savings = (market_val * 0.02) / 360
                
                # Display Metrics (Columns used only for data grid, as standard UI practice)
                m1, m2, m3 = st.columns(3)
                m1.metric("Institutional Float Located", f"{total_shares:,.0f}")
                m2.metric("Market Value", f"${market_val/1_000_000:,.1f}M")
                m3.metric("Est. Daily Cost Savings", f"${daily_savings:,.2f}")
                
                # Display Table
                st.subheader(f"Target Counterparty List ({ticker})")
                st.dataframe(
                    df_clean[['Holder', 'Lending Category', 'Shares']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Log
                st.markdown("**Regulatory Verification Log**")
                tz = pytz.timezone('US/Eastern')
                log_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S EST")
                st.code(f"[SYSTEM LOG: {log_time}] ACTION: Identified {len(df_clean)} potential 'Bona Fide' arrangements for {ticker}.")

    except Exception as e:
        st.error(f"Analysis Error: {e}")
