"""Polymarket 자동 주문 스크립트 (Trust Wallet / EOA 기본).

공식 가이드(Placing Your First Order) 기반:
1) private key로 bootstrap client 생성
2) user API creds 유도
3) signature_type/funder 포함 client 재초기화
4) market 메타(tickSize/negRisk) 조회 후 주문 생성+전송

추가 기능:
- Gamma API 기반 토큰 검색(find-token)
- buy/sell 드라이런(--dry-run)

사용 예시:
  python polymarket_autosign_example.py find-token --query "trump"
  python polymarket_autosign_example.py buy --token-id <TOKEN_ID> --price 0.52 --size 5
  python polymarket_autosign_example.py buy --token-id <TOKEN_ID> --price 0.52 --size 5 --dry-run
  python polymarket_autosign_example.py sell --token-id <TOKEN_ID> --price 0.70 --size 2
  python polymarket_autosign_example.py open-orders
  python polymarket_autosign_example.py trades
  python polymarket_autosign_example.py cancel --order-id <ORDER_ID>

필수 환경변수:
- POLY_PRIVATE_KEY

선택 환경변수:
- POLY_HOST (default: https://clob.polymarket.com)
- POLY_CHAIN_ID (default: 137)
- POLY_SIGNATURE_TYPE (default: 0)
- POLY_FUNDER_ADDRESS (미설정 시 private key에서 자동 계산)
- POLY_GAMMA_URL (default: https://gamma-api.polymarket.com)
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass
class BotConfig:
    host: str
    chain_id: int
    private_key: str
    signature_type: int
    funder_address: str
    gamma_url: str

    @staticmethod
    def from_env() -> "BotConfig":
        host = os.getenv("POLY_HOST", "https://clob.polymarket.com")
        chain_id = int(os.getenv("POLY_CHAIN_ID", "137"))
        private_key = os.getenv("POLY_PRIVATE_KEY", "")
        signature_type = int(os.getenv("POLY_SIGNATURE_TYPE", "0"))
        gamma_url = os.getenv("POLY_GAMMA_URL", "https://gamma-api.polymarket.com")

        if not private_key:
            raise ValueError("POLY_PRIVATE_KEY 환경변수가 비어 있습니다.")

        if signature_type not in (0, 1, 2):
            raise ValueError("POLY_SIGNATURE_TYPE는 0, 1, 2 중 하나여야 합니다.")

        from eth_account import Account

        inferred_address = Account.from_key(private_key).address
        funder_address = os.getenv("POLY_FUNDER_ADDRESS", inferred_address)

        return BotConfig(
            host=host,
            chain_id=chain_id,
            private_key=private_key,
            signature_type=signature_type,
            funder_address=funder_address,
            gamma_url=gamma_url,
        )


class PolymarketAutoTrader:
    def __init__(self, config: BotConfig) -> None:
        from py_clob_client.client import ClobClient

        bootstrap_client = ClobClient(config.host, key=config.private_key, chain_id=config.chain_id)
        user_api_creds = bootstrap_client.create_or_derive_api_creds()

        self.client = ClobClient(
            config.host,
            key=config.private_key,
            chain_id=config.chain_id,
            creds=user_api_creds,
            signature_type=config.signature_type,
            funder=config.funder_address,
        )

    def create_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not 0 < price < 1:
            raise ValueError("price는 0과 1 사이여야 합니다. (예: 0.53)")
        if size <= 0:
            raise ValueError("size는 0보다 커야 합니다.")

        market = self.client.get_market(token_id)
        from py_clob_client.clob_types import OrderArgs, OrderType

        order_args = OrderArgs(token_id=token_id, price=price, size=size, side=side)
        options = {
            "tick_size": market["tickSize"],
            "neg_risk": market["negRisk"],
        }

        if dry_run:
            return {
                "dry_run": True,
                "order": {
                    "token_id": token_id,
                    "price": price,
                    "size": size,
                    "side": side,
                    "order_type": "GTC",
                },
                "market": {
                    "tickSize": market["tickSize"],
                    "negRisk": market["negRisk"],
                },
            }

        return self.client.create_and_post_order(order_args, options=options, order_type=OrderType.GTC)

    def get_open_orders(self) -> list[dict[str, Any]]:
        return self.client.get_open_orders()

    def get_trades(self) -> list[dict[str, Any]]:
        return self.client.get_trades()

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return self.client.cancel_order(order_id)





def find_tokens_public(gamma_url: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    params = urlencode({"search": query, "limit": limit})
    url = f"{gamma_url.rstrip('/')}/markets?{params}"

    try:
        with urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, OSError) as exc:
        raise RuntimeError(f"Gamma API 요청 실패: {exc}") from exc

    if not isinstance(payload, list):
        return []

    results: list[dict[str, Any]] = []
    for market in payload:
        question = market.get("question") or market.get("title") or ""
        slug = market.get("slug")
        for outcome in market.get("outcomeTokens", []) or []:
            results.append(
                {
                    "question": question,
                    "slug": slug,
                    "outcome": outcome.get("outcome"),
                    "token_id": outcome.get("token_id") or outcome.get("tokenId"),
                }
            )

    return [row for row in results if row.get("token_id")]

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Polymarket 자동 주문 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    find_token = sub.add_parser("find-token", help="Gamma API로 token_id 검색")
    find_token.add_argument("--query", required=True)
    find_token.add_argument("--limit", type=int, default=10)

    buy = sub.add_parser("buy", help="BUY 주문")
    buy.add_argument("--token-id", required=True)
    buy.add_argument("--price", type=float, required=True)
    buy.add_argument("--size", type=float, required=True)
    buy.add_argument("--dry-run", action="store_true")

    sell = sub.add_parser("sell", help="SELL 주문")
    sell.add_argument("--token-id", required=True)
    sell.add_argument("--price", type=float, required=True)
    sell.add_argument("--size", type=float, required=True)
    sell.add_argument("--dry-run", action="store_true")

    sub.add_parser("open-orders", help="오픈 주문 조회")
    sub.add_parser("trades", help="체결 내역 조회")

    cancel = sub.add_parser("cancel", help="주문 취소")
    cancel.add_argument("--order-id", required=True)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    try:
        if args.command == "find-token":
            gamma_url = os.getenv("POLY_GAMMA_URL", "https://gamma-api.polymarket.com")
            result = find_tokens_public(gamma_url, args.query, args.limit)
        else:
            config = BotConfig.from_env()
            trader = PolymarketAutoTrader(config)

            if args.command == "buy":
                result = trader.create_order(args.token_id, args.price, args.size, "BUY", dry_run=args.dry_run)
            elif args.command == "sell":
                result = trader.create_order(args.token_id, args.price, args.size, "SELL", dry_run=args.dry_run)
            elif args.command == "open-orders":
                result = trader.get_open_orders()
            elif args.command == "trades":
                result = trader.get_trades()
            elif args.command == "cancel":
                result = trader.cancel_order(args.order_id)
            else:
                raise RuntimeError("지원하지 않는 명령입니다.")

        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        error_payload = {"ok": False, "error": str(exc)}
        print(json.dumps(error_payload, indent=2, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
