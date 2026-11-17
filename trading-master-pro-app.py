import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# --- App ၏ အပြင်အဆင် သတ်မှတ်ခြင်း ---
st.set_page_config(page_title="Trading Master Pro", page_icon="📈", layout="wide")

# ==========================================
# Language Controller
# ==========================================
st.sidebar.header("⚙️ Settings")
language = st.sidebar.radio("Language / ဘာသာစကား", ["Myanmar (မြန်မာ)", "English"])

def t(mm_text, en_text):
    return mm_text if language == "Myanmar (မြန်မာ)" else en_text

st.title(t("📈 Trading Master Pro", "📈 Trading Master Pro"))
st.markdown("---")

tabs = st.tabs([
    t("📊 1. Technical Analysis", "📊 1. Technical Analysis"),
    t("⚙️ 2. Analysis Back Testing", "⚙️ 2. Analysis Back Testing"),
    t("🌍 3. Fundamental Analysis", "🌍 3. Fundamental Analysis"),
    t("🧠 4. Trading Psychology", "🧠 4. Trading Psychology"),
    t("📓 5. Trading Diary", "📓 5. Trading Diary")
])

tv_symbols = {
    "BTC/USDT": "BINANCE:BTCUSDT",
    "ETH/USDT": "BINANCE:ETHUSDT",
    "XAU/USD": "OANDA:XAUUSD",
    "EUR/USD": "FX:EURUSD",
    "GBP/USD": "FX:GBPUSD",
    "DXY": "TVC:DXY"
}

DIARY_FILE = "trading_diary.csv"

