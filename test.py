import requests

def test_coingecko_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    
    # 테스트용 코인들 (확실히 존재하는 ID)
    ids = ["bitcoin", "ethereum", "solana"]
    
    params = {
        "ids": ",".join(ids),
        "vs_currencies": "usd,krw"
    }

    headers = {
        "accept": "application/json",
        "user-agent": "finance-dashboard-test"
    }

    print("📡 CoinGecko 요청 중...")
    r = requests.get(url, params=params, headers=headers, timeout=10)

    print("HTTP 상태코드:", r.status_code)
    print("응답 원문:", r.text[:500])  # 혹시 HTML 에러 오는지 확인용

    if r.status_code != 200:
        print("❌ API 호출 실패")
        return

    data = r.json()

    print("\n✅ 파싱 결과:")
    for coin_id in ids:
        info = data.get(coin_id)
        if info:
            print(f"{coin_id} → USD: {info.get('usd')} / KRW: {info.get('krw')}")
        else:
            print(f"{coin_id} → ❌ 응답 없음")

if __name__ == "__main__":
    test_coingecko_prices()
