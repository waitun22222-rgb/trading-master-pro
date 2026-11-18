import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import os
import xml.etree.ElementTree as ET
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
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
    t("🌍 2. Fundamental Analysis", "🌍 2. Fundamental Analysis"),
    t("🧠 3. Trading Psychology", "🧠 3. Trading Psychology"),
    t("📓 4. Trading Diary", "📓 4. Trading Diary")
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
DIARY_IMG_DIR = "diary_images"

# ==========================================
# Data helpers (no API key needed)
# ==========================================
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

@st.cache_data(ttl=600)
def fetch_fear_greed():
    """Crypto Fear & Greed Index: (value, classification) or (None, None)."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        d = r.json()["data"][0]
        return int(d["value"]), d["value_classification"]
    except Exception:
        return None, None

@st.cache_data(ttl=600)
def fetch_news(query, n=4):
    """Google News RSS: list of (title, source, time_yangon, link)."""
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        root = ET.fromstring(r.content)
        out = []
        for it in root.findall(".//item")[:n]:
            title = (it.findtext("title", "") or "").strip()
            link = (it.findtext("link", "") or "").strip()
            src = (it.findtext("source", "") or "").strip()
            pub = (it.findtext("pubDate", "") or "").strip()
            try:
                when = parsedate_to_datetime(pub).astimezone(ZoneInfo("Asia/Yangon")).strftime("%m-%d %H:%M")
            except Exception:
                when = pub
            if title and link:
                out.append((title[:110], src, when, link))
        return out
    except Exception:
        return []

# ==========================================
# TAB 1: Technical Analysis (do everything inside the chart)
# ==========================================
with tabs[0]:
    st.header(t("📊 Technical Analysis (TradingView Interactive Chart)", "📊 Technical Analysis"))

    html_code = """
    <div id="tv_wrap" style="width: 100%; background:#131722; position:relative;">
        <style>
          #tv_wrap.fs-landscape #tv_bar { display: none; }
          #tv_wrap.fs-landscape #tv_chart_container {
            position: absolute; top: 50%; left: 50%;
            width: 100vh; height: 100vw;
            transform: translate(-50%, -50%) rotate(90deg);
          }
        </style>
        <div id="tv_bar" style="display:flex; justify-content:flex-end; padding:6px 8px;">
            <button id="tv_fs" style="background:#2a2e39; color:#fff; border:1px solid #555; border-radius:6px; padding:5px 12px; font-size:13px; cursor:pointer;">⛶ Fullscreen</button>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({
            "autosize": true,
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
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
            "save_image": true,
            "toolbar_bg": "#f1f3f6",
            "studies": [],
            "container_id": "tv_chart_container"
        });
        (function(){
          var wrap = document.getElementById('tv_wrap');
          document.addEventListener('fullscreenchange', function(){
            if (document.fullscreenElement) {
              if (window.innerHeight > window.innerWidth) {
                if (screen.orientation && screen.orientation.lock) {
                  screen.orientation.lock('landscape').then(function(){
                    if (screen.orientation.type.indexOf('landscape') !== 0) { wrap.classList.add('fs-landscape'); }
                  }).catch(function(){ wrap.classList.add('fs-landscape'); });
                } else {
                  wrap.classList.add('fs-landscape');
                }
              }
            } else {
              wrap.classList.remove('fs-landscape');
            }
          });
          document.getElementById('tv_fs').addEventListener('click', function(){
            if (wrap.requestFullscreen) { wrap.requestFullscreen().catch(function(){}); }
            else if (wrap.webkitRequestFullscreen) { wrap.webkitRequestFullscreen(); }
          });
        })();
        </script>
        <div id="tv_chart_container" style="height: 600px; width: 100%;"></div>
    </div>
    """

    components.html(html_code, height=640)

# ==========================================
# TAB 2: Fundamental Analysis (live data)
# ==========================================
with tabs[1]:
    st.header(t("🌍 Fundamental Analysis", "🌍 Fundamental Analysis"))
    st.write(t("Trade မလုပ်ခင် ဒီ Dashboard ကို တစ်ချက်ကြည့်ပါ — ဈေးကွက် အခြေအနေ တစ်ခုလုံး ခြုံငုံမိသွားမယ်။",
               "Check this dashboard before trading — it shows the whole market picture at a glance."))

    dxy_price, dxy_chg = fetch_yahoo("DX-Y.NYB")
    y10_price, y10_chg = fetch_yahoo("^TNX")
    btc_price, btc_chg = fetch_binance_ticker("BTCUSDT")
    eth_price, eth_chg = fetch_binance_ticker("ETHUSDT")
    spx_price, spx_chg = fetch_yahoo("^GSPC")
    ndx_price, ndx_chg = fetch_yahoo("^IXIC")
    gold_price, gold_chg = fetch_yahoo("GC=F")
    vix_price, vix_chg = fetch_yahoo("^VIX")
    fng_value, fng_class = fetch_fear_greed()

    def show_metric(col, label, price, chg, fmt="{:,.2f}", suffix=""):
        if price is not None:
            col.metric(label=label, value=fmt.format(price) + suffix,
                       delta=f"{chg:+.2f}%" if chg is not None else None)
        else:
            col.metric(label=label, value="—")

    st.subheader(t("💵 Dollar & Bonds", "💵 Dollar & Bonds"))
    r1c1, r1c2 = st.columns(2)
    show_metric(r1c1, "DXY (US Dollar Index)", dxy_price, dxy_chg)
    show_metric(r1c2, "US 10Y Yield", y10_price, y10_chg, suffix="%")
    st.caption(t("DXY တက်ရင် BTC/Gold ဖိအားများတယ်။ 10Y Yield တက်ရင် Dollar အားကောင်းပြီး Crypto အတွက် အနှုတ်လက္ခဏာ ဖြစ်တတ်တယ်။",
                 "A rising DXY pressures BTC/Gold. A rising 10Y Yield strengthens the dollar and usually weighs on crypto."))

    st.subheader(t("🪙 Crypto", "🪙 Crypto"))
    r2c1, r2c2, r2c3 = st.columns(3)
    show_metric(r2c1, "BTC/USDT (24h)", btc_price, btc_chg, fmt="${:,.0f}")
    show_metric(r2c2, "ETH/USDT (24h)", eth_price, eth_chg, fmt="${:,.2f}")
    if fng_value is not None:
        r2c3.metric(label=t("Fear & Greed Index", "Fear & Greed Index"),
                    value=f"{fng_value} — {fng_class}")
    else:
        r2c3.metric(label=t("Fear & Greed Index", "Fear & Greed Index"), value="—")
    st.caption(t("Fear & Greed: 0-25 Extreme Fear (လူတွေ ကြောက်ပြီး ရောင်းနေချိန် — သတိထားဝယ်ဖို့ အခွင့်အရေး ဖြစ်တတ်တယ်)၊ 75-100 Extreme Greed (လူတွေ အရမ်းပျော်နေချိန် — သတိထားရမယ့်အချိန်)။",
                 "Fear & Greed: 0-25 Extreme Fear (panic selling — often a careful buying opportunity), 75-100 Extreme Greed (euphoria — time to be careful)."))

    st.subheader(t("📈 US Stocks & Gold", "📈 US Stocks & Gold"))
    r3c1, r3c2, r3c3, r3c4 = st.columns(4)
    show_metric(r3c1, "S&P 500", spx_price, spx_chg)
    show_metric(r3c2, "Nasdaq", ndx_price, ndx_chg)
    show_metric(r3c3, "Gold (XAU/USD)", gold_price, gold_chg, fmt="${:,.2f}")
    show_metric(r3c4, "VIX (Fear Index)", vix_price, vix_chg)
    st.caption(t("S&P 500 / Nasdaq ကျရင် Crypto လည်း အတူလိုက်ကျတတ်တယ်။ VIX 20 အထက်ဆိုရင် ဈေးကွက် ကြောက်နေပြီလို့ ဆိုလိုတယ်။ Gold တက်နေရင် လူတွေ Safe Haven ရှာနေတယ်လို့ အဓိပ္ပာယ်ရတယ်။",
                 "When S&P 500 / Nasdaq fall, crypto often follows. VIX above 20 means the market is fearful. Rising gold means people are seeking a safe haven."))

    if dxy_price is None and btc_price is None:
        st.warning(t("Live Data ဆွဲမရပါ — အင်တာနက် စစ်ပြီး စာမျက်နှာကို Refresh လုပ်ပါ။",
                     "Could not fetch live data — check your connection and refresh the page."))
    st.caption(t("အချိန်ကို Yangon Time ဖြင့် ပြထားပါတယ် — ", "Times shown in Yangon Time — ")
               + datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.subheader(t("📰 အရေးကြီးသတင်း", "📰 Important News"))
    ncol1, ncol2 = st.columns(2)
    with ncol1:
        st.write(t("🪙 Crypto သတင်း", "🪙 Crypto News"))
        crypto_news = fetch_news("Bitcoin OR Ethereum OR crypto market", 4)
        if crypto_news:
            for title, src, when, link in crypto_news:
                st.markdown(f"- [{title}]({link})  \n  *{src} · {when}*")
        else:
            st.write(t("သတင်း ဆွဲမရပါ။", "Could not load news."))
    with ncol2:
        st.write(t("📈 Stocks & Fed သတင်း", "📈 Stocks & Fed News"))
        stock_news = fetch_news("stock market OR Federal Reserve OR Nvidia", 4)
        if stock_news:
            for title, src, when, link in stock_news:
                st.markdown(f"- [{title}]({link})  \n  *{src} · {when}*")
        else:
            st.write(t("သတင်း ဆွဲမရပါ။", "Could not load news."))

# ==========================================
# TAB 3: Trading Psychology (daily tip + pre-trade checklist)
# ==========================================
with tabs[2]:
    st.header(t("🧠 Trading Psychology", "🧠 Trading Psychology"))

    daily_tips = [
        ("Trade တစ်ပွဲမှာ Risk 1-2% ပဲ ယူပါ။ တစ်ပွဲတည်း များများရှုံးရင် ပြန်ကောက်ဖို့ အရမ်းခက်သွားမယ်။",
         "Risk only 1-2% per trade. One big loss is very hard to recover from."),
        ("Plan ရေးပြီးမှ Trade လုပ်ပါ — Plan မရှိတဲ့ Trade က လောင်းကစားပဲ။",
         "Plan the trade, then trade the plan. A trade without a plan is gambling."),
        ("ရှုံးတဲ့ Trade က သင်ခန်းစာပါ — Plan အတိုင်း လုပ်ပြီး ရှုံးရင် မင်းမှားတာ မဟုတ်ဘူး၊ ဈေးကွက်က အဲဒီလိုပဲ။",
         "A losing trade is a lesson. If you followed your plan and lost, you did nothing wrong — that is the market."),
        ("Revenge Trade ကို လုံးဝ မလုပ်ပါနဲ့ — ရှုံးပြီးပြီးချင်း ပြန်ဝင်ရင် နှစ်ဆ ရှုံးတတ်တယ်။",
         "Never revenge trade. Entering right after a loss usually doubles it."),
        ("FOMO က အဈေးအကြီးဆုံး စိတ်ခံစားမှုပါ — ဈေးတက်နေတာမြင်ပြီး လိုက်ဝင်တာ များသောအားဖြင့် နောက်ကျသွားပြီ။",
         "FOMO is the most expensive emotion. Chasing a pump usually means you are already late."),
        ("Stop-loss က မင်းရဲ့ Seat Belt ပါ — မပါဘဲ ကားမောင်းသလို အန္တရာယ်များတယ်။",
         "Your stop-loss is your seatbelt. Trading without one is like driving without it."),
        ("Target ရောက်ရင် Profit ယူပါ — လောဘကြီးပြီး ထပ်စောင့်တာ များသောအားဖြင့် အမြတ်ပျောက်သွားတတ်တယ်။",
         "Take profit at your target. Waiting for more out of greed often turns a win into a loss."),
        ("တစ်နေ့ Setup ကောင်းကောင်း တစ်ပွဲက Setup မကောင်းတဲ့ ဆယ်ပွဲထက် ပိုကောင်းတယ်။",
         "One good setup a day beats ten forced trades."),
        ("Diary ရေးပါ — မင်းရဲ့ မှတ်တမ်းက မင်းရဲ့ အကောင်းဆုံး ဆရာပဲ။",
         "Keep a journal. Your diary is your best teacher."),
        ("ဈေးကွက်က မနက်ဖြန်လည်း ရှိနေမယ် — မင်းရဲ့ Capital က ရှိနေဖို့ လိုတယ်။",
         "The market will be here tomorrow. Your capital needs to be here too."),
        ("Chart ကို Trade လုပ်ပါ၊ သတင်းအတင်းကို မလုပ်ပါနဲ့ — သတင်းက ဈေးကို လိုက်တာပါ၊ ဈေးက သတင်းကို မလိုက်ဘူး။",
         "Trade the chart, not the hype. Price moves first; the news follows."),
        ("မသေချာရင် မဝင်ပါနဲ့ — မဝင်တာလည်း Position တစ်မျိုးပဲ။",
         "If you are unsure, stay out. No trade is also a position."),
        ("အပတ်တိုင်း တနင်္ဂနွေမှာ Diary ပြန်ဖတ်ပါ — ထပ်တလဲလဲ မှားနေတဲ့ အမှားကို ရှာပြီး ပြင်ပါ။",
         "Review your diary every Sunday. Find the mistake you keep repeating, and fix it."),
        ("စိတ်ငြိမ်မှ Trade လုပ်ပါ — စိတ်ရှုပ်နေချိန်၊ အိပ်ရေးပျက်ချိန်မှာ ဆုံးဖြတ်ချက်တွေ မှားတတ်တယ်။",
         "Trade only with a calm mind. Tired or emotional decisions are usually wrong ones."),
    ]
    tip_idx = datetime.now().timetuple().tm_yday % len(daily_tips)
    tip_mm, tip_en = daily_tips[tip_idx]
    st.subheader(t("📖 ဒီနေ့ရဲ့ ပညာပေး Tip", "📖 Today's Tip"))
    st.success(t(tip_mm, tip_en))

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
# TAB 4: Trading Diary (RR, Volume, chart screenshot — saved to CSV)
# ==========================================
with tabs[3]:
    st.header(t("📓 Trading Diary", "📓 Trading Diary"))

    diary_cols = ["Pair", "Type", "Entry", "Exit", "Return %", "RR Ratio",
                  "Volume", "Result", "Setup", "Notes", "Chart"]

    # Load saved diary once per session
    if "journal_data" not in st.session_state:
        if os.path.exists(DIARY_FILE):
            try:
                df_old = pd.read_csv(DIARY_FILE)
                for c in diary_cols:
                    if c not in df_old.columns:
                        df_old[c] = ""
                st.session_state.journal_data = df_old[diary_cols].to_dict("records")
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
            j_rr = st.number_input(t("RR Ratio (1 : X)", "RR Ratio (1 : X)"), min_value=0.0, value=2.0, step=0.5, format="%.1f")
        with col_c:
            j_volume = st.number_input(t("Volume (USDT)", "Volume (USDT)"), min_value=0.0, format="%.2f")
            j_result = st.selectbox("Result", ["Win 🏆", "Loss 💔", "Break Even 🤝"])
            j_setup = st.selectbox("Setup Type", ["Price Action", "SMC"])

        j_notes = st.text_input("Notes")
        j_chart = st.file_uploader(t("📸 Chart Screenshot ပုံ (Technical Analysis Tab က Save Image နဲ့ သိမ်းထားတဲ့ပုံ)",
                                     "📸 Chart Screenshot (the image saved with Save Image from the Technical Analysis tab)"),
                                   type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button(t("💾 မှတ်တမ်းတင်ရန်", "💾 Save to Diary"))
        if submitted:
            if j_entry > 0 and j_exit > 0:
                ret_pct = (j_exit - j_entry) / j_entry * 100
                if j_type.startswith("Sell"):
                    ret_pct = -ret_pct
            else:
                ret_pct = 0.0
            chart_name = ""
            if j_chart is not None:
                os.makedirs(DIARY_IMG_DIR, exist_ok=True)
                safe_name = "".join(c for c in j_chart.name if c.isalnum() or c in ("-", "_", "."))
                chart_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + safe_name
                with open(os.path.join(DIARY_IMG_DIR, chart_name), "wb") as f:
                    f.write(j_chart.getbuffer())
            st.session_state.journal_data.append({
                "Pair": j_symbol, "Type": j_type, "Entry": j_entry,
                "Exit": j_exit, "Return %": round(ret_pct, 2),
                "RR Ratio": j_rr, "Volume": j_volume,
                "Result": j_result, "Setup": j_setup, "Notes": j_notes,
                "Chart": chart_name
            })
            save_diary()
            st.success(t("မှတ်တမ်းတင်ပြီးပါပြီ — CSV ဖိုင်ထဲလည်း သိမ်းထားပါတယ်။",
                         "Saved! Also stored in the CSV file."))

    if st.session_state.journal_data:
        df_j = pd.DataFrame(st.session_state.journal_data)
        s1, s2, s3, s4 = st.columns(4)
        total = len(df_j)
        wins = (df_j["Result"].astype(str).str.startswith("Win")).sum()
        win_rate = (wins / total * 100) if total else 0.0
        avg_ret = df_j["Return %"].mean() if "Return %" in df_j.columns else 0.0
        avg_rr = df_j["RR Ratio"].mean() if "RR Ratio" in df_j.columns else 0.0
        s1.metric(t("Total Trades", "Total Trades"), total)
        s2.metric(t("Win Rate", "Win Rate"), f"{win_rate:.1f}%")
        s3.metric(t("Avg Return / Trade", "Avg Return / Trade"), f"{avg_ret:.2f}%")
        s4.metric(t("Avg RR Ratio", "Avg RR Ratio"), f"1:{avg_rr:.1f}")
        st.dataframe(df_j, use_container_width=True)
        st.download_button(
            t("⬇️ Diary CSV Download လုပ်ရန်", "⬇️ Download Diary CSV"),
            data=pd.DataFrame(st.session_state.journal_data).to_csv(index=False).encode("utf-8"),
            file_name="trading_diary.csv", mime="text/csv")

        # Show saved chart screenshots (newest first)
        with_images = [r for r in reversed(st.session_state.journal_data)
                       if str(r.get("Chart", "")).strip() != ""
                       and os.path.exists(os.path.join(DIARY_IMG_DIR, str(r["Chart"])))]
        if with_images:
            st.subheader(t("📸 သိမ်းထားတဲ့ Chart ပုံများ", "📸 Saved Chart Screenshots"))
            for r in with_images[:6]:
                st.caption(f"{r.get('Pair', '')} — {r.get('Type', '')} — {r.get('Result', '')} — {r.get('Notes', '')}")
                st.image(os.path.join(DIARY_IMG_DIR, str(r["Chart"])), use_container_width=True)

        if st.checkbox(t("မှတ်တမ်းအားလုံး ဖျက်ရန် (အတည်ပြုရန်)", "Delete all records (confirm)"), key="diary_clear_confirm"):
            if st.button(t("🗑️ အကုန်ဖျက်မယ်", "🗑️ Delete All"), key="diary_clear"):
                st.session_state.journal_data = []
                if os.path.exists(DIARY_FILE):
                    os.remove(DIARY_FILE)
                st.rerun()
    else:
        st.info(t("မှတ်တမ်းမရှိသေးပါ — အပေါ်က Form မှာ Trade တစ်ခု ထည့်ပါ။",
                  "No records yet — add a trade in the form above."))
    st.caption(t("⚠️ Diary နဲ့ ပုံတွေကို App နဲ့အတူ ဖိုင်ထဲ သိမ်းထားပါတယ်။ App ကို ပြန်တင်ရင် (redeploy) ပျောက်နိုင်လို့ အခါအားလျော်စွာ Download လုပ်ပြီး သိမ်းထားပါ။",
                 "⚠️ The diary and images are stored in files next to the app. They can be lost on redeploy, so download a backup copy from time to time."))
