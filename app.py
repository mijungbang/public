import datetime
import json
import streamlit as st
import pandas as pd
from fnc import get_krx_market_price_info, get_krx_index, get_nextrade_filtered_symbols
from streamlit.components.v1 import html

# 📄 페이지 설정
st.set_page_config(page_title="KRX•NXT 전종목 시세 조회", layout="centered")
st.title("KRX•NXT 전종목 시세 조회")

# 📅 날짜 선택
today = datetime.date.today()
d1 = st.date_input("📅 기준일 선택", value=today)

# ▶️ 조회 버튼
search_clicked = st.button("시가총액 조회", use_container_width=True, type="primary")

# ===== 공통 유틸 =====
def parse_time1(raw: str) -> str:
    # 예: '2025.09.18 AM 11:26:39' 그대로
    return raw

def parse_time2(raw: str) -> str:
    # '2025-09-18 11:06' -> '2025.09.18 AM/PM 11:06'
    try:
        dt = datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M")
        ampm = "AM" if dt.hour < 12 else "PM"
        hh = dt.hour if 1 <= dt.hour <= 12 else (12 if dt.hour % 12 == 0 else dt.hour % 12)
        return f"{dt.strftime('%Y.%m.%d')} {ampm} {hh:02d}:{dt.strftime('%M')}"
    except Exception:
        return raw

def format_numbers_with_commas(df: pd.DataFrame, exclude_cols=("단축코드",)) -> pd.DataFrame:
    """정수는 콤마, 실수는 콤마+소수 둘째자리"""
    out = df.copy()
    for col in out.columns:
        if col in exclude_cols:
            continue
        s = pd.to_numeric(out[col], errors="coerce")
        if s.notna().sum() == 0:
            continue
        # 정수 여부 체크
        is_int_like = (s.dropna() % 1 == 0).all()
        if is_int_like:
            out[col] = s.map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            out[col] = s.map(lambda v: "" if pd.isna(v) else f"{float(v):,.2f}")
    return out

