import json

import streamlit as st

from polymarket_autosign_example import BotConfig, PolymarketAutoTrader, find_tokens_public


def apply_theme(dark_mode: bool) -> None:
    if dark_mode:
        st.markdown(
            """
            <style>
            .stApp {background-color: #0f1117; color: #e6edf3;}
            [data-testid="stSidebar"] {background-color: #161b22;}
            [data-baseweb="input"] input, textarea {color: #e6edf3 !important;}
            .stButton>button {background-color: #21262d; color: #e6edf3; border: 1px solid #30363d;}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            .stApp {background-color: #ffffff; color: #111827;}
            [data-testid="stSidebar"] {background-color: #f8fafc;}
            .stButton>button {background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1;}
            </style>
            """,
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="Polymarket Web Trader", page_icon="📈", layout="wide")
st.title("📈 Polymarket 웹 트레이더 (Trust Wallet)")
st.caption("브라우저 팝업 대신 서버/앱에서 자동 서명 주문을 실행합니다.")

with st.sidebar:
    st.header("연결 설정")
    dark_mode = st.toggle("다크모드", value=True)
    host = st.text_input("클로브 호스트 주소", value="https://clob.polymarket.com", help="기본값을 그대로 사용하세요")
    chain_id = st.number_input("체인 ID", value=137, step=1, help="Polygon 메인넷은 137")
    signature_type = st.selectbox("서명 타입", options=[0, 1, 2], index=0, help="Trust Wallet EOA는 0")
    gamma_url = st.text_input("감마 API 주소", value="https://gamma-api.polymarket.com")

    st.markdown("---")
    st.subheader("거래 지갑 정보")
    private_key = st.text_input("개인키 (POLY_PRIVATE_KEY)", type="password")
    funder_address = st.text_input("펀더 주소 (선택)", value="", help="비우면 개인키에서 자동 계산")


apply_theme(dark_mode)

@st.cache_data(ttl=30)
def cached_find_tokens(gamma: str, query: str, limit: int):
    return find_tokens_public(gamma, query, limit)


def build_trader() -> PolymarketAutoTrader:
    if not private_key:
        raise ValueError("매수/매도를 하려면 POLY_PRIVATE_KEY를 입력하세요.")

    resolved_funder = funder_address
    if not resolved_funder:
        from eth_account import Account

        resolved_funder = Account.from_key(private_key).address

    config = BotConfig(
        host=host,
        chain_id=int(chain_id),
        private_key=private_key,
        signature_type=int(signature_type),
        funder_address=resolved_funder,
        gamma_url=gamma_url,
    )

    return PolymarketAutoTrader(config)


search_tab, trade_tab, manage_tab = st.tabs(["토큰 검색", "매수/매도", "주문 관리"])

with search_tab:
    st.subheader("Gamma API 토큰 검색")
    query = st.text_input("검색어", value="trump")
    limit = st.slider("개수", min_value=1, max_value=30, value=10)

    if st.button("토큰 검색", use_container_width=True):
        try:
            rows = cached_find_tokens(gamma_url, query, int(limit))
            if not rows:
                st.warning("검색 결과가 없습니다.")
            else:
                st.success(f"{len(rows)}개 결과")
                st.dataframe(rows, use_container_width=True)
        except Exception as exc:
            st.error(str(exc))

with trade_tab:
    st.subheader("매수/매도")

    col1, col2 = st.columns(2)
    with col1:
        side = st.selectbox("주문 방향", options=["BUY", "SELL"])
        token_id = st.text_input("TOKEN_ID", value="")
    with col2:
        price = st.number_input("가격(0~1)", min_value=0.0001, max_value=0.9999, value=0.50, step=0.01, format="%.4f")
        size = st.number_input("수량", min_value=0.0001, value=5.0, step=1.0)

    dry_run = st.checkbox("드라이런(전송 없이 검증)", value=True)

    if st.button("주문 실행", type="primary", use_container_width=True):
        try:
            trader = build_trader()
            result = trader.create_order(token_id=token_id, price=float(price), size=float(size), side=side, dry_run=dry_run)
            st.success("요청 처리 완료")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

with manage_tab:
    st.subheader("오픈 주문 / 체결 / 취소")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("오픈 주문 조회", use_container_width=True):
            try:
                trader = build_trader()
                st.json(trader.get_open_orders())
            except Exception as exc:
                st.error(str(exc))

    with c2:
        if st.button("체결 내역 조회", use_container_width=True):
            try:
                trader = build_trader()
                st.json(trader.get_trades())
            except Exception as exc:
                st.error(str(exc))

    st.markdown("---")
    order_id = st.text_input("취소할 ORDER_ID")
    if st.button("주문 취소", use_container_width=True):
        try:
            trader = build_trader()
            st.json(trader.cancel_order(order_id))
        except Exception as exc:
            st.error(str(exc))

st.markdown("---")
st.caption("보안 주의: 개인키는 테스트용 소액 지갑으로만 사용하세요.")
