import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

# =============================
# 設定
# =============================
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "all-yui")
PRICE_DATA_FILE = "price_history.json"

# 監視したい商品リスト（楽天検索キーワードと商品名）
PRODUCTS = [
    {
        "name": "MiNiPiC キッズカメラ",
        "search_keyword": "MiNiPiC キッズカメラ",
    }
]

# =============================
# 楽天検索結果から最安値を取得
# =============================
def get_lowest_price(keyword):
    encoded = requests.utils.quote(keyword)
    url = f"https://search.rakuten.co.jp/search/mall/{encoded}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        prices = re.findall(r'(\d{1,2},\d{3})\s*円', soup.get_text())
        if not prices:
            return None, url

        # 数値に変換（3,000円以上の価格のみ対象：送料・ポイント・アクセサリ除外）
        price_nums = [int(p.replace(",", "")) for p in prices if int(p.replace(",", "")) >= 3000]
        if not price_nums:
            return None, url
        min_price = min(price_nums)
        return min_price, url

    except Exception as e:
        print(f"エラー: {e}")
        return None, url

# =============================
# 価格履歴の読み込み・保存
# =============================
def load_history():
    if os.path.exists(PRICE_DATA_FILE):
        with open(PRICE_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(PRICE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# =============================
# Slack通知
# =============================
def notify_slack(message):
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": SLACK_CHANNEL,
        "text": message
    }
    response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
    result = response.json()
    if result.get("ok"):
        print("Slack通知を送信しました ✅")
    else:
        print(f"Slack通知エラー: {result.get('error')}")

# =============================
# メイン処理
# =============================
def main():
    history = load_history()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 40)
    print("  価格監視ツール（楽天最安値チェック）")
    print("=" * 40)
    print(f"実行日時: {now}")
    print()

    for product in PRODUCTS:
        name = product["name"]
        keyword = product["search_keyword"]

        print(f"商品: {name}")
        print(f"検索キーワード: {keyword}")

        current_price, search_url = get_lowest_price(keyword)

        if current_price is None:
            print("  → 価格取得失敗")
            print()
            continue

        print(f"  → 楽天最安値: ¥{current_price:,}")

        # 前回の価格と比較
        if name in history:
            prev_price = history[name]["price"]
            prev_date = history[name]["updated_at"]
            print(f"  → 前回価格: ¥{prev_price:,}（{prev_date}）")

            if current_price < prev_price:
                diff = prev_price - current_price
                message = (
                    f"🎉 価格が下がりました！\n"
                    f"商品: {name}\n"
                    f"前回: ¥{prev_price:,} → 今回: ¥{current_price:,}\n"
                    f"値下がり: ¥{diff:,}\n"
                    f"検索URL: {search_url}"
                )
                print(f"  → 値下がり！¥{diff:,}安くなりました 🎉")
                notify_slack(message)

            elif current_price > prev_price:
                diff = current_price - prev_price
                print(f"  → 値上がり（¥{diff:,}高くなりました）")
            else:
                print(f"  → 変化なし")
        else:
            print(f"  → 初回登録（価格を記録しました）")

        # 価格履歴を更新
        history[name] = {
            "price": current_price,
            "keyword": keyword,
            "updated_at": now
        }
        print()

    save_history(history)
    print("価格履歴を保存しました → price_history.json")

if __name__ == "__main__":
    main()
