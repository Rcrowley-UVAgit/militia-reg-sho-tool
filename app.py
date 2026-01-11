import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz
import openai

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Militia Alpha: Direct Borrow Analyst",
    layout="wide"
)

# Professional CSS (Dark Mode, High Contrast)
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
    # Safety: Handle potential non-string inputs from raw data
    name_str = str(name).upper() if name else ""
    
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

def get_ai_analysis(api_key, ticker, holders_df, short_float, news_list):
    """
    Feeds financial data into LLM to generate an investment memo.
    """
    if not api_key:
        return "⚠️ OpenAI API Key missing. Please add it in the sidebar to generate the memo."
    
    # Prepare Context
    top_holders = holders_df.head(5)[['Holder', 'Lending Category', 'Shares']].to_string(index=False)
    news_summary = "\n".join([f"- {n['title']} ({n['publisher']})" for n in news_list[:5]])
    
    prompt = f"""
    You are a Senior Analyst at "Militia Investments," a distressed credit fund. 
    Your ethos: "Cut out middlemen," "First Principles thinking," and "High Agency."
    
    TASK: Write a brief, cynical, and high-insight deal memo on a potential Direct Borrow Short on {ticker}.
    
    DATA CONTEXT:
    1. Short Interest: {short_float}% of Float (Is this crowded? Is a squeeze risk high?)
    2. Supply: We identified these top holders for a direct 'Bona Fide' borrow (bypassing Prime Brokers):
    {top_holders}
    3. Recent News:
    {news_summary}
    
    OUTPUT FORMAT:
    1. **The Setup:** One sentence on why this stock is in play.
    2. **The Friction:** Analyze the short squeeze risk given the float data.
    3. **The Execution:** Specifically recommend which Tier 1 holder to call for the MSLA (Master Securities Lending Agreement).
    4. **Verdict:** "Proceed" or "Pass".
    
    Keep it under 200 words. No fluff.
    """
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4-turbo",  # or gpt-3.5-turbo
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating analysis: {e}"

# --- 3. UI LAYOUT ---

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("OpenAI API Key (for AI Analysis)", type="password")
    st.info("Key is used only for this session and not stored.")
    st.markdown("---")
    st.markdown("**Methodology**")
    st.caption("Identifies 'Sticky Capital' (Pensions) vs 'Flighty Capital' (Hedge Funds) to optimize borrow stability.")

st.title("Militia Alpha: Direct Borrow Analyst")

# Section 1: The Thesis
st.markdown("""
### 1. The "Middleman Tax" Thesis
Standard short selling relies on Prime Brokers who charge massive spreads (e.g., borrow at 50bps, lend at 300bps). 
**The Solution:** Regulation SHO Rule 203(b)(1) allows us to bypass brokers if we secure a "bona fide arrangement" directly with a lender.
""")
st.divider()

# Section 2: Input & Execution
col_input, col_status = st.columns([1, 2])
with col_input:
    ticker = st.text_input("Target Ticker", value="GME").upper()
with col_status:
    if ticker:
        cik = fetch_sec_cik(ticker)
        if cik:
            st.success(f"SEC Database Verified: CIK {cik}")
        else:
            st.warning("Verifying ticker with SEC...")

if st.button("RUN FULL ANALYSIS", type="primary"):
    if not ticker:
        st.error("Please enter a ticker.")
    else:
        try:
            with st.spinner(f"Pulling 13F Data, News, and Short Interest for {ticker}..."):
                # A. Fetch Market Data
                stock = yf.Ticker(ticker)
                
                # 1. Price
                try:
                    current_price = stock.fast_info['last_price']
                except:
                    current_price = 0.0
                
                # 2. Short Interest (Replaces 'Short Ratio' with % of Float if available)
                try:
                    info = stock.info
                    short_float = info.get('shortPercentOfFloat', 0)
                    if short_float:
                        short_float = round(short_float * 100, 2)
                    else:
                        short_float = "N/A"
                except:
                    short_float = "N/A"

                # 3. News Headlines
                try:
                    news_raw = stock.news
                    news_clean = [{'title': n['title'], 'publisher': n['publisher']} for n in news_raw]
                except:
                    news_clean = []

                # 4. Institutional Holders
                holders = stock.institutional_holders
                
                if holders is None or holders.empty:
                    st.error("No institutional data found. Try a larger cap ticker.")
                else:
                    # --- DATA PROCESSING ---
                    holders = holders.copy()
                    
                    # Robust Column Handling
                    cols = [c.lower() for c in holders.columns]
                    # We assume yfinance returns roughly [Holder, Shares, ...]
                    # We force standard names based on position
                    holders_clean = holders.iloc[:, :2].copy()
                    holders_clean.columns = ['Holder', 'Shares']
                    
                    # Clean Types
                    holders_clean['Holder'] = holders_clean['Holder'].astype(str)
                    holders_clean['Shares'] = pd.to_numeric(holders_clean['Shares'], errors='coerce').fillna(0)
                    
                    # Logic: Score Lenders
                    holders_clean['Lending Category'] = holders_clean['Holder'].apply(score_lender_quality)
                    
                    # Sort: Tier 1 (Pensions) First, then by size
                    holders_clean = holders_clean.sort_values(by=['Lending Category', 'Shares'], ascending=[True, False])
                    
                    # Metrics
                    total_shares = holders_clean['Shares'].sum()
                    market_val = total_shares * current_price
                    daily_savings = (market_val * 0.02) / 360 # 200bps spread assumption
                    
                    # --- DISPLAY: METRICS ---
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Institutional Float", f"{total_shares:,.0f}")
                    m2.metric("Market Value", f"${market_val/1_000_000:,.1f}M")
                    m3.metric("Est. Daily Savings", f"${daily_savings:,.0f}")
                    m4.metric("Short % of Float", f"{short_float}%")
                    
                    st.divider()
                    
                    # --- DISPLAY: AI MEMO ---
                    st.header("2. AI Opportunity Memo")
                    if api_key:
                        with st.spinner("Generating Investment Memo..."):
                            memo = get_ai_analysis(api_key, ticker, holders_clean, short_float, news_clean)
                            st.info(memo)
                    else:
                        st.warning("Enter OpenAI API Key in sidebar to generate the Investment Memo.")

                    # --- DISPLAY: TARGET LIST ---
                    st.subheader(f"3. Direct Borrow Targets ({ticker})")
                    st.dataframe(
                        holders_clean[['Holder', 'Lending Category', 'Shares']].style.apply(
                            lambda x: ['background-color: #1e3a2f' if "Tier 1" in v else '' for v in x], 
                            axis=1
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # --- LOG ---
                    tz = pytz.timezone('US/Eastern')
                    st.caption(f"Log: Analysis generated at {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S EST')}")

        except Exception as e:
            st.error(f"Critical Error: {e}")
