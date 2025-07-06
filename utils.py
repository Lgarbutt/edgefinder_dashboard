import requests
import pandas as pd

# ✅ Fetch candles from OANDA
def get_oanda_candles(instrument, granularity="H4", count=100,
                      api_key="a50ae073aca76d5be3301ae680fc7637-4bd8d0c37d174ca7b5eeade46783c214",
                      account_id="001-001-3101533-001"):
    url = f"https://api-fxtrade.oanda.com/v3/instruments/{instrument}/candles"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    params = {
        "granularity": granularity,
        "count": count,
        "price": "M"
    }
    r = requests.get(url, headers=headers, params=params)

    if "candles" not in r.json():
        print("❌ ERROR:", r.status_code, r.text)
        return pd.DataFrame()

    data = r.json()
    candles = []
    for c in data.get("candles", []):
        if c["complete"]:
            candles.append({
                "time": c["time"],
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"]),
            })
    return pd.DataFrame(candles)


# ✅ Load COT + Economic data
def load_cot_and_econ_data(excel_file):
    cot_df = pd.read_excel(excel_file, sheet_name="Cleaned Data")
    econ_df = pd.read_excel(excel_file, sheet_name="Economic Raw Data")

    cot_df.columns = cot_df.columns.str.strip()
    econ_df.columns = econ_df.columns.str.strip()

    # Add institutional bias
    if 'Bias' not in cot_df.columns and 'InstNet Position' in cot_df.columns:
        cot_df['Bias'] = cot_df['InstNet Position'].apply(lambda x: 'Bullish' if x > 0 else 'Bearish')

    # Add economic score logic if missing
    if 'Score' not in econ_df.columns:
        def score_row(row):
            score = 0
            if row.get("GDP Growth", 0) > 0.5:
                score += 1
            if row.get("Interest Rate", 0) > 2:
                score += 1
            if row.get("Inflation Rate", 100) < 3:
                score += 1
            if row.get("Jobless Rate", 100) < 5:
                score += 1
            if row.get("Gov. Budget", -100) > -5:
                score += 1
            if row.get("Debt/GDP", 1000) < 100:
                score += 1
            return score
        econ_df["Score"] = econ_df.apply(score_row, axis=1)

    return cot_df, econ_df  # ✅ Move this to the end


# ✅ MACD Trend Bias
def calculate_macd_bias(df):
    if df.empty or len(df) < 10:
        return "Neutral"
    return "Bullish" if df["close"].iloc[-1] > df["close"].mean() else "Bearish"


# ✅ Retail Sentiment from Excel
def get_excel_retail_sentiment(cot_df, selected_pair):
    row = cot_df[cot_df["Currency"] == selected_pair]
    if row.empty:
        return None  # fallback
    long = row["RetLongs"].values[0]
    short = row["RetShorts"].values[0]
    total = long + short
    if total == 0:
        return 50
    return round((long / total) * 100, 1)


# ✅ Final Bias Score Generator
def calculate_bias_score(sentiment_percent, cot_bias, macro_score, tech_bias):
    score = 0

    # Retail Sentiment logic
    if sentiment_percent is not None:
        if sentiment_percent < 50:
            score += 1  # crowd is short, bullish signal

    # Institutional (COT) Bias
    if cot_bias == "Bullish":
        score += 1

    # Technical Bias (MACD)
    if tech_bias == "Bullish":
        score += 1

    # Economic Score
    if macro_score >= 3:
        score += 1
    if macro_score >= 5:
        score += 1

    # Final bias label
    if score >= 4:
        label = "Strong Bullish"
    elif score == 3:
        label = "Bullish"
    elif score == 2:
        label = "Neutral"
    elif score == 1:
        label = "Bearish"
    else:
        label = "Strong Bearish"

    return {
        "bias": label,
        "confidence": score / 5,
        "commentary": f"Bias is {label} based on retail: {sentiment_percent}%, COT: {cot_bias}, Macro score: {macro_score}, Tech: {tech_bias}"
    }
