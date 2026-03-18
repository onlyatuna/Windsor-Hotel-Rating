import os
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_PATH = "reviews.csv"

st.set_page_config(page_title="裕元花園酒店 Google 評論", page_icon="🏨", layout="wide")
st.title("🏨 裕元花園酒店 — Google 評論分析")

# ── 載入資料 ──────────────────────────────────────────────
@st.cache_data
def load_data(path):
    return pd.read_csv(path, encoding="utf-8-sig")

if not os.path.exists(CSV_PATH):
    st.info("尚無資料，GitHub Actions 每天上午 10 點（台灣時間）會自動更新。")
    st.stop()

df = load_data(CSV_PATH)
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

# 顯示最後更新時間
mtime = os.path.getmtime(CSV_PATH)
st.caption(f"資料最後更新：{datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')}")

# ── 側邊欄篩選 ────────────────────────────────────────────
st.sidebar.header("篩選條件")
rating_filter = st.sidebar.multiselect(
    "星級",
    options=[5, 4, 3, 2, 1],
    default=[5, 4, 3, 2, 1],
)
keyword = st.sidebar.text_input("關鍵字搜尋（評論內容）")

filtered = df[df["rating"].isin(rating_filter)]
if keyword:
    filtered = filtered[
        filtered["review"].fillna("").str.contains(keyword, case=False)
    ]

# ── 統計摘要 ──────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("總評論數", len(df))
col2.metric("平均評分", f"{df['rating'].mean():.2f} ⭐" if not df["rating"].isna().all() else "N/A")
col3.metric("篩選結果", len(filtered))

# ── 評分分佈 ──────────────────────────────────────────────
st.subheader("評分分佈")
rating_counts = df["rating"].value_counts().sort_index(ascending=False)
st.bar_chart(rating_counts)

# ── 評論列表 ──────────────────────────────────────────────
st.subheader("評論列表")
for _, row in filtered.iterrows():
    stars = "⭐" * int(row["rating"]) if pd.notna(row["rating"]) else ""
    with st.expander(f'{row["reviewer"] or "匿名"}  {stars}  {row["date"] or ""}'):
        st.write(row["review"] or "（無內容）")