# ==========================================
# Data helpers (no API key needed)
# ==========================================
@st.cache_data(ttl=300)
def fetch_klines(symbol, interval, limit=500):
    """Binance public klines — data-api first, binance.us fallback."""
    urls = [
        f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if isinstance(data, list) and len(data) > 50:
                cols = ["open_time", "open", "high", "low", "close", "volume",
                        "close_time", "qav", "trades", "taker_base", "taker_quote", "ignore"]
                df = pd.DataFrame(data, columns=cols)
                df["close"] = df["close"].astype(float)
                df["open"] = df["open"].astype(float)
                df["high"] = df["high"].astype(float)
                df["low"] = df["low"].astype(float)
                df["volume"] = df["volume"].astype(float)
                df["time"] = pd.to_datetime(df["open_time"], unit="ms")
                return df[["time", "open", "high", "low", "close", "volume"]].copy()
        except Exception:
            continue
    return None

@st.cache_data(ttl=300)
def fetch_yahoo(symbol):
    """Yahoo Finance quote: (price, change_percent) or (None, None)."""
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        meta = r.json()["chart"]["result"][0]["meta"]
        return meta.get("regularMarketPrice"), meta.get("regularMarketChangePercent")
    except Exception:
        return None, None

@st.cache_data(ttl=300)
def fetch_binance_ticker(symbol):
    """24h ticker from Binance public data API."""
    try:
        r = requests.get(
            f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={symbol}",
            timeout=10)
        d = r.json()
        return float(d["lastPrice"]), float(d["priceChangePercent"])
    except Exception:
        return None, None

# ==========================================
# TAB 1: Technical Analysis
# ==========================================
with tabs[0]:
    st.header(t("📊 Technical Analysis (TradingView Interactive Chart)", "📊 Technical Analysis"))

    col1, col2 = st.columns(2)
    with col1:
        selected_pair = st.selectbox(t("Trading Pair ရွေးချယ်ရန်", "Select Trading Pair"), list(tv_symbols.keys()))
    with col2:
        timeframe = st.selectbox(t("Timeframe (မိနစ်)", "Timeframe (Minutes)"), ["15", "60", "240", "D", "W"])

    st.write(t("အောက်ပါ Chart တွင် မျဉ်းဆွဲခြင်း Tool များနှင့် Indicator (အများဆုံး ၂ ခု) ကို အသုံးပြုနိုင်ပါသည်။",
               "You can use drawing tools and up to 2 indicators on the chart below."))

    html_code = f"""
    <div style="height: 600px; width: 100%;">
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "autosize": false,
            "width": "100%",
            "height": 600,
            "symbol": "{tv_symbols[selected_pair]}",
            "interval": "{timeframe}",
            "timezone": "Asia/Yangon",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "backgroundColor": "#131722",
            "gridColor": "#1f293d",
            "hide_top_toolbar": false,
            "hide_legend": false,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "save_image": false,
            "toolbar_bg": "#f1f3f6",
            "studies": [],
            "container_id": "tv_chart_container"
        }});
        </script>
        <div id="tv_chart_container" style="height: 100%; width: 100%;"></div>
    </div>
    """

    components.html(html_code, height=620)

# ==========================================
# TAB 2: Back Testing (real data, EMA crossover)
# ==========================================
with tabs[1]:
    st.header(t("⚙️ Analysis Back Testing", "⚙️ Analysis Back Testing"))
    st.write(t("Binance Data အစစ်ဖြင့် EMA Crossover Strategy ကို စမ်းသပ်ပါ။ Long-only (ဝယ်ရောင်းမဟုတ်၊ ဈေးတက်မှဝယ်၊ ဈေးကျရင် ထွက်တယ်)။",
               "Test an EMA Crossover strategy on real Binance data. Long-only: buy when fast EMA is above slow EMA, exit when it crosses back down."))

    bcol1, bcol2, bcol3, bcol4 = st.columns(4)
    with bcol1:
        bt_pair = st.selectbox(t("Trading Pair", "Trading Pair"), ["BTCUSDT", "ETHUSDT", "SOLUSDT"], key="bt_pair")
    with bcol2:
        bt_tf = st.selectbox(t("Timeframe", "Timeframe"), ["15m", "1h", "4h", "1d"], index=1, key="bt_tf")
    with bcol3:
        ema_fast = st.number_input(t("Fast EMA", "Fast EMA"), min_value=2, max_value=100, value=9, key="ema_fast")
    with bcol4:
        ema_slow = st.number_input(t("Slow EMA", "Slow EMA"), min_value=5, max_value=200, value=21, key="ema_slow")

    bcol5, bcol6 = st.columns(2)
    with bcol5:
        bt_capital = st.number_input(t("စတင်ငွေ (USDT)", "Starting Capital (USDT)"), min_value=10.0, value=1000.0, step=100.0, key="bt_capital")
    with bcol6:
        bt_limit = st.selectbox(t("Candles အရေအတွက်", "Number of Candles"), [200, 500], index=1, key="bt_limit")

    if ema_fast >= ema_slow:
        st.warning(t("Fast EMA က Slow EMA ထက် ငယ်ရမယ်။", "Fast EMA must be smaller than Slow EMA."))
    elif st.button(t("▶️ Backtest စမ်းသပ်ရန်", "▶️ Run Backtest"), key="bt_run"):
        with st.spinner(t("Data ဆွဲနေပါတယ်...", "Fetching data...")):
            df = fetch_klines(bt_pair, bt_tf, limit=int(bt_limit))
        if df is None or len(df) < ema_slow + 10:
            st.error(t("Data ဆွဲမရပါ — အင်တာနက် စစ်ပြီး ထပ်ကြိုးစားပါ။", "Could not fetch data — check your connection and try again."))
        else:
            df["ema_fast"] = df["close"].ewm(span=int(ema_fast), adjust=False).mean()
            df["ema_slow"] = df["close"].ewm(span=int(ema_slow), adjust=False).mean()
            df["position"] = (df["ema_fast"] > df["ema_slow"]).astype(int)
            df["ret"] = df["close"].pct_change().fillna(0)
            df["strat_ret"] = df["position"].shift(1).fillna(0) * df["ret"]
            df["equity"] = float(bt_capital) * (1 + df["strat_ret"]).cumprod()
            df["buy_hold"] = float(bt_capital) * (df["close"] / df["close"].iloc[0])

            # Round-trip trades
            trades = []
            in_trade = False
            entry_price, entry_time = 0.0, None
            for _, row in df.iterrows():
                if row["position"] == 1 and not in_trade:
                    in_trade, entry_price, entry_time = True, row["close"], row["time"]
                elif row["position"] == 0 and in_trade:
                    in_trade = False
                    ret = (row["close"] - entry_price) / entry_price * 100
                    trades.append({"Entry": entry_time, "Exit": row["time"],
                                   "Entry Price": round(entry_price, 2), "Exit Price": round(row["close"], 2),
                                   "Return %": round(ret, 2)})
            open_note = ""
            if in_trade:
                open_note = t(" (လက်ရှိ Trade တစ်ခု ဖွင့်ထားဆဲ — ပိတ်မပြီးသေး)", " (one trade still open — not counted)")

            total_ret = (df["equity"].iloc[-1] / float(bt_capital) - 1) * 100
            bh_ret = (df["buy_hold"].iloc[-1] / float(bt_capital) - 1) * 100
            wins = sum(1 for tr in trades if tr["Return %"] > 0)
            win_rate = (wins / len(trades) * 100) if trades else 0.0
            dd = (df["equity"] - df["equity"].cummax()) / df["equity"].cummax()
            max_dd = dd.min() * 100

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t("Strategy Return", "Strategy Return"), f"{total_ret:.2f}%", f"{df['equity'].iloc[-1]:,.2f} USDT")
            m2.metric(t("Buy & Hold Return", "Buy & Hold Return"), f"{bh_ret:.2f}%")
            m3.metric(t("Win Rate", "Win Rate"), f"{win_rate:.1f}%", f"{wins}/{len(trades)} " + t("ပွဲ", "trades"))
            m4.metric(t("Max Drawdown", "Max Drawdown"), f"{max_dd:.2f}%")

            st.subheader(t("📈 Equity Curve (Strategy vs Buy & Hold)", "📈 Equity Curve (Strategy vs Buy & Hold)"))
            st.line_chart(df.set_index("time")[["equity", "buy_hold"]])
            st.subheader(t("📉 Price + EMA", "📉 Price + EMA"))
            st.line_chart(df.set_index("time")[["close", "ema_fast", "ema_slow"]])

            if trades:
                st.subheader(t("📋 Trades", "📋 Trades") + open_note)
                st.dataframe(pd.DataFrame(trades), use_container_width=True)
            else:
                st.info(t("ဒီကာလအတွင်း Trade တစ်ပွဲမှ မဖြစ်ခဲ့ပါ။", "No completed trades in this period."))
            st.caption(t("⚠️ အတိတ်က ရလဒ်က အနာဂတ် အမြတ်ကို အာမမခံပါ။ Backtest ကို Strategy သင်ယူဖို့ပဲ သုံးပါ။",
                         "⚠️ Past results do not guarantee future profits. Use backtests to learn, not as a promise."))

