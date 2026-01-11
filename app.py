import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Militia Alpha: Direct Borrow Targeter", layout="wide")
st.markdown("""<style>.metric-card {background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #ff4b4b;}
h1, h2, h3 {font-family: 'Helvetica Neue', sans-serif;} .stButton>button {width: 100%; border-radius: 0px; font-weight: bold; border: 1px solid #ff4b4b;}</style>""", unsafe_allow_html=True)

# --- UTILITY FUNCTIONS ---
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
    else: return "Tier 3: Standard Asset Mgr"

# --- SIDEBAR LOGIC ---
with st.sidebar:
    st.header("⚖️ Legal Engineering")
    st.info("**Objective:** Bypass Prime Broker Spread (50-300bps)")
    st.markdown("### Statutory Basis\n**Reg SHO Rule 203(b)(1)**\n*The Loophole:* A 'Bona Fide Arrangement' with a direct lender satisfies locate requirements.")
    st.divider()
    st.markdown("### Process\n1. Identify 13F Holders\n2. Filter Pensions/Trusts\n3. Execute MSLA\n4. Log Locate")
    st.caption("Built by Ryan Crowley - UVA Law '26")

# --- MAIN APP ---
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
            stock = yf.Ticker(
