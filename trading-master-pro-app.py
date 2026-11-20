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

# --- Live clock (Myanmar time, updates every second, no app rerun) ---
_is_mm = (language == "Myanmar (မြန်မာ)")
_clock_locale = "my-MM" if _is_mm else "en-GB"
_clock_numbering = "mymr" if _is_mm else "latn"
_clock_label = "🕐 မြန်မာစံတော်ချိန်" if _is_mm else "🕐 Myanmar Time (Yangon)"
_clock_html = f"""
<div id="live-clock" style="font-size:20px; padding:2px 0 8px 0;">—</div>
<script>
function tickClock() {{
  var now = new Date();
  var timeFmt = new Intl.DateTimeFormat("{_clock_locale}", {{timeZone: "Asia/Yangon", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, numberingSystem: "{_clock_numbering}"}});
  var dateFmt = new Intl.DateTimeFormat("{_clock_locale}", {{timeZone: "Asia/Yangon", weekday: "long", year: "numeric", month: "long", day: "numeric", numberingSystem: "{_clock_numbering}"}});
  document.getElementById("live-clock").innerHTML = "<b>{_clock_label}:</b> " + timeFmt.format(now) + " &nbsp;•&nbsp; " + dateFmt.format(now);
}}
tickClock();
setInterval(tickClock, 1000);
</script>
"""
components.html(_clock_html, height=45)

st.markdown("---")