# ==========================================
# TAB 3: Fundamental Analysis (live data)
# ==========================================
with tabs[2]:
    st.header(t("🌍 Fundamental Analysis", "🌍 Fundamental Analysis"))
    st.write(t("DXY၊ US 10Y Yield၊ BTC နဲ့ ETH ဈေးကို Live ဆွဲပြထားပါတယ်။",
               "Live DXY, US 10Y Yield, BTC and ETH prices."))

    dxy_price, dxy_chg = fetch_yahoo("DX-Y.NYB")
    y10_price, y10_chg = fetch_yahoo("^TNX")
    btc_price, btc_chg = fetch_binance_ticker("BTCUSDT")
    eth_price, eth_chg = fetch_binance_ticker("ETHUSDT")

    f1, f2, f3, f4 = st.columns(4)
    if dxy_price is not None:
        f1.metric(label="DXY (US Dollar Index)", value=f"{dxy_price:.2f}",
                  delta=f"{dxy_chg:+.2f}%" if dxy_chg is not None else None)
    else:
        f1.metric(label="DXY (US Dollar Index)", value="—")
    if y10_price is not None:
        f2.metric(label="US 10Y Yield", value=f"{y10_price:.2f}%",
                  delta=f"{y10_chg:+.2f}%" if y10_chg is not None else None)
    else:
        f2.metric(label="US 10Y Yield", value="—")
    if btc_price is not None:
        f3.metric(label="BTC/USDT (24h)", value=f"${btc_price:,.0f}",
                  delta=f"{btc_chg:+.2f}%" if btc_chg is not None else None)
    else:
        f3.metric(label="BTC/USDT (24h)", value="—")
    if eth_price is not None:
        f4.metric(label="ETH/USDT (24h)", value=f"${eth_price:,.2f}",
                  delta=f"{eth_chg:+.2f}%" if eth_chg is not None else None)
    else:
        f4.metric(label="ETH/USDT (24h)", value="—")

    if dxy_price is None and btc_price is None:
        st.warning(t("Live Data ဆွဲမရပါ — အင်တာနက် စစ်ပြီး စာမျက်နှာကို Refresh လုပ်ပါ။",
                     "Could not fetch live data — check your connection and refresh the page."))
    st.caption(t("အချိန်ကို Yangon Time ဖြင့် ပြထားပါတယ် — ", "Times shown in Yangon Time — ")
               + datetime.now().strftime("%Y-%m-%d %H:%M"))
    st.write(t("DXY တက်ရင် BTC/Gold ဈေး ဖိအားများတတ်ပြီး၊ DXY ကျရင် Risk Asset တွေအတွက် အဆင်ပြေတတ်ပါတယ်။ US 10Y Yield တက်ရင် Dollar အားကောင်းပြီး Crypto အတွက် အနှုတ်လက္ခဏာ ဖြစ်တတ်ပါတယ်။",
               "When DXY rises, BTC/Gold usually face pressure; when DXY falls, risk assets tend to do better. A rising US 10Y Yield usually strengthens the dollar and weighs on crypto."))

