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
    # Force string to avoid Timestamp errors
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
                holders = holders.iloc[:, :5] # Take first 5 columns
                holders.columns = ['Holder', 'Shares', 'Date Reported', '% Out', 'Value']
                holders['Holder'] = holders['Holder'].astype(str) # Force text format

                # Filter and Score
                holders['Lending Tier'] = holders['Holder'].apply(score_lender_quality)
                total_shares = holders['Shares'].sum()
                
                # --- DASHBOARD ---
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Float Found", f"{total_shares:,}")
                m2.metric("Counterparties Identified", len(holders))
                m3.metric("Est. Daily Savings (200bps)", f"${(total_shares * 0.02 * 25 / 365):,.0f}")

                st.subheader("🎯 Direct Lending Targets")
                
                # Color code Tier 1
                st.dataframe(
                    holders.style.apply(
                        lambda x: ['background-color: #1e3a2f' if "Tier 1" in v else '' for v in x], 
                        axis=1
                    ),
                    use_container_width=True
                )

                # --- OUTREACH GENERATOR ---
                st.divider()
                st.header("⚡ Execution: MSLA Outreach Generator")
                
                target_fund = st.selectbox("Select Counterparty for Outreach", holders['Holder'].tolist())
                
                email_body = f"""
To: General Counsel, {target_fund}
From: Militia Investments

Re: Direct Stock Borrow Arrangement ({ticker}) - Master Securities Lending Agreement

We have identified {target_fund} as a significant holder of {ticker} via recent 13F filings. 
We are seeking to enter into a direct Master Securities Lending Agreement (MSLA) to borrow {ticker} inventory, bypassing prime brokerage intermediaries. 

**Proposal:**
1. **Collateral:** 102% Cash Collateral (Daily Mark-to-Market)
2. **Fee Split:** We propose a fee split superior to your current Prime Broker lending agent rate.
3. **Regulatory:** This arrangement will serve as a "Bona Fide Arrangement" under Regulation SHO Rule 203(b)(1).

Please verify if your holdings are currently unencumbered and available for direct lending.

Best,
Ryan Crowley
Legal Counsel Candidate
"""
                st.text_area("Draft Legal Correspondence", value=email_body, height=350)
                
                # --- COMPLIANCE LOG ---
                st.divider()
                st.markdown("### 📝 Compliance Audit Trail (Reg SHO)")
                
                tz = pytz.timezone('US/Eastern')
                time_now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S EST")
                
                audit_log = f"""
                [LOG ENTRY GENERATED: {time_now}]
                ------------------------------------------------
                USER: R. Crowley
                ASSET: {ticker}
                ACTION: Direct Locate Identification
                STATUTE: 17 CFR § 242.203(b)(1)(i)
                BASIS: Bona Fide Arrangement identified with {target_fund}.
                STATUS: PENDING MSLA EXECUTION.
                ------------------------------------------------
                """
                st.code(audit_log, language="text")

    except Exception as e:
        st.error(f"An error occurred: {e}")
