import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# --- 網頁設定 ---
st.set_page_config(page_title="美股數據追蹤神器", layout="wide")

# 預設的股票代碼清單
DEFAULT_TICKERS = (
    "ORCL, MU, AVGO, TSM, NFLX, GOOG, META, NVDA, ASML, TSLA, MSFT, AMZN, AAPL, "
    "ON, CDNS, GFS, GEV, QCOM, KLAC, LRCX, SMC, AMAT, INTC, AMD, ARM, GE, VRT, "
    "IBM, SAP, ADBE, NOW, CRM, FTNT, PANW, CRWD, APP, VRSK, MRVL, VRSN, DUOL, "
    "ZM, CSCO, SNPS"
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
        symbol = symbol.strip().upper()
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
            trailing_pe = info.get('trailingPE', None) # 過去四季本益比
            forward_pe = info.get('forwardPE', None)   # 預估本益比

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

# --- 網頁介面 (UI) ---

st.title("📈 美股數據追蹤表")
st.markdown("資料來源：Yahoo Finance (延遲報價)")

with st.sidebar:
    st.header("⚙️ 設定")
    st.write("在此輸入股票代號 (用逗號分隔)：")
    user_tickers = st.text_area("股票代號清單", value=DEFAULT_TICKERS, height=300)
    if st.button("🔄 手動更新資料"):
        st.cache_data.clear()
        st.rerun()

ticker_list = [t.strip() for t in user_tickers.split(',') if t.strip()]

if ticker_list:
    df = get_stock_data(ticker_list)

    if not df.empty and "代號" in df.columns:
        df = df.sort_values(by="代號").reset_index(drop=True)

    # 顯示更新時間 (美東)
    ny_timezone = pytz.timezone('America/New_York')
    ny_time = datetime.now(ny_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
    st.info(f"最後更新時間 (美東): {ny_time}")

    # 顯示表格與欄位設定
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

    # 下載 CSV 按鈕
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載 Excel (CSV)",
        data=csv,
        file_name=f'us_stocks_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )
else:

    st.warning("⚠️ 請至少輸入一個有效的股票代號。")
