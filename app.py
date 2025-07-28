import streamlit as st
import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ✅ 정상 상장 종목
def krx_listingcompany_normal(fromDate, toDate):
    url = "https://kind.krx.co.kr/listinvstg/listingcompany.do"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://kind.krx.co.kr/listinvstg/listingcompany.do?method=searchListingTypeMain",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://kind.krx.co.kr",
    }
    data = {
        "method": "searchListingTypeSub",
        "currentPageSize": "100",
        "pageIndex": "1",
        "orderMode": "1",
        "orderStat": "D",
        "repIsuSrtCd": "",
        "isurCd": "",
        "forward": "listingtype_sub",
        "listTypeArrStr": "01|02|03|04|05|",
        "secuGrpArrStr": "0|ST|FS|MF|SC|RT|DR|",
        "secuGrpArr": ["0", "ST|FS", "MF|SC|RT", "DR"],
        "listTypeArr": ["01", "02", "03", "04", "05"],
        "fromDate": fromDate,
        "toDate": toDate,
    }
    try:
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="list type-00 tmt30")
        columns = ["단축코드", "회사명", "상장일", "상장유형", "증권구분", "업종", "국적", "상장주선인/지정자문인"]
        data_rows = []
        if table and table.tbody:
            for row in table.tbody.find_all("tr"):
                cells = row.find_all("td")
                onclick = row.get("onclick", "")
                match = re.search(r"fnDetailView\('(\d+)'", onclick)
                short_code = match.group(1) if match else ""
                row_data = [short_code]
                for i, cell in enumerate(cells[:len(columns) - 1]):
                    if i == 0:
                        row_data.append(cell.get("title", "").strip())
                    else:
                        row_data.append(cell.get_text(strip=True))
                data_rows.append(row_data)
        return pd.DataFrame(data_rows, columns=columns)
    except Exception as e:
        st.error(f"❌ 상장 종목 조회 실패: {e}")
        return pd.DataFrame(columns=columns)

# ✅ 넥스트레이드 거래가능 종목
def get_nextrade_filtered_symbols(trade_date):
    url = "https://www.nextrade.co.kr/brdinfoTime/brdinfoTimeList.do"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nextrade.co.kr/menu/transactionStatusMain/menuList.do",
        "Origin": "https://www.nextrade.co.kr",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "_search": "false",
        "nd": str(int(pd.Timestamp.now().timestamp() * 1000)),
        "pageUnit": "900",
        "pageIndex": "1",
        "sidx": "",
        "sord": "asc",
        "scAggDd": trade_date,
        "scMktId": "",
        "searchKeyword": ""
    }
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
        response.encoding = 'utf-8'
        result = response.json()
        keep_keys = ["aggDd", "mktNm", "isuCd", "isuSrdCd", "isuAbwdNm", "cptrTrdPmsnCdNm", "trdIpsbRsn"]
        raw_data = result.get('brdinfoTimeList', [])
        filtered_data = [{k: item.get(k, None) for k in keep_keys} for item in raw_data]
        df = pd.DataFrame(filtered_data)
        df.columns = ["집계일", "시장구분", "종목코드", "단축코드", "종목명", "거래가능시장", "거래불가사유"]
        df["단축코드"] = df["단축코드"].str[1:]
        return df[(df["거래가능시장"] != "거래불가") | (df["거래불가사유"] == "거래정지")]
    except Exception as e:
        st.error(f"❌ Nextrade 데이터 오류: {e}")
        return pd.DataFrame()

