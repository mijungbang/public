import requests
import pandas as pd

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
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        time = data.get("CURRENT_DATETIME")
        items = data.get("OutBlock_1", [])
    except Exception as e:
        print("🚫 KRX 시가총액 데이터 요청 오류:", e)
        return pd.DataFrame(columns=["시장구분", "표준코드","단축코드", "종목명", "시가총액", "상장주식수", "KRX종가"])

    if not items:
        print("⚠️ KRX 응답에 유효한 데이터 없음")
        return pd.DataFrame(columns=["시장구분", "표준코드","단축코드", "종목명", "시가총액", "상장주식수", "KRX종가"])

    df = pd.DataFrame(items)

    df.rename(columns={
        "MKT_NM": "시장구분",
        "ISU_CD" : "표준코드",
        "ISU_SRT_CD": "단축코드",
        "ISU_ABBRV": "종목명",
        "MKTCAP": "시가총액",
        "LIST_SHRS":"상장주식수",
        "TDD_CLSPRC":"KRX종가"
    }, inplace=True)

    # 정제
    df = df[["시장구분", "표준코드","단축코드", "종목명", "시가총액", "상장주식수", "KRX종가"]]
    df = df[df["시장구분"] != "KONEX"]
    df["시장구분"] = df["시장구분"].str.replace("KOSDAQ GLOBAL", "KOSDAQ")
    df["시가총액"] = pd.to_numeric(df["시가총액"].str.replace(",", ""), errors="coerce").fillna(0)

    df.reset_index(drop=True, inplace=True)
    return time, df


def get_krx_index(trdDd: str):
    url = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
    headers = {
        "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010106",
        "User-Agent": "Mozilla/5.0"
    }
    payload1 = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT00601",
        "locale": "ko_KR",
        "tboxindIdx_finder_equidx0_0": "코스피 200",
        "indIdx": "1",
        "indIdx2": "028",
        "codeNmindIdx_finder_equidx0_0": "코스피 200",
        "param1indIdx_finder_equidx0_0": "",
        "trdDd": trdDd,
        "money": "3",
        "csvxls_isNo": "false",
    }
    payload2 = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT00601",
        "locale": "ko_KR",
        "tboxindIdx_finder_equidx0_0": "코스닥 150",
        "indIdx": "2",
        "indIdx2": "203",
        "codeNmindIdx_finder_equidx0_0": "코스닥 150",
        "param1indIdx_finder_equidx0_0": "",
        "trdDd": trdDd,
        "money": "3",
        "csvxls_isNo": "false",
    }

    empty_cols = ["지수구분", "단축코드", "종목명"]
    try:
        resp1 = requests.post(url, headers=headers, data=payload1, verify=False)
        resp2 = requests.post(url, headers=headers, data=payload2, verify=False)
        resp1.raise_for_status()
        resp2.raise_for_status()
        data1 = resp1.json()
        data2 = resp2.json()
        items1 = data1.get("output")
        items2 = data2.get("output")
    except Exception as e:
        print("🚫 조회 오류:", e)
        return pd.DataFrame(columns=empty_cols)

    if not items1:
        print("⚠️유효한 데이터 없음")
        return pd.DataFrame(columns=empty_cols)
        
    df1 = pd.DataFrame(items1).rename(columns={"IDX_ID": "지수구분" , "ISU_SRT_CD": "단축코드","ISU_ABBRV": "종목명"})
    df2 = pd.DataFrame(items2).rename(columns={"IDX_ID": "지수구분" , "ISU_SRT_CD": "단축코드","ISU_ABBRV": "종목명"})
    df1["지수구분"] = "K200"
    df2["지수구분"] = "Q150"

    df3 = pd.concat([df1,df2], ignore_index=True)[["지수구분","단축코드","종목명"]]
   
    return df3

def get_nextrade_filtered_symbols(trdDd):
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
        "scAggDd": trdDd,
        "scMktId": "",
        "searchKeyword": ""
    }

    try:
        response = requests.post(url, headers=headers, data=payload, verify=False)
        response.encoding = 'utf-8'
        result = response.json()

        # 필요한 키만 추출
        keep_keys = ["mktNm", "isuCd", "isuSrdCd", "isuAbwdNm","curPrc", "accTdQty", "accTrval","cptrTrdPmsnCdNm", "trdIpsbRsn"]
        raw_data = result.get('brdinfoTimeList', [])
        time = result["setTime"]
        
        filtered_data = [
            {k: item.get(k, None) for k in keep_keys}
            for item in raw_data
        ]

        df = pd.DataFrame(filtered_data)
        df.columns = ["시장구분", "표준코드", "단축코드", "종목명", "NXT현재가", "거래량", "거래대금", "거래가능시장", "거래불가사유"]
        df["단축코드"] = df["단축코드"].str[1:]
        #df = df[(df["거래가능시장"]!="거래불가")|(df["거래불가사유"]=="거래정지")]
        return time, df

    except Exception as e:
        print("🚫 오류 발생:", e)
        return pd.DataFrame()