tabs = st.tabs([
    t("📊 1. Technical Analysis", "📊 1. Technical Analysis"),
    t("🌍 2. Fundamental Analysis", "🌍 2. Fundamental Analysis"),
    t("🧠 3. Trading Psychology", "🧠 3. Trading Psychology"),
    t("📓 4. Trading Diary", "📓 4. Trading Diary"),
    t("🧮 5. Lot Size Calculator", "🧮 5. Lot Size Calculator")
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
# TAB 1: Technical Analysis — Price Action Toolkit (no embedded chart;
# Wai does charting directly in TradingView)
# ==========================================
PA_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT",
            "COMPUSDT", "SNDKUSDT", "SPCXUSDT", "NVDAUSDT", "XAUUSDT", "BNBUSDT"]
TV_MAP = {"NVDAUSDT": "NASDAQ:NVDA", "SNDKUSDT": "NASDAQ:SNDK"}

@st.cache_data(ttl=300)
def fetch_klines(symbol, interval, limit=250):
    """Binance Futures klines -> list of (o, h, l, c, close_ms) or None."""
    for base in ("https://data-api.binance.vision", "https://www.binance.com"):
        try:
            r = requests.get(f"{base}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=10)
            data = r.json()
            if isinstance(data, list) and len(data) > 5:
                return [(float(k[1]), float(k[2]), float(k[3]), float(k[4]), int(k[6])) for k in data]
        except Exception:
            continue
    return None

def closed_candles(klines):
    now_ms = int(datetime.now(ZoneInfo("UTC")).timestamp() * 1000)
    return [k for k in klines if k[4] <= now_ms]

def sma(values, n):
    if len(values) < n:
        return None
    return sum(values[-n:]) / n

def detect_patterns(closed):
    """Last closed candle: pattern names among Hammer, Shooting Star,
    Bullish Engulfing, Bearish Engulfing (same rules as the hourly watch)."""
    if len(closed) < 2:
        return []
    o, h, l, c, _ = closed[-1]
    po, ph, pl, pc, _ = closed[-2]
    body = abs(c - o)
    lower = min(o, c) - l
    upper = h - max(o, c)
    rng = h - l
    out = []
    is_doji = rng > 0 and body <= 0.05 * rng
    if (lower >= 2 * body and upper <= body) or (is_doji and lower >= 0.6 * rng and upper <= 0.15 * rng):
        out.append("Hammer")
    if (upper >= 2 * body and lower <= body) or (is_doji and upper >= 0.6 * rng and lower <= 0.15 * rng):
        out.append("Shooting Star")
    if pc < po and c > o and o <= pc and c >= po:
        out.append("Bullish Engulfing")
    if pc > po and c < o and o >= pc and c <= po:
        out.append("Bearish Engulfing")
    return out

def find_sr_levels(closed, window=5, tol=0.005):
    """Pivot highs/lows clustered within tol -> (resistance levels, support levels)."""
    highs, lows = [], []
    for i in range(window, len(closed) - window):
        h, l = closed[i][1], closed[i][2]
        if h == max(k[1] for k in closed[i - window:i + window + 1]):
            highs.append(h)
        if l == min(k[2] for k in closed[i - window:i + window + 1]):
            lows.append(l)
    def cluster(levels):
        groups = []
        for lv in sorted(levels):
            if groups and abs(lv - groups[-1][-1]) / groups[-1][-1] <= tol:
                groups[-1].append(lv)
            else:
                groups.append([lv])
        return [sum(g) / len(g) for g in groups]
    return cluster(highs), cluster(lows)

def fmt_p(p):
    p = float(p)
    if p >= 10000:
        return f"${p:,.0f}"
    if p >= 100:
        return f"${p:,.2f}"
    if p >= 1:
        return f"${p:,.2f}"
    return f"${p:,.4f}"

with tabs[0]:
    st.header(t("📊 Technical Analysis — Price Action Toolkit", "📊 Technical Analysis — Price Action Toolkit"))
    st.write(t("Chart ကို TradingView မှာ တိုက်ရိုက်ကြည့်ပါ — ဒီ Tab က Support/Resistance, MA200, Candle Pattern နဲ့ H1 Entry တို့ကို တွက်ချက်ပေးပါတယ်။",
               "Do charting directly in TradingView — this tab calculates Support/Resistance, MA200, candle patterns and H1 entries for you."))
    pa_pair = st.selectbox(t("Pair ရွေးပါ", "Select Pair"), PA_PAIRS, key="pa_pair")
    tv_sym = TV_MAP.get(pa_pair, f"BINANCE:{pa_pair}")
    st.link_button(t(f"📈 {pa_pair} ကို TradingView မှာ ဖွင့်ရန်", f"📈 Open {pa_pair} in TradingView"),
                   f"https://www.tradingview.com/chart/?symbol={tv_sym}")

    k1d = fetch_klines(pa_pair, "1d", 250)
    k4h = fetch_klines(pa_pair, "4h", 250)
    k1h = fetch_klines(pa_pair, "1h", 30)
    if not k1d or not k4h:
        st.warning(t("Binance က Data ဆွဲမရပါ — အင်တာနက် စစ်ပြီး Refresh လုပ်ပါ။",
                     "Could not fetch Binance data — check your connection and refresh."))
    else:
        c1d, c4h = closed_candles(k1d), closed_candles(k4h)
        price = c1d[-1][3]
        ma200_d1 = sma([k[3] for k in c1d], 200)
        ma200_h4 = sma([k[3] for k in c4h], 200)
        votes = []
        if ma200_d1 is not None:
            votes.append(1 if price > ma200_d1 else -1)
        if ma200_h4 is not None:
            votes.append(1 if price > ma200_h4 else -1)
        pat4h = detect_patterns(c4h)
        pat1d = detect_patterns(c1d)
        for p in pat4h + pat1d:
            votes.append(1 if p in ("Hammer", "Bullish Engulfing") else -1)
        s = sum(votes)
        bias = t("📈 Bullish", "📈 Bullish") if s > 0 else (t("📉 Bearish", "📉 Bearish") if s < 0 else t("➖ Neutral / Mixed", "➖ Neutral / Mixed"))
        st.subheader(t(f"{pa_pair} — လက်ရှိအခြေအနေ", f"{pa_pair} — Current Picture"))
        b1, b2, b3, b4 = st.columns(4)
        b1.metric(t("လက်ရှိဈေး", "Price"), fmt_p(price))
        if ma200_d1 is not None:
            b2.metric("MA200 (D1)", fmt_p(ma200_d1), f"{(price / ma200_d1 - 1) * 100:+.1f}%")
        else:
            b2.metric("MA200 (D1)", "—")
        if ma200_h4 is not None:
            b3.metric("MA200 (H4)", fmt_p(ma200_h4), f"{(price / ma200_h4 - 1) * 100:+.1f}%")
        else:
            b3.metric("MA200 (H4)", "—")
        b4.metric(t("Price Action Bias", "Price Action Bias"), bias)
        st.caption(t("Bias က MA200 (D1+H4) အပေါ်/အောက် + H4/D1 Pattern တွေကို ပေါင်းပြီး တွက်ထားတာပါ — Trade ဝင်ဖို့ အမိန့်မဟုတ်ပါ၊ ကိုယ့် Analysis နဲ့ အတည်ပြုပါ။",
                     "Bias combines price vs MA200 (D1+H4) and H4/D1 patterns — it is not a trade call; confirm with your own analysis."))
        st.subheader(t("🧱 Support & Resistance", "🧱 Support & Resistance"))
        for label, closed in ((t("Daily (D1)", "Daily (D1)"), c1d), (t("4H", "4H"), c4h)):
            highs, lows = find_sr_levels(closed)
            res = sorted([x for x in highs if x > price])[:3]
            sup = sorted([x for x in lows if x < price], reverse=True)[:3]
            st.write(f"**{label}**")
            rc1, rc2 = st.columns(2)
            with rc1:
                st.write(t("🔴 Resistance (အပေါ်)", "🔴 Resistance (above)"))
                if res:
                    for r in res:
                        st.write(f"• {fmt_p(r)}  ({(r / price - 1) * 100:+.1f}%)")
                else:
                    st.write("—")
            with rc2:
                st.write(t("🟢 Support (အောက်)", "🟢 Support (below)"))
                if sup:
                    for sp in sup:
                        st.write(f"• {fmt_p(sp)}  ({(sp / price - 1) * 100:+.1f}%)")
                else:
                    st.write("—")
        st.subheader(t("🎯 H1 Entry Check", "🎯 H1 Entry Check"))
        st.write(t("H4/D1 က Direction သတ်မှတ်ပြီး H1 မှာ Entry Timing ရှာပါ — H1 Pattern က H4/D1 Bias နဲ့ တူတဲ့ ဘက်ဖြစ်ရမယ်။",
                   "H4/D1 set the direction; H1 times the entry — the H1 pattern must agree with the H4/D1 bias."))
        if k1h:
            c1h = closed_candles(k1h)
            h1_trend = t("Up", "Up") if c1h[-1][3] > c1h[-6][3] else t("Down", "Down")
            h1_pat = detect_patterns(c1h)
            st.write(t(f"H1 Trend (နောက် 5 Candle): **{h1_trend}** • နောက်ဆုံး H1 Pattern: **{', '.join(h1_pat) if h1_pat else '—'}**",
                       f"H1 Trend (last 5 candles): **{h1_trend}** • Last H1 pattern: **{', '.join(h1_pat) if h1_pat else '—'}**"))
            rows = []
            for k in c1h[-5:]:
                rows.append({"Time (Yangon)": datetime.fromtimestamp(k[4] / 1000, ZoneInfo("Asia/Yangon")).strftime("%m-%d %H:%M"),
                             "Open": fmt_p(k[0]), "High": fmt_p(k[1]), "Low": fmt_p(k[2]), "Close": fmt_p(k[3])})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader(t("🕯️ Candle Pattern Scanner — H4 & D1 (Pair ၁၁ ခု)", "🕯️ Candle Pattern Scanner — H4 & D1 (11 pairs)"))
    st.write(t("နောက်ဆုံး ပိတ်ပြီးသား H4/D1 Candle မှာ Hammer, Shooting Star, Bullish/Bearish Engulfing ပေါ်တဲ့ Pair တွေ — နာရီတိုင်း Alert ပို့တဲ့ Watch နဲ့ အတူတူပဲ။",
               "Last closed H4/D1 candles showing Hammer, Shooting Star, Bullish/Bearish Engulfing — same rules as the hourly alert watch."))
    scan_rows = []
    for sym in PA_PAIRS:
        k4 = fetch_klines(sym, "4h", 8)
        k1 = fetch_klines(sym, "1d", 8)
        row = {"Pair": sym, "H4": "—", "D1": "—", "SL ref": "—"}
        if k4:
            cc = closed_candles(k4)
            pp = detect_patterns(cc)
            if pp:
                row["H4"] = ", ".join(pp)
                row["SL ref"] = fmt_p(cc[-1][2]) if pp[0] in ("Hammer", "Bullish Engulfing") else fmt_p(cc[-1][1])
        if k1:
            cc = closed_candles(k1)
            pp = detect_patterns(cc)
            if pp:
                row["D1"] = ", ".join(pp)
                if row["SL ref"] == "—":
                    row["SL ref"] = fmt_p(cc[-1][2]) if pp[0] in ("Hammer", "Bullish Engulfing") else fmt_p(cc[-1][1])
        scan_rows.append(row)
    st.dataframe(pd.DataFrame(scan_rows), use_container_width=True, hide_index=True)

    st.subheader(t("📏 Price Action Rules", "📏 Price Action Rules"))
    st.markdown(t("""
- **Trend နဲ့အတူ Trade လုပ်ပါ** — ဈေးက MA200 (D1+H4) အပေါ်မှာဆို Long Bias ပဲ၊ အောက်မှာဆို Short Bias ပဲ။
- **D1 → H4 → H1** — D1 က Direction၊ H4 က Setup၊ H1 က Entry Timing။
- **S/R နားမှာပဲ ဝင်ပါ** — Support နားမှာ Long၊ Resistance နားမှာ Short။ Range အလယ်မှာ မဝင်ပါနဲ့။
- **Candle ပိတ်ပြီးမှ ဝင်ပါ** — ပုံစံပေါ်နေတုန်း (မပိတ်သေးတဲ့ Candle) မှာ မဝင်ပါနဲ့။
- **Pattern + S/R ပေါင်းမှ အားကောင်းတယ်** — Pattern တစ်ခုတည်းက အားနည်းတယ်။
- **SL က Pattern Candle ရဲ့ Low/High အောက်/အပေါ်မှာ ထားပါ**၊ Risk 1–2% ပဲ ယူပါ (Tab 5 Calculator သုံးပါ)။
- **ရှေ့မှာ S/R ကြီး ပိတ်နေရင် မဝင်ပါနဲ့** — Target မရောက်ခင် Resistance/Support နဲ့ တိုးနိုင်တယ်။
- **H4 နဲ့ D1 Bias ကွဲနေရင် စောင့်ပါ** — နှစ်ခုလုံး တူတဲ့ ဘက်မှ ဝင်ပါ။
""",
"""
- **Trade with the trend** — price above MA200 (D1+H4) means long bias only; below means short bias only.
- **D1 → H4 → H1** — D1 sets direction, H4 sets the setup, H1 times the entry.
- **Enter only near S/R** — longs near support, shorts near resistance; never mid-range.
- **Wait for the candle to CLOSE** — never enter on a forming pattern.
- **Pattern + S/R confluence is strong** — a pattern alone is weak.
- **Place SL below/above the pattern candle's low/high**, risk only 1–2% per trade (use the Tab 5 calculator).
- **Do not enter when a major S/R sits just ahead** — it can block the target.
- **If H4 and D1 bias disagree, wait** — enter only when both agree.
"""))

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

# ==========================================
# TAB 5: Lot Size Calculator (risk-based position sizing)
# ==========================================
with tabs[4]:
    st.header(t("🧮 Lot Size Calculator", "🧮 Lot Size Calculator"))
    st.write(t("Account Balance နဲ့ Risk % ပေါ်မူတည်ပြီး ဘယ်လောက် Lot (Quantity) ဝင်ရမလဲ တွက်ပေးပါတယ် — SL ထိရင် ဆုံးရှုံးမယ့်ငွေက Risk Amount အတိအကျပဲ ဖြစ်မယ်။",
               "Calculates how much to buy/sell (quantity) from your account balance and risk % — if the stop-loss is hit, you lose exactly the risk amount."))

    ls_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT",
                  "COMPUSDT", "SNDKUSDT", "SPCXUSDT", "NVDAUSDT", "XAUUSDT", "BNBUSDT"]

    in_col, out_col = st.columns([1, 1])
    with in_col:
        st.subheader(t("📝 ထည့်သွင်းရန်", "📝 Inputs"))
        ls_pair = st.selectbox(t("Pair", "Pair"), ls_symbols, key="ls_pair")
        if st.button(t("📥 Live Price ယူမယ်", "📥 Get Live Price"), key="ls_live_btn"):
            lp, _lp_chg = fetch_binance_ticker(ls_pair)
            if lp is not None:
                st.session_state["ls_entry_input"] = float(lp)
                st.success(t(f"Live Price: ${lp:,.2f} — Entry မှာ ထည့်ပြီးပြီ။",
                             f"Live price: ${lp:,.2f} — filled into Entry."))
                st.rerun()
            else:
                st.warning(t("Live Price ဆွဲမရပါ — Entry ကို ကိုယ်တိုင် ရိုက်ပါ။",
                             "Could not fetch live price — enter the price manually."))
        ls_balance = st.number_input(t("Account Balance (USDT)", "Account Balance (USDT)"),
                                     min_value=0.0, value=100.0, step=10.0, format="%.2f", key="ls_balance")
        ls_risk = st.number_input(t("Risk per Trade (%)", "Risk per Trade (%)"),
                                  min_value=0.1, max_value=10.0, value=1.0, step=0.5, format="%.1f", key="ls_risk")
        ls_dir = st.radio(t("Direction", "Direction"), ["Long (Buy)", "Short (Sell)"],
                          horizontal=True, key="ls_dir")
        ls_entry = st.number_input(t("Entry Price ($)", "Entry Price ($)"),
                                   min_value=0.0, value=0.0, format="%.4f", key="ls_entry_input")
        ls_sl = st.number_input(t("Stop Loss Price ($)", "Stop Loss Price ($)"),
                                min_value=0.0, value=0.0, format="%.4f", key="ls_sl_input")
        ls_tp = st.number_input(t("Take Profit Price ($) — မရှိရင် 0 ထားပါ", "Take Profit Price ($) — 0 if none"),
                                min_value=0.0, value=0.0, format="%.4f", key="ls_tp_input")
        ls_lev = st.number_input(t("Leverage (x)", "Leverage (x)"),
                                 min_value=1, max_value=125, value=10, step=1, key="ls_lev")

    with out_col:
        st.subheader(t("📊 ရလဒ်", "📊 Results"))
        is_long = ls_dir.startswith("Long")
        err = None
        if ls_entry <= 0 or ls_sl <= 0:
            st.info(t("Entry နဲ့ Stop Loss ဈေးတွေ ထည့်ပါ — ရလဒ် ချက်ချင်း တွက်ပြပါမယ်။",
                      "Enter Entry and Stop Loss prices — results calculate instantly."))
        elif ls_entry == ls_sl:
            err = t("Entry နဲ့ Stop Loss တူလို့ မရပါ။",
                    "Entry and Stop Loss cannot be the same.")
        elif is_long and ls_sl > ls_entry:
            err = t("Long အတွက် Stop Loss က Entry အောက်မှာ ရှိရမယ်။",
                    "For a Long, the Stop Loss must be below Entry.")
        elif (not is_long) and ls_sl < ls_entry:
            err = t("Short အတွက် Stop Loss က Entry အပေါ်မှာ ရှိရမယ်။",
                    "For a Short, the Stop Loss must be above Entry.")
        if err:
            st.error(err)
        elif ls_entry > 0 and ls_sl > 0:
            risk_amt = ls_balance * ls_risk / 100.0
            risk_per_unit = abs(ls_entry - ls_sl)
            qty = risk_amt / risk_per_unit
            pos_value = qty * ls_entry
            margin = pos_value / ls_lev
            margin_pct = (margin / ls_balance * 100.0) if ls_balance > 0 else 0.0
            if qty >= 1000:
                qty_str = f"{qty:,.2f}"
            elif qty >= 1:
                qty_str = f"{qty:,.4f}"
            else:
                qty_str = f"{qty:,.6f}"
            m1, m2 = st.columns(2)
            m1.metric(t("Risk Amount (ဆုံးရှုံးနိုင်ငွေ)", "Risk Amount"), f"${risk_amt:,.2f}")
            m2.metric(t("Risk per Unit", "Risk per Unit"), f"${risk_per_unit:,.4f}")
            m1.metric(t("Position Size (Lot / Quantity)", "Position Size (Lot / Quantity)"), qty_str)
            m2.metric(t("Position Value", "Position Value"), f"${pos_value:,.2f}")
            m1.metric(t("Required Margin", "Required Margin"), f"${margin:,.2f}")
            m2.metric(t("Margin / Balance", "Margin / Balance"), f"{margin_pct:.1f}%")
            if ls_tp > 0:
                rr = abs(ls_tp - ls_entry) / risk_per_unit
                st.metric(t("Risk : Reward", "Risk : Reward"), f"1 : {rr:.2f}")
                st.write(t(f"TP ထိရင် အမြတ် ≈ ${risk_amt * rr:,.2f} • SL ထိရင် အရှုံး = ${risk_amt:,.2f}",
                           f"If TP hits, profit ≈ ${risk_amt * rr:,.2f} • If SL hits, loss = ${risk_amt:,.2f}"))
            st.markdown("---")
            st.write(t(f"🧮 ဖော်မြူလာ: Quantity = (Balance ${ls_balance:,.0f} × {ls_risk:.1f}%) ÷ |Entry − SL| = ${risk_amt:,.2f} ÷ ${risk_per_unit:,.4f}",
                       f"🧮 Formula: Quantity = (Balance ${ls_balance:,.0f} × {ls_risk:.1f}%) ÷ |Entry − SL| = ${risk_amt:,.2f} ÷ ${risk_per_unit:,.4f}"))
            if margin > ls_balance:
                st.warning(t(f"⚠️ Margin ${margin:,.2f} က Balance ${ls_balance:,.2f} ထက် များနေတယ် — Leverage မြှင့်တာ (သို့) Risk % လျှော့တာ လုပ်ပါ။",
                             f"⚠️ Margin ${margin:,.2f} exceeds your balance ${ls_balance:,.2f} — raise leverage or lower risk %."))
            elif margin_pct > 50:
                st.warning(t("⚠️ Margin က Balance ရဲ့ 50% ကျော်နေတယ် — Position ကြီးနေတယ်၊ သတိထားပါ။",
                             "⚠️ Margin is over 50% of your balance — the position is large, be careful."))
            st.caption(t("💡 Quantity ကို Exchange ရဲ့ Step Size အတိုင်း အောက်ကို ချပြီး ရိုက်ပါ (ဥပမာ 0.0123 → 0.012)။ Fee (ကော်မရှင်) မပါဝင်သေးပါ။",
                         "💡 Round the quantity DOWN to the exchange's step size (e.g. 0.0123 → 0.012). Trading fees are not included."))
