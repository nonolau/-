import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# --- 網頁設定 ---
st.set_page_config(page_title="美股數據追蹤神器", layout="wide")

# ==========================================
# 👇 1. [程式讀取用] 已幫您填入發布的 CSV 連結 👇
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRZNUW6Gj0wIYcSXNyYNXbdU9XolqG3tFs8RPMJmq8_9yxvf7vbQ3Wd_JE-C-BYpsBZULZtdT9QtRg9/pub?gid=0&single=true&output=csv"

# 👇 2. [舅舅編輯用] 已填入您的共用連結 (讓舅舅可以編輯) 👇
GOOGLE_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1w7BGj0xHQWVFvR8PogFj6NmsMmJ6CCzOY4AeAZFURoY/edit?usp=sharing"
# ==========================================

# 預設的股票代碼清單 (如果沒有設定 Google Sheet，就會用這個)
# 注意：變數名稱必須是 DEFAULT_TICKERS_STR，請勿更改名稱
DEFAULT_TICKERS_STR = (
    "ORCL, MU, AVGO, TSM, NFLX, GOOG, META, NVDA, ASML, TSLA, MSFT, AMZN, AAPL, "
    "ON, CDNS, GFS, GEV, QCOM, KLAC, LRCX, SMCI, AMAT, INTC, AMD, ARM, GE, VRT, "
    "IBM, SAP, ADBE, NOW, CRM, FTNT, PANW, CRWD, APP, VRSK, MRVL, VRSN, DUOL, "
    "ZM, CSCO, SNPS, ANET, DELL, MNST, U, CRCL, CCJ, OXY, SNOW, HOOD, PLTR, "
    "RBLX, VST, SOFI, TEM, EBAY, SE, SHOP, PDD, PCAR, CAT, WMT, LULU, MS, BAC, "
    "CVX, ABBV, NEE, EXPE, BKNG, GEHC, MELI, ANF, GS, AXP, LLY, NVO, REGN, ISRG, "
    "ABNB, KO, UBER, UPST, PYPL, CRWV, MRK, UNH, SBUX, V, SNAP, IBM, AFRM, DECK"
)

# --- 核心功能：抓取資料 ---
@st.cache_data(ttl=300)
def get_stock_data(ticker_list):
    data = []
    
    # 建立進度條
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_tickers = len(ticker_list)

    for i, symbol in enumerate(ticker_list):
        symbol = str(symbol).strip().upper()
        if not symbol:
            continue
            
        try:
            progress_bar.progress((i + 1) / total_tickers)
            status_text.text(f"正在抓取: {symbol} ...")
            
            ticker = yf.Ticker(symbol)
            
            # 抓取過去 1 年歷史股價
            hist = ticker.history(period="1y")
            
            if hist.empty:
                data.append({"代號": symbol, "錯誤": "查無歷史股價"})
                continue

            low_365 = hist['Low'].min()
            high_365 = hist['High'].max()
            current_price = hist['Close'].iloc[-1]
            
            # 抓取基本面資料
            info = ticker.info
            trailing_pe = info.get('trailingPE', None)
            forward_pe = info.get('forwardPE', None)

            data.append({
                "代號": symbol,
                "最低 (365天)": round(low_365, 2),
                "最高 (365天)": round(high_365, 2),
                "現價": round(current_price, 2),
                "本益比 (Trailing P/E)": round(trailing_pe, 2) if trailing_pe else "N/A",
                "預估本益比 (Forward P/E)": round(forward_pe, 2) if forward_pe else "N/A",
                "錯誤": ""
            })
            
        except Exception as e:
            data.append({"代號": symbol, "錯誤": "抓取失敗"})
            print(f"Error fetching {symbol}: {e}")

    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(data)

