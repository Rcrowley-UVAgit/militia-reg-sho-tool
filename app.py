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
            
            # --- FIX: Ensure 'holders.empty' is fully written ---
            if holders is None or holders.empty:
                st.error(f"No institutional data found for {ticker}. Try a larger cap stock.")
            else:
                # 2. Process Data
                
                # Check column count and slice to the first 5 if needed
                if holders.shape[1] >= 5:
                    holders = holders.iloc[:, :5]
                    
                holders.columns = ['Holder', 'Shares', 'Date Reported', '% Out', 'Value']

                # Apply the "Militia Filter"
                holders['Lending Tier'] = holders['Holder'].apply(score_lender_quality)
                
                # Sort: Tier 1 first, then by Share count
                holders = holders.sort_values(by=['Lending Tier', 'Shares'], ascending=[True, False])
                
                # 3. Calculate Metrics
                total_shares = holders['Shares'].sum()
                market_value_held = total_shares * current_price
                
                # Assume a 200bps spread saving (Standard for HTB stocks)
                daily_savings = (market_value_held * 0.02) / 360 
                
                # 4. Dashboard Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Float Located", f"{total_shares:,.0f} Shares")
                m2.metric("Market Value Located", f"${market_value_held/1_000_000:,.1f}M")
                m3.metric("Est. Daily Spread Savings (200bps)", f"${daily_savings:,.2f}", help="Savings generated by bypassing PB and borrowing directly.")

                st.subheader("🎯 Prioritized Lending Targets")
                st.caption("Sorted by 'Source Quality' (Tier 1) then Position Size.")
                
                # Display DataFrame
                st.dataframe(
                    holders[['Holder', 'Lending Tier', 'Shares', '% Out']],
                    use_container_width=True,
                    hide_index=True
                )

                # 5. Actionable Work Product
                st.divider()
                st.header("⚡ Execution: MSLA Outreach Generator")
                
                # Select box for the user to choose a target
                target_fund = st.selectbox("Select Counterparty for Outreach", holders['Holder'].tolist())
                
                # Dynamic Legal Email Generation
                email_subject = f"Confidential: Direct Securities Lending Inquiry - {ticker} / {target_fund}"
                email_body = f"""
To: General Counsel / Head of Securities Lending, {target_fund}
From: Militia Investments

Re: Direct Stock Borrow Arrangement ({ticker}) - Master Securities Lending Agreement

We have identified {target_fund} as a significant holder of {ticker} via recent 13F filings. 

We are seeking to enter into a direct Master Securities Lending Agreement (MSLA) to borrow {ticker} inventory, bypassing prime brokerage intermediaries. 

**Value Proposition:**
1. **Fee Split:** We propose a fee split superior to your current Prime Broker lending agent rate.
2. **Collateral:** 102% Cash Collateral (Daily Mark-to-Market).
3. **Regulatory:** This arrangement will serve as a "Bona Fide Arrangement" under Regulation SHO Rule 203(b)(1).

Please verify if your holdings are currently unencumbered and available for direct lending.

Best,
Ryan Crowley
Legal Counsel Candidate
"""
                st.text_area("Draft Legal Correspondence", value=email_body, height=350)
                
                # 6. Compliance Log
                st.divider()
                st.markdown("### 📝 Reg SHO Compliance Audit Trail")
                
                tz = pytz.timezone('US/Eastern')
                time_now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S EST")
                
                audit_log = f"""
[SYSTEM LOG GENERATED: {time_now}]
------------------------------------------------
OPERATOR: R. Crowley
ASSET:    {ticker} (${current_price:.2f})
ACTION:   Direct Locate Identification
STATUTE:  17 CFR § 242.203(b)(1)(i)
TARGET:   {target_fund}
STATUS:   PENDING MSLA EXECUTION.
------------------------------------------------
"""
                st.code(audit_log, language="text")

    except Exception as e:
        st.error(f"An error occurred: {e}")