# ==========================================
# TAB 4: Trading Psychology (pre-trade checklist)
# ==========================================
with tabs[3]:
    st.header(t("🧠 Trading Psychology", "🧠 Trading Psychology"))
    st.write(t("Trade မလုပ်ခင် ဒီ Checklist ကို အကုန်ဖြည့်ပြီးမှ ဝင်ပါ — တစ်ခုခု ကျန်နေရင် မဝင်တာက ပိုကောင်းပါတယ်။",
               "Complete this checklist before every trade — if anything is unchecked, it is better not to enter."))

    psych_items = [
        t("Stop-loss ထားပြီးပြီ။", "Stop-loss is set."),
        t("Risk:Reward အနည်းဆုံး 1:2 ရှိတယ်။", "Risk:Reward is at least 1:2."),
        t("Position Size တွက်ပြီးပြီ (Risk ≤ 2%)။", "Position size calculated (risk ≤ 2%)."),
        t("Trade Plan ကို ရေးပြီးပြီ။", "Trading plan is written down."),
        t("Revenge Trade မဟုတ်ဘူး။", "This is not a revenge trade."),
        t("FOMO ကြောင့် ဝင်တာ မဟုတ်ဘူး။", "Not entering out of FOMO."),
        t("စိတ်အေးအေးနဲ့ ဆုံးဖြတ်ထားတာ။", "Decided with a calm, clear mind."),
    ]
    checked = 0
    for i, item in enumerate(psych_items):
        if st.checkbox(item, key=f"psych_{i}"):
            checked += 1
    score = checked / len(psych_items) * 100
    st.progress(int(score))
    st.write(t(f"Discipline Score: {score:.0f}% ({checked}/{len(psych_items)})",
               f"Discipline Score: {score:.0f}% ({checked}/{len(psych_items)})"))
    if score == 100:
        st.success(t("✅ အားလုံး ပြည့်စုံပါပြီ — Plan အတိုင်း Trade လုပ်နိုင်ပါတယ်။", "✅ All checks passed — you may trade according to your plan."))
    elif score >= 70:
        st.warning(t("⚠️ နည်းနည်း ကျန်နေသေးတယ် — ကျန်တာကို စစ်ပြီးမှ ဝင်ပါ။", "⚠️ Almost there — finish the remaining checks before entering."))
    else:
        st.error(t("🛑 Checklist မပြည့်သေးပါ — အခု Trade မလုပ်တာ ပိုကောင်းပါတယ်။", "🛑 Checklist incomplete — better not to trade right now."))