# --- 輔助功能：從 Google Sheet 讀取清單 ---
def load_tickers_from_sheet(url):
    try:
        # 讀取 CSV，假設第一欄是股票代號，且沒有標題 (header=None)
        df_sheet = pd.read_csv(url, header=None)
        tickers = df_sheet[0].dropna().astype(str).tolist()
        clean_tickers = [t for t in tickers if len(t) < 10 and t.upper() != "TICKER"]
        return clean_tickers
    except Exception as e:
        st.error(f"無法讀取 Google Sheet，請檢查連結設定。\n錯誤訊息: {e}")
        return []

# --- 網頁介面 (UI) ---

st.title("📈 美股數據追蹤表")

# --- 決定資料來源 ---
final_ticker_list = []
source_msg = ""

if GOOGLE_SHEET_URL:
    # 優先使用 Google Sheet
    st.markdown(f"資料來源：**Google 試算表連動** (延遲報價)")
    sheet_tickers = load_tickers_from_sheet(GOOGLE_SHEET_URL)
    if sheet_tickers:
        final_ticker_list = sheet_tickers
        source_msg = "✅ 已從 Google Sheet 載入最新清單"
    else:
        st.warning("Google Sheet 讀取失敗，切換回預設清單。")
        final_ticker_list = [t.strip() for t in DEFAULT_TICKERS_STR.split(',') if t.strip()]
else:
    # 沒有設定 URL，使用手動輸入模式
    st.markdown("資料來源：**手動設定模式** (延遲報價)")
    query_params = st.query_params
    url_tickers = query_params.get("tickers", None)
    initial_value = url_tickers if url_tickers else DEFAULT_TICKERS_STR

    with st.sidebar:
        st.header("⚙️ 設定")
        user_tickers = st.text_area("股票代號清單", value=initial_value, height=300)
        
        if user_tickers != initial_value:
            st.query_params["tickers"] = user_tickers
            
        if st.button("🔄 手動更新資料"):
            st.cache_data.clear()
            st.rerun()
            
    final_ticker_list = [t.strip() for t in user_tickers.split(',') if t.strip()]

# --- 顯示主要內容 ---
if GOOGLE_SHEET_URL:
    with st.sidebar:
        st.header("⚙️ 設定")
        st.info("目前的股票清單是由 Google 試算表控制。")
        
        # [新增] 編輯按鈕
        if GOOGLE_SHEET_EDIT_URL:
            st.link_button("📝 點此去修改股票清單", GOOGLE_SHEET_EDIT_URL)
            st.caption("修改後請等約 5 分鐘，再按重新整理。")
        
        if st.button("🔄 重新載入資料 (Refresh)"):
            st.cache_data.clear()
            st.rerun()

if source_msg:
    st.info(source_msg)

# 如果是手動模式，重新載入按鈕已經在上方
if GOOGLE_SHEET_URL and not source_msg: 
     pass # 避免重複顯示

if final_ticker_list:
    df = get_stock_data(final_ticker_list)

    if not df.empty and "代號" in df.columns:
        df = df.sort_values(by="代號").reset_index(drop=True)

    # 顯示更新時間
    ny_timezone = pytz.timezone('America/New_York')
    ny_time = datetime.now(ny_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
    st.caption(f"最後更新時間 (美東): {ny_time}")

    # 顯示表格
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "代號": st.column_config.TextColumn("股票代號"),
            "最低 (365天)": st.column_config.NumberColumn(format="$%.2f"),
            "最高 (365天)": st.column_config.NumberColumn(format="$%.2f"),
            "現價": st.column_config.NumberColumn(format="$%.2f"),
            "本益比 (Trailing P/E)": st.column_config.TextColumn("本益比 (Trailing)"),
            "預估本益比 (Forward P/E)": st.column_config.TextColumn("預估 (Forward)"),
            "錯誤": st.column_config.TextColumn("備註")
        }
    )

    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載 Excel (CSV)",
        data=csv,
        file_name=f'us_stocks_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )
else:
    st.warning("⚠️ 目前清單是空的，請檢查 Google Sheet 或輸入代號。")
