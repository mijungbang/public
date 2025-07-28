import streamlit as st
import requests
import pandas as pd

# 🔍 종목 정보 조회 함수
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
        response = requests.post(url, headers=headers, data=payload, timeout=10, verify=False)
        response.encoding = 'utf-8'
        result = response.json()
        keep_keys = ["aggDd", "mktNm", "isuCd", "isuSrdCd", "isuAbwdNm", "cptrTrdPmsnCdNm", "trdIpsbRsn"]
        raw_data = result.get('brdinfoTimeList', [])
        filtered_data = [{k: item.get(k, None) for k in keep_keys} for item in raw_data]
        df = pd.DataFrame(filtered_data)
        df.columns = ["집계일", "시장구분", "종목코드", "단축코드", "종목명", "거래가능시장", "거래불가사유"]
        df["단축코드"] = df["단축코드"].str[1:]
        return df
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
        return pd.DataFrame()

# 🖥️ Streamlit UI
st.set_page_config(page_title="넥스트레이드 종목 조회", layout="wide")

st.title("📊 넥스트레이드 종목 필터링")

# 📅 날짜 입력
selected_date = st.date_input("조회할 날짜 선택", pd.Timestamp.today())
formatted_date = selected_date.strftime("%Y%m%d")

if st.button("데이터 조회"):
    with st.spinner("데이터를 불러오는 중입니다..."):
        df = get_nextrade_filtered_symbols(formatted_date)
        if not df.empty:
            st.success(f"{formatted_date} 기준 종목 수: {len(df)}개")
            st.dataframe(df, use_container_width=True)
            # 다운로드 옵션
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 CSV 다운로드", data=csv, file_name=f"nextrade_{formatted_date}.csv", mime="text/csv")
        else:
            st.warning("해당 날짜에 대한 데이터가 없습니다.")
