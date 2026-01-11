import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- UI & CSS ---
st.set_page_config(page_title="Militia Alpha: Direct Borrow Targeter", layout="wide")
st.markdown("""<style>.metric-card {background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #ff4b4b;}
h1, h2, h3 {font-family: 'Helvetica Neue', sans-serif;} .stButton>button {width: 100%; border-radius: 0px; font-weight: bold; border: 1px solid #ff4b4b;}</style>""", unsafe_allow_html=True)

# --- UTILITIES ---
def get_sec_headers():
    return {'User-Agent': 'MilitiaApplicant/1.0 (apply@virginia.edu)'}

def fetch_sec_cik(ticker):
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=get_sec_headers())
        data = response.json()
        for entry in data.values():
            if entry['ticker'] == ticker.upper(): return str(entry['cik_str']).zfill(10)
        return None
    except: return None

def score_lender_quality(name):
    name_str = str(name).upper()
    t1 = ['PENSION', 'RETIREMENT', 'TEACHERS', 'SYSTEM', 'TRUST', 'UNIVERSITY', 'ENDOWMENT']
    t2 = ['VANGUARD', 'BLACKROCK', 'STATE STREET', 'FIDELITY']
    if any(k in name_str for k in t1): return "Tier 1: Sticky/Direct (High Priority)"
    elif any(k in name_str for k in t2): return "Tier 2: Passive Aggregator"
    return "Tier 3: Standard Asset Mgr"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚖️ Legal Engineering")
    st.info("**Objective:** Bypass Prime Broker Spread (50-300bps)")
    st.markdown("### Statutory Basis\n**Reg SHO Rule 203(b)(1)**\n*The Loophole:* A 'Bona Fide Arrangement' with a direct lender satisfies locate requirements.")
    st.divider()
    st.markdown("### Process\n1. Identify 13F Holders\n2. Filter Pensions/Trusts\n3. Execute MSLA\n4. Log Locate")
    st.caption("Built by Ryan Crowley - UVA Law '26")

# --- MAIN ---
st.title("🛡️ Reg SHO Direct Borrow Targeter")
st.markdown("### Operational Tool: Locate & Compliance Automation")

col1, col2 = st.columns([1, 2])
with col1:
    ticker = st.text_input("Target Ticker", value="GME").upper()
with col2:
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik: st.success(f"SEC Verified: CIK {cik}")
        else: st.warning("Ticker not found in SEC database")

if st.button("RUN ANALYSIS"):
    try:
        with st.spinner(f"Analyzing {ticker}..."):
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            if holders is None or holders.empty:
                st.error("No institutional data found.")
            else:
                # Data Pipeline
                holders = holders.iloc[:, :5]
                holders.columns = ['Holder', 'Shares', 'Date Reported', '% Out', 'Value']
                holders['Holder'] = holders['Holder'].astype(str)
                holders['Shares'] = pd.to_numeric(holders['Shares'], errors='coerce').fillna(0)
                holders['Lending Tier'] = holders['Holder'].apply(score_lender_quality)
                total_shares = holders['Shares'].sum()
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Float Found", f"{total_shares:,.0f}")
                m2.metric("Counterparties", len(holders))
                m3.metric("Est. Savings (200bps)", f"${(total_shares * 0.02 * 25 / 365):,.0f}")

                st.subheader("🎯 Direct Lending Targets")
                st.dataframe(holders.style.apply(lambda x: ['background-color: #1e3a2f' if "Tier 1" in v else '' for v in x], axis=1), use_container_width=True)

                # Outreach
                st.divider()
                st.header("⚡ Execution: MSLA Outreach Generator")
                target_fund = st.selectbox("Select Counterparty", holders['Holder'].tolist())
                email_body = f"To: General Counsel, {target_fund}\nFrom: Militia Investments\n\nRe: Direct Stock Borrow Arrangement ({ticker})\n\nWe seek to enter a direct MSLA to bypass prime brokerage intermediaries under Reg SHO Rule 203(b)(1).\n\nBest,\nRyan Crowley"
                st.text_area("Draft Legal Correspondence", value=email_body, height=200)
                
                # Audit
                st.divider()
                st.markdown("### 📝 Compliance Audit Trail")
                tz = pytz.timezone('US/Eastern')
                audit_log = f"[{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S EST')}]\nUSER: R. Crowley\nASSET: {ticker}\nSTATUTE: 17 CFR § 242.203(b)(1)(i)\nSTATUS: PENDING MSLA."
                st.code(audit_log, language="text")
    except Exception as e:
        st.error(f"Error: {e}")
