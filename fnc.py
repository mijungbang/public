import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib3

def get_krx_market_price_info(trdDd):
    import requests
    import pandas as pd

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
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        time = data.get("CURRENT_DATETIME")
        items = data.get("OutBlock_1", [])
    except Exception as e:
        print("🚫 KRX 시가총액 데이터 요청 오류:", e)
        return pd.DataFrame(columns=["단축코드", "종목명", "시장구분", "시가총액"])

    if not items:
        print("⚠️ KRX 응답에 유효한 데이터 없음")
        return pd.DataFrame(columns=["단축코드", "종목명", "시장구분", "시가총액"])

    df = pd.DataFrame(items)

    df.rename(columns={
        "MKT_NM": "시장구분",
        "ISU_CD" : "표준코드",
        "ISU_SRT_CD": "단축코드",
        "ISU_ABBRV": "종목명",
        "MKTCAP": "시가총액"
    }, inplace=True)

    # 정제
    df = df[["시장구분", "표준코드","단축코드", "종목명", "시가총액"]]
    df = df[df["시장구분"] != "KONEX"]
    df["시장구분"] = df["시장구분"].str.replace("KOSDAQ GLOBAL", "KOSDAQ")
    df["시가총액"] = pd.to_numeric(df["시가총액"].str.replace(",", ""), errors="coerce").fillna(0)

    df.reset_index(drop=True, inplace=True)
    return time, df
