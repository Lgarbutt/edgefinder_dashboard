import streamlit as st
import pandas as pd
from utils import (
    get_oanda_candles,
    calculate_macd_bias,
    load_cot_and_econ_data,
    calculate_bias_score
)

# --- PAGE SETUP ---
st.set_page_config(page_title="EdgeFinder Dashboard", layout="wide")
st.title("📊 EdgeFinder One-Tab Dashboard")

# --- USER INPUTS ---
pairs = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "AUD_CAD", "USD_CAD",
    "USD_CHF", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP"
]
selected_pair = st.selectbox("Select Currency Pair:", pairs)

# --- PAIR MAPPINGS ---
pair_to_currency = {
    "EUR_USD": ("EUR", "USD"),
    "USD_JPY": ("USD", "JPY"),
    "GBP_USD": ("GBP", "USD"),
    "AUD_USD": ("AUD", "USD"),
    "AUD_CAD": ("AUD", "CAD"),
    "USD_CAD": ("USD", "CAD"),
    "USD_CHF": ("USD", "CHF"),
    "NZD_USD": ("NZD", "USD"),
    "EUR_JPY": ("EUR", "JPY"),
    "GBP_JPY": ("GBP", "JPY"),
    "EUR_GBP": ("EUR", "GBP")
}

pair_to_country = {
    "EUR_USD": ("Euro Area", "United States"),
    "USD_JPY": ("United States", "Japan"),
    "GBP_USD": ("United Kingdom", "United States"),
    "AUD_USD": ("Australia", "United States"),
    "AUD_CAD": ("Australia", "Canada"),
    "USD_CAD": ("United States", "Canada"),
    "USD_CHF": ("United States", "Switzerland"),
    "NZD_USD": ("New Zealand", "United States"),
    "EUR_JPY": ("Euro Area", "Japan"),
    "GBP_JPY": ("United Kingdom", "Japan"),
    "EUR_GBP": ("Euro Area", "United Kingdom")
}

currency1, currency2 = pair_to_currency[selected_pair]
country1, country2 = pair_to_country[selected_pair]

# --- LOAD DATA ---
cot_df, econ_df = load_cot_and_econ_data("COT data.xlsx")


# --- Sentiment and Bias Functions ---
def get_sentiment_stats(currency, col_long, col_short):
    row = cot_df[cot_df["Currency"] == currency]
    if not row.empty:
        longs = int(row[col_long].values[0])
        shorts = int(row[col_short].values[0])
        net = longs - shorts
        bias = "Bullish" if net > 0 else "Bearish"
    else:
        longs = shorts = net = 0
        bias = "Neutral"
    return longs, shorts, net, bias

inst1_longs, inst1_shorts, inst1_net, inst1_bias = get_sentiment_stats(currency1, "InstLongs", "InstShorts")
inst2_longs, inst2_shorts, inst2_net, inst2_bias = get_sentiment_stats(currency2, "InstLongs", "InstShorts")
ret1_longs, ret1_shorts, ret1_net, ret1_bias = get_sentiment_stats(currency1, "RetLongs", "RetShorts")
ret2_longs, ret2_shorts, ret2_net, ret2_bias = get_sentiment_stats(currency2, "RetLongs", "RetShorts")

# --- Economic Score ---
econ_row1 = econ_df[econ_df["Country"] == country1]
econ_row2 = econ_df[econ_df["Country"] == country2]
score1 = econ_row1["Score"].values[0] if not econ_row1.empty else 0
score2 = econ_row2["Score"].values[0] if not econ_row2.empty else 0
econ_score = max(min(6, score1 - score2 + 3), 0)

# --- Technical Bias (MACD) ---
candles = get_oanda_candles(selected_pair, granularity="H4")
macd_bias = calculate_macd_bias(candles)

# --- Final Bias ---
bias_result = calculate_bias_score(
    sentiment_percent=None,
    cot_bias=inst1_bias,
    macro_score=econ_score,
    tech_bias=macd_bias
)

# --- Display Metrics ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🧠 Final Bias", bias_result["bias"])
    st.progress(bias_result["confidence"])

with col3:
    st.markdown("#### 📈 Economic Score")
    st.write(f"Score: {econ_score}/6")
    st.write(f"{country1} Score: {score1} / {country2} Score: {score2}")
    st.markdown("#### 📊 Technical Bias (MACD)")
    st.write(macd_bias)

# --- Economic Table ---
if not econ_row1.empty and not econ_row2.empty:
    st.markdown("---")
    st.markdown("### 🧮 Economic Comparison Table")
    categories = ["GDP Growth", "Interest Rate", "Inflation Rate", "Jobless Rate", "Gov. Budget", "Debt/GDP"]
    econ_table = pd.DataFrame({
        "Category": categories,
        country1: [econ_row1.iloc[0][col] for col in categories],
        country2: [econ_row2.iloc[0][col] for col in categories],
    })
    st.dataframe(econ_table, use_container_width=True)

# --- Sentiment Table ---
st.markdown("### 📊 Institutional & Retail Sentiment Table")
sentiment_df = pd.DataFrame({
    "Entity": ["Institutional", "Institutional", "Retail", "Retail"],
    "Currency": [currency1, currency2, currency1, currency2],
    "Longs": [inst1_longs, inst2_longs, ret1_longs, ret2_longs],
    "Shorts": [inst1_shorts, inst2_shorts, ret1_shorts, ret2_shorts],
    "Net": [inst1_net, inst2_net, ret1_net, ret2_net],
    "Bias": [inst1_bias, inst2_bias, ret1_bias, ret2_bias],
})

def highlight_net(val):
    color = 'blue' if val > 0 else 'red' if val < 0 else 'black'
    return f'color: {color}'

st.dataframe(sentiment_df.style.applymap(highlight_net, subset=["Net"]), use_container_width=True)

# --- TradingView Embed ---
st.components.v1.html(f"""
<iframe src="https://www.tradingview.com/widgetembed/?frameElementId=tradingview_advanced&symbol=OANDA:{selected_pair.replace('_','')}&interval=60&symboledit=1&saveimage=1&toolbarbg=F1F3F6&studies=%5B%22MACD%40tv-basicstudies%22%5D&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&hide_side_toolbar=false&allow_symbol_change=true&details=true&hotlist=true&calendar=true&studies_overrides={{}}&overrides={{}}&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=en" width="1000" height="600" frameborder="0"></iframe>
""", height=600)