def display_header_and_copy(copy_id: str, data_for_copy: pd.DataFrame, date_str: str, time_str: str, label: str, show_delay: bool = True):
    """상단 정보 + 탭별 복사 버튼. label: 'KRX' or 'NXT' / show_delay: 지연 문구 노출 여부"""
    col1, col2 = st.columns([4, 1.5], vertical_alignment="center")

    delay_html = ' <span style="color:gray;">(20분 지연 정보)</span>' if show_delay else ""
    with col1:
        st.markdown(
            f"""
            <div style="line-height:1.6; font-size:14px">
              📅 <b>데이터 기준일:</b> {date_str}<br>
              ⏱️ <b>{label} 기준 시간:</b> {time_str}{delay_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    # 복사용 데이터 (단축코드 엑셀 보존)
    df_copy = data_for_copy.copy()
    if "단축코드" in df_copy.columns:
        df_copy["단축코드"] = df_copy["단축코드"].astype(str).str.zfill(6)
        df_copy["단축코드"] = df_copy["단축코드"].apply(lambda x: f'="{x}"')

    clipboard_text = df_copy.to_csv(sep="\t", index=False)
    js_safe_text = json.dumps(clipboard_text)

    with col2:
        html(f"""
        <div style="display:flex; justify-content:flex-end;">
            <button id="{copy_id}" onclick="copyToClipboard_{copy_id}()" style="
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
            function copyToClipboard_{copy_id}() {{
                const text = {js_safe_text};
                navigator.clipboard.writeText(text).then(function() {{
                    var btn = document.getElementById("{copy_id}");
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

# 🔍 조회 실행
if search_clicked:
    # ---- 1) KRX 전종목 시세 ----
    time1, df1 = get_krx_market_price_info(d1.strftime("%Y%m%d"))
    if df1 is None or len(df1) == 0:
        st.warning("📭 데이터가 없습니다.")
        st.stop()

    df1 = df1.copy()
    df1["단축코드"] = df1["단축코드"].astype(str).str.zfill(6)
    df1["시가총액"] = pd.to_numeric(df1["시가총액"], errors="coerce")
    df1 = df1[df1["시장구분"] != "KONEX"]
    df1["시장구분"] = df1["시장구분"].str.replace("KOSDAQ GLOBAL", "KOSDAQ")
    df1 = df1.sort_values(by=["시장구분", "시가총액"], ascending=[False, False]).reset_index(drop=True)

    # 보기용 포맷
    df_view1 = df1.copy()
    df_view1["시가총액"] = df_view1["시가총액"].apply(lambda x: f"{x:,.0f}")

    # ---- 2) NXT(넥스트레이드) 필터 종목 ----
    time2_raw, df_view2 = get_nextrade_filtered_symbols(d1.strftime("%Y%m%d"))
    if df_view2 is not None and len(df_view2) > 0:
        df_view2 = df_view2.copy()
        if "단축코드" in df_view2.columns:
            df_view2["단축코드"] = df_view2["단축코드"].astype(str).str.zfill(6)
        # ✅ 숫자 콤마 포맷 적용 (단축코드 제외)
        df_view2 = format_numbers_with_commas(df_view2, exclude_cols=("단축코드",))

    # 시간 문자열
    time_str_tab1 = parse_time1(time1)     # 예: '2025.09.18 AM 11:26:39'
    time_str_tab2 = parse_time2(time2_raw) # 예: '2025.09.18 AM 11:06'
    date_str = d1.strftime("%Y-%m-%d")

    # ===== 탭 UI ====
    tab1, tab2 = st.tabs(["KRX 전체 시세", "NXT 전체 시세"])
    
    # ===== 지수구분 조인 =====
    # 1) 지수 데이터 로드 (K200 + Q150)
    df_idx = get_krx_index(d1.strftime("%Y%m%d"))  # 이 함수가 df를 리턴한다면 그대로 사용
    # get_krx_index가 (time, df) 형태를 리턴한다면 아래처럼:
    # _, df_idx = get_krx_index(d1.strftime("%Y%m%d"))
    
    # 2) 필요한 컬럼만, 중복 우선순위(K200 > Q150) 정리
    df_idx = df_idx[["단축코드", "지수구분"]].copy()
    df_idx["단축코드"] = df_idx["단축코드"].astype(str).str.zfill(6)
    priority = pd.Categorical(df_idx["지수구분"], categories=["K200", "Q150"], ordered=True)
    df_idx = (
        df_idx.assign(_p=priority)
              .sort_values("_p")
              .drop_duplicates(subset="단축코드", keep="first")
              .drop(columns="_p")
    )
    
    # 3) 키 정규화
    for _df in (df_view1, df_view2):
        if _df is not None and len(_df) > 0:
            _df["단축코드"] = _df["단축코드"].astype(str).str.zfill(6)
    
    # 4) 머지
    def insert_after(df, col_to_move, after_col):
        cols = list(df.columns)
        if col_to_move in cols:
            cols.remove(col_to_move)
        i = cols.index(after_col) + 1
        cols = cols[:i] + [col_to_move] + cols[i:]
        return df[cols]
    
    if df_view1 is not None and len(df_view1) > 0:
        df_view1 = df_view1.merge(df_idx, on="단축코드", how="left")
        df_view1["지수구분"] = df_view1["지수구분"].astype(object).fillna("")  # ← 추가
        df_view1 = insert_after(df_view1, "지수구분", "시장구분")
    
    if df_view2 is not None and len(df_view2) > 0:
        df_view2 = df_view2.merge(df_idx, on="단축코드", how="left")
        df_view2["지수구분"] = df_view2["지수구분"].astype(object).fillna("")  # ← 추가
        df_view2 = insert_after(df_view2, "지수구분", "시장구분")

    with tab1:
        display_header_and_copy(
            copy_id="copy_tab1",
            data_for_copy=df_view1,
            date_str=date_str,
            time_str=time_str_tab1,
            label="KRX",
            show_delay=True,     # ⬅️ KRX는 지연 문구 표시
        )
        st.dataframe(df_view1, use_container_width=True, hide_index=True)

    with tab2:
        display_header_and_copy(
            copy_id="copy_tab2",
            data_for_copy=df_view2,
            date_str=date_str,
            time_str=time_str_tab2,
            label="NXT",
            show_delay=False,    # ⬅️ NXT는 지연 문구 숨김
        )
        st.dataframe(df_view2, use_container_width=True, hide_index=True)