# ==========================================
# TAB 5: Trading Diary (saved to CSV file)
# ==========================================
with tabs[4]:
    st.header(t("📓 Trading Diary", "📓 Trading Diary"))

    # Load saved diary once per session
    if "journal_data" not in st.session_state:
        if os.path.exists(DIARY_FILE):
            try:
                st.session_state.journal_data = pd.read_csv(DIARY_FILE).to_dict("records")
            except Exception:
                st.session_state.journal_data = []
        else:
            st.session_state.journal_data = []

    def save_diary():
        pd.DataFrame(st.session_state.journal_data).to_csv(DIARY_FILE, index=False)

    with st.form("diary_form", clear_on_submit=True):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            j_symbol = st.selectbox("Trading Pair", list(tv_symbols.keys()))
            j_type = st.radio("Position Type", ["Buy (Long)", "Sell (Short)"])
        with col_b:
            j_entry = st.number_input("Entry Price", min_value=0.0, format="%.4f")
            j_exit = st.number_input("Exit Price", min_value=0.0, format="%.4f")
        with col_c:
            j_result = st.selectbox("Result", ["Win 🏆", "Loss 💔", "Break Even 🤝"])
            j_setup = st.selectbox("Setup Type", ["Price Action", "SMC"])

        j_notes = st.text_input("Notes")

        submitted = st.form_submit_button(t("💾 မှတ်တမ်းတင်ရန်", "💾 Save to Diary"))
        if submitted:
            if j_entry > 0 and j_exit > 0:
                ret_pct = (j_exit - j_entry) / j_entry * 100
                if j_type.startswith("Sell"):
                    ret_pct = -ret_pct
            else:
                ret_pct = 0.0
            st.session_state.journal_data.append({
                "Pair": j_symbol, "Type": j_type, "Entry": j_entry,
                "Exit": j_exit, "Return %": round(ret_pct, 2),
                "Result": j_result, "Setup": j_setup, "Notes": j_notes
            })
            save_diary()
            st.success(t("မှတ်တမ်းတင်ပြီးပါပြီ — CSV ဖိုင်ထဲလည်း သိမ်းထားပါတယ်။",
                         "Saved! Also stored in the CSV file."))

    if st.session_state.journal_data:
        df_j = pd.DataFrame(st.session_state.journal_data)
        s1, s2, s3 = st.columns(3)
        total = len(df_j)
        wins = (df_j["Result"].astype(str).str.startswith("Win")).sum()
        win_rate = (wins / total * 100) if total else 0.0
        avg_ret = df_j["Return %"].mean() if "Return %" in df_j.columns else 0.0
        s1.metric(t("Total Trades", "Total Trades"), total)
        s2.metric(t("Win Rate", "Win Rate"), f"{win_rate:.1f}%")
        s3.metric(t("Avg Return / Trade", "Avg Return / Trade"), f"{avg_ret:.2f}%")
        st.dataframe(df_j, use_container_width=True)
        st.download_button(
            t("⬇️ Diary CSV Download လုပ်ရန်", "⬇️ Download Diary CSV"),
            data=pd.DataFrame(st.session_state.journal_data).to_csv(index=False).encode("utf-8"),
            file_name="trading_diary.csv", mime="text/csv")
        if st.checkbox(t("မှတ်တမ်းအားလုံး ဖျက်ရန် (အတည်ပြုရန်)", "Delete all records (confirm)"), key="diary_clear_confirm"):
            if st.button(t("🗑️ အကုန်ဖျက်မယ်", "🗑️ Delete All"), key="diary_clear"):
                st.session_state.journal_data = []
                if os.path.exists(DIARY_FILE):
                    os.remove(DIARY_FILE)
                st.rerun()
    else:
        st.info(t("မှတ်တမ်းမရှိသေးပါ — အပေါ်က Form မှာ Trade တစ်ခု ထည့်ပါ။",
                  "No records yet — add a trade in the form above."))
    st.caption(t("⚠️ Diary ကို App နဲ့အတူ CSV ဖိုင်ထဲ သိမ်းထားပါတယ်။ App ကို ပြန်တင်ရင် (redeploy) ပျောက်နိုင်လို့ အခါအားလျော်စွာ Download လုပ်ပြီး သိမ်းထားပါ။",
                 "⚠️ The diary is stored in a CSV file next to the app. It can be lost on redeploy, so download a backup copy from time to time."))
