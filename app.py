import datetime
import streamlit as st
import pandas as pd
from fnc import get_krx_market_price_info
from streamlit.components.v1 import html

# 📄 페이지 설정
st.set_page_config(page_title="[12001] KRX 전종목 시세 조회", layout="centered")
st.title("[12001] KRX 전종목 시세 조회")

# 📅 날짜 선택
today = datetime.date.today()
d1 = st.date_input("📅 기준일 선택", value=today)

# ▶️ 조회 버튼
search_clicked = st.button("시가총액 조회", use_container_width=True, type="primary")

# 🔍 조회 실행
if search_clicked:
    time, df = get_krx_market_price_info(d1.strftime("%Y%m%d"))

    if df is None or len(df) == 0:
        st.warning("📭 데이터가 없습니다.")
        st.stop()

    # 정제 및 정렬
    df["단축코드"] = df["단축코드"].astype(str).str.zfill(6)
    df["시가총액"] = pd.to_numeric(df["시가총액"], errors="coerce")
    df = df[df["시장구분"] != "KONEX"]
    df["시장구분"] = df["시장구분"].str.replace("KOSDAQ GLOBAL", "KOSDAQ")
    df = df.sort_values(by=["시장구분", "시가총액"], ascending=[False, False]).reset_index(drop=True)
    df["시가총액"] = df["시가총액"].apply(lambda x: f"{x:,.0f}")

    # 📅 기준일 & 복사 버튼 레이아웃
    col1, col2 = st.columns([4, 1.5])
    with col1:
        st.markdown(
            f"""
            <div style="line-height:1.6; font-size:14px">
            📅 <b>데이터 기준일:</b> {d1.strftime('%Y-%m-%d')}  
            <br>⏱️ <b>KRX 기준 시간:</b> {time} <span style="color:gray;">(20분 지연 정보)</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 복사할 탭 구분 텍스트
    df_view = df.copy()
    df["단축코드"] = df["단축코드"].apply(lambda x: f'="{x}"')
    clipboard_text = df.to_csv(sep="\t", index=False)

    # 📋 클립보드 복사 버튼
    with col2:
        html(f"""
        <div style="display:flex; justify-content:flex-end;">
            <button id="copyButton" onclick="copyToClipboard()" style="
                font-size:15px;
                padding:6px 12px;
                width: 100%;
                background-color:#4CAF50;
                color:white;
                border:none;
                border-radius:4px;
                cursor:pointer;
                transition: background-color 0.3s;
            ">📋 복사</button>
        </div>
        <script>
            function copyToClipboard() {{
                navigator.clipboard.writeText(`{clipboard_text}`).then(function() {{
                    var btn = document.getElementById("copyButton");
                    btn.innerText = "✅ 복사 완료";
                    btn.style.backgroundColor = "#777";
                    setTimeout(function() {{
                        btn.innerText = "📋 복사";
                        btn.style.backgroundColor = "#4CAF50";
                    }}, 2000);
                }});
            }}
        </script>
        """, height=45)

    # 🧾 시가총액 테이블 출력
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    