# ✅ KRX 시가총액 데이터
def get_krx_market_price_info(trdDd):
    url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
    headers = {
        "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020202",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
        "locale": "ko_KR",
        "mktId": "ALL",
        "trdDd": trdDd,
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false"
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        data = response.json()
        df = pd.DataFrame(data['OutBlock_1'])
        df = df.rename(columns={
            "ISU_SRT_CD": "단축코드",
            "ISU_ABBRV": "종목명",
            "MKT_NM": "시장구분",
            "MKTCAP": "시가총액"
        })
        df = df[df["시장구분"] != "KONEX"]
        df["시장구분"] = df["시장구분"].str.replace("KOSDAQ GLOBAL", "KOSDAQ")
        df["시가총액"] = df["시가총액"].str.replace("-", "0").str.replace(",", "").astype(float)
        return df[["단축코드", "종목명", "시장구분", "시가총액"]]
    except Exception as e:
        st.error(f"❌ 시가총액 데이터 오류: {e}")
        return pd.DataFrame()

# ✅ Streamlit 인터페이스
st.set_page_config(page_title="신규상장 시가총액 분석", layout="wide")
st.title("📈 신규상장 종목 시가총액 편입 분석기")

col1, col2 = st.columns(2)
from_date = col1.date_input("조회 시작일", pd.to_datetime("today") - pd.Timedelta(days=5))
to_date = col2.date_input("조회 종료일", pd.to_datetime("today"))

if from_date > to_date:
    st.error("⛔ 시작일은 종료일보다 빠를 수 없습니다.")
    st.stop()

if st.button("🔍 신규상장 종목 불러오기"):
    with st.spinner("데이터 불러오는 중..."):
        listing = krx_listingcompany_normal(from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"))
        if not listing.empty:
            st.success(f"✅ 총 {len(listing)}개 종목 조회됨")
            st.dataframe(listing, use_container_width=True)
            selected = st.selectbox("분석할 종목 선택", listing["회사명"])
            if selected:
                target_date = listing[listing["회사명"] == selected]["상장일"].values[0]
                target_name = selected

                df_filtered = get_nextrade_filtered_symbols(target_date)
                market_cap = get_krx_market_price_info(target_date)

                if market_cap.empty or df_filtered.empty:
                    st.warning("⚠️ 시가총액 또는 거래가능 종목 데이터가 없습니다.")
                    st.stop()

                df_merged = df_filtered.merge(market_cap, on=["단축코드", "종목명", "시장구분"], how="left")

                try:
                    row = market_cap[market_cap["종목명"] == target_name].iloc[0]
                    target_market = row["시장구분"]
                    target_ticker = row["단축코드"]
                    target_marketcap = row["시가총액"]
                except IndexError:
                    st.error("❌ 해당 종목의 시가총액 정보 없음")
                    st.stop()

                market_df = df_merged[df_merged["시장구분"] == target_market].dropna(subset=["시가총액"]).copy()
                market_df = market_df.sort_values("시가총액", ascending=False).reset_index(drop=True)

                rank = (market_df["시가총액"] > target_marketcap).sum() + 1
                total = len(market_df)
                rank_cutoff = total // 2
                percent_rank = (rank - 1) / (total - 1) if total > 1 else 0
                marketcap_cutoff = market_df.iloc[rank_cutoff - 1]["시가총액"] if rank_cutoff - 1 < total else None
                included = "편입" if rank <= rank_cutoff else "미편입"

                st.markdown(f"""
                    ### 📝 분석 결과
                    **{target_name}**  
                    - 📅 상장일: `{target_date}`  
                    - 📊 시장: `{target_market}`  
                    - 💰 시가총액: `{int(target_marketcap):,} 원`  
                    - 📌 순위: **{rank}위 / {total}종목**  
                    - 📈 Percent Rank: **{percent_rank:.2%}**  
                    - 🧮 기준 시가총액 (상위 50%): **{int(marketcap_cutoff):,} 원**  
                    - ✅ 편입 여부: **{included}**
                """)

                summary_df = pd.DataFrame([{
                    "상장일": target_date,
                    "종목코드": target_ticker,
                    "종목명": target_name,
                    "시장": target_market,
                    "시가총액": target_marketcap,
                    "편입기준 시총": marketcap_cutoff,
                    "순위": rank,
                    "절반기준": rank_cutoff,
                    "Percent Rank": percent_rank,
                    "편입여부": included
                }])
                st.dataframe(summary_df, use_container_width=True)
        else:
            st.warning("해당 기간에 신규상장 종목이 없습니다.")
