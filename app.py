import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import urllib3

# 경고 제거
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -------------------- 핵심 함수 정의 --------------------

@st.cache_data(show_spinner=False)
def krx_listingcompany_normal(fromDate, toDate):
    # ... (본문 동일)
    # 코드 축약: 실제 함수 내용은 그대로 붙여넣으시면 됩니다
    pass

@st.cache_data(show_spinner=False)
def krx_listingcompany_merge(fromDate, toDate):
    # ... (본문 동일)
    pass

@st.cache_data(show_spinner=False)
def get_krx_market_price_info(trdDd):
    # ... (본문 동일)
    pass

def get_nextrade_filtered_symbols(trade_date):
    # ... (본문 동일)
    pass

# -------------------- Streamlit 페이지 --------------------

st.set_page_config(page_title="📈 신규상장 종목 시가총액 순위분석", layout="wide")
st.title("📈 신규상장 종목 시가총액 순위 분석기")

col1, col2 = st.columns(2)
with col1:
    fromDate = st.date_input("조회 시작일", pd.to_datetime("2025-07-22"))
with col2:
    toDate = st.date_input("조회 종료일", pd.to_datetime("2025-07-25"))

if st.button("🔍 신규상장 종목 불러오기"):
    with st.spinner("신규 상장기업 데이터를 불러오는 중입니다..."):
        listing_company_normal = krx_listingcompany_normal(fromDate.strftime("%Y-%m-%d"), toDate.strftime("%Y-%m-%d"))
        listing_company_merge = krx_listingcompany_merge(fromDate.strftime("%Y-%m-%d"), toDate.strftime("%Y-%m-%d"))

        target_col = ["단축코드", "회사명", "상장일", "상장유형", "증권구분", "국적"]
        listing_company_total = pd.concat([
            listing_company_normal[target_col],
            listing_company_merge[target_col]
        ], ignore_index=True)

        listing_company_total = listing_company_total.sort_values("상장일", ascending=False).reset_index(drop=True)
        listing_company_total["상장일"] = pd.to_datetime(listing_company_total["상장일"]).dt.strftime("%Y%m%d")

        st.success(f"총 {len(listing_company_total)}개 상장 종목 조회됨")
        selected_row = st.selectbox("분석할 신규상장 종목을 선택하세요:", listing_company_total["회사명"].tolist())

        target_row = listing_company_total[listing_company_total["회사명"] == selected_row].iloc[0]
        target_date = target_row["상장일"]
        target_name = target_row["회사명"]

        # Step 1~2: 데이터 수집
        df_filtered = get_nextrade_filtered_symbols(target_date)
        market_cap = get_krx_market_price_info(target_date)

        # Step 3~4: 병합 및 정보 추출
        df_filtered = df_filtered.merge(market_cap, on=["단축코드", "종목명", "시장구분"], how="left")
        try:
            target_info = market_cap[market_cap["종목명"] == target_name].iloc[0]
            target_market = target_info["시장구분"]
            target_ticker = target_info["단축코드"]
            target_marketcap = target_info["시가총액"]
        except:
            st.error("❌ 해당 종목의 시장 또는 시가총액 정보를 찾을 수 없습니다.")
            st.stop()

        # Step 5~6: 시장 필터링 및 순위 계산
        market_df = df_filtered[df_filtered["시장구분"] == target_market].copy()
        market_df = market_df.dropna(subset=["시가총액"]).sort_values("시가총액", ascending=False).reset_index(drop=True)
        rank = (market_df["시가총액"] > target_marketcap).sum() + 1
        total = len(market_df)
        rank_cutoff = total // 2
        percent_rank = (rank-1)/(total-1) if total > 1 else 0
        marketcap_cutoff = market_df.iloc[rank_cutoff - 1]["시가총액"] if rank_cutoff - 1 < total else None
        included = "편입" if rank <= rank_cutoff else "미편입"

        # Step 9~10: 요약 출력
        st.subheader("📌 분석 결과 요약")
        st.markdown(f"**{target_name}** 의 시가총액은 **{target_marketcap:,.0f}원**이며, **{target_market}** 시장 기준 **{rank}/{total}위** 입니다.")
        st.markdown(f"➡️ Percent Rank: **{percent_rank:.2%}** / 편입 기준 순위: **{rank_cutoff}위**")
        st.markdown(f"✔️ 결과: **{'✅ 상위 50% 이내 편입' if included == '편입' else '❌ 편입 기준 미달'}**")

        summary_df = pd.DataFrame([{
            "신규상장_상장일": target_date,
            "신규상장_종목코드": target_ticker,
            "신규상장_종목명": target_name,
            "신규상장_시장구분": target_market,
            "신규상장_시가총액": target_marketcap,
            "편입기준_시가총액": marketcap_cutoff,
            "신규상장_시가총액_rank": rank,
            "편입기준_시가총액_rank": rank_cutoff,
            "신규상장_시가총액_prnk": percent_rank,
            "편입여부": included
        }])
        st.dataframe(summary_df, use_container_width=True)
