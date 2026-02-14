# Polymarket 자동서명 트레이딩 가이드 (Trust Wallet 기준)

Polymarket 공식 "Placing Your First Order" 흐름을 기준으로,
Trust Wallet(EOA)에서 팝업 클릭 없이 서버에서 자동 서명/주문하는 방법입니다.

## 핵심

- 서명은 필수(무서명 불가)
- 수동 팝업 대신 서버가 개인키로 자동 서명 가능

## 설치

```bash
pip install py-clob-client eth-account
```

## 환경변수

```bash
export POLY_PRIVATE_KEY="0x..."
export POLY_HOST="https://clob.polymarket.com"
export POLY_CHAIN_ID="137"
export POLY_SIGNATURE_TYPE="0"      # Trust Wallet EOA 기본
# 선택: export POLY_FUNDER_ADDRESS="0x..."
# 선택: export POLY_GAMMA_URL="https://gamma-api.polymarket.com"
```

- `POLY_FUNDER_ADDRESS` 미설정 시 private key로 자동 계산
- `POLY_SIGNATURE_TYPE`:
  - `0`: EOA (Trust Wallet 직접지갑)
  - `1`: POLY_PROXY
  - `2`: GNOSIS_SAFE

## 웹 화면으로 사용하기 (추천)

브라우저 화면에서 바로 검색/매수/매도/취소하려면 Streamlit 앱을 실행하세요.

```bash
streamlit run polymarket_web_app.py
```

화면 기능:
- 토큰 검색(Gamma API)
- 매수/매도 + 드라이런
- 오픈 주문/체결 조회
- 주문 취소
- 사이드바 한글 라벨 + 다크모드 토글 지원

## 구현 순서 (공식 순서 반영)

1. private key로 bootstrap `ClobClient`
2. `create_or_derive_api_creds()` 실행
3. `creds + signature_type + funder`로 client 재초기화
4. `get_market(token_id)`로 `tickSize`, `negRisk` 조회
5. `create_and_post_order(...)`로 주문 생성/서명/전송

## CLI 사용법

```bash
# 1) 토큰 검색 (Gamma API)
python polymarket_autosign_example.py find-token --query "trump" --limit 10

# 2) BUY (실주문)
python polymarket_autosign_example.py buy --token-id <TOKEN_ID> --price 0.52 --size 5

# 3) BUY 드라이런 (전송 없이 검증)
python polymarket_autosign_example.py buy --token-id <TOKEN_ID> --price 0.52 --size 5 --dry-run

# 4) SELL
python polymarket_autosign_example.py sell --token-id <TOKEN_ID> --price 0.70 --size 2

# 5) 오픈 주문 조회
python polymarket_autosign_example.py open-orders

# 6) 체결 내역 조회
python polymarket_autosign_example.py trades

# 7) 주문 취소
python polymarket_autosign_example.py cancel --order-id <ORDER_ID>
```

## 주의사항

- `price`는 0~1 사이, `size`는 0 초과여야 함
- 실거래 전 `--dry-run` + 소액 테스트 필수
- 토큰 ID는 Gamma API 검색 결과를 사용

## 트러블슈팅

- Invalid signature: signature_type/funder/private key 조합 오류
- Unauthorized: user API creds mismatch
- Not enough balance/allowance: 잔고/승인 부족
- Geoblock: 제한 지역 요청
- 네트워크/차단 이슈 시 CLI가 스택트레이스 대신 JSON 에러(`{"ok": false, "error": "..."}`)를 출력
