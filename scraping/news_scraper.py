import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_yahoo_news():
    url = "https://news.yahoo.co.jp/"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # ヘッドラインを取得
    headlines = soup.select("a[href*='/articles/']")

    print(f"=== Yahoo!ニュース ヘッドライン ===")
    print(f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    seen = set()
    count = 0
    for item in headlines:
        text = item.get_text(strip=True)
        if text and text not in seen and len(text) > 10:
            seen.add(text)
            count += 1
            print(f"{count}. {text}")
            if count >= 10:
                break

    print()
    print(f"合計 {count} 件取得しました")

if __name__ == "__main__":
    get_yahoo_news()
