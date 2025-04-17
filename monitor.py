import yfinance as yf
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd

# === 設定區 ===
STOCK_SYMBOL = "2330.TW"
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")
TO_EMAIL = os.environ.get("TO_EMAIL")

def send_email(subject, content):
    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=TO_EMAIL,
            subject=subject,
            plain_text_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print(f">>> Email sent: {subject}")
    except Exception as e:
        print(f">>> Failed to send email: {e}")

def get_price_data():
    try:
        df = yf.download(STOCK_SYMBOL, period="30d", interval="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            print(">>> 資料抓取失敗或缺少欄位")
            return None

        current_price = df["Close"].iloc[-1].item()
        ma20 = df["Close"].rolling(window=20).mean().iloc[-1]

        if pd.isna(ma20):
            print(">>> MA20 資料不足")
            return None

        return current_price, ma20.item()
    except Exception as e:
        print(f">>> 取得資料錯誤：{e}")
        return None

def main():
    result = get_price_data()
    if not result:
        print(">>> 無法取得股價資料")
        return

    current_price, ma20 = result
    print(f">>> 現價：{current_price:.2f} / MA20：{ma20:.2f}")

    # 儲存上一次的狀態
    state_file = "last_state.txt"
    try:
        with open(state_file, "r") as f:
            below_price = float(f.read().strip())
    except:
        below_price = None

    if current_price < ma20:
        if below_price is None:
            # 第一次跌破
            send_email("【TSMC 警示】跌破 20 日均線", f"目前股價 {current_price:.2f}，已跌破均線 {ma20:.2f}")
            below_price = current_price
        else:
            drop_pct = (below_price - current_price) / below_price * 100
            if drop_pct >= 10:
                send_email("【TSMC 警示】跌破後再跌 10%", f"目前股價 {current_price:.2f}，自跌破價 {below_price:.2f}，下跌 {drop_pct:.2f}%")
                below_price = below_price  # 維持原值
            elif drop_pct >= 5:
                send_email("【TSMC 警示】跌破後再跌 5%", f"目前股價 {current_price:.2f}，自跌破價 {below_price:.2f}，下跌 {drop_pct:.2f}%")
    else:
        below_price = None  # 重置狀態

    # 更新狀態檔
    with open(state_file, "w") as f:
        f.write(str(below_price) if below_price is not None else "")

if __name__ == "__main__":
    main()
