import csv
import re

INPUT_FILE = "reviews.csv"
OUTPUT_FILE = "reviews_clean.csv"


def clean_date(date_str):
    """清理日期欄位：去除 '上次編輯：' 和 '，評論出處：...' 等附加資訊"""
    d = date_str.strip()
    d = re.sub(r'上次編輯：', '', d)
    d = re.sub(r'，評論出處：.*', '', d)
    d = re.sub(r',.*', '', d)
    return d.strip()


def clean_review(text):
    """清理評論欄位"""
    if not text:
        return ""

    # 1. 移除飯店回覆：從「親愛的」開始到句尾（含客服信箱段落）
    # 策略：找到「親愛的」位置，截斷其後所有內容（飯店回覆一律在最後）
    hotel_reply_start = re.search(r'親愛的.{1,40}您好', text)
    if hotel_reply_start:
        text = text[:hotel_reply_start.start()].strip()

    # 保底：移除「這是裕元花園酒店的客服信箱」及其後
    text = re.sub(r'這是裕元花園酒店的客服信箱.*', '', text)
    text = re.sub(r'guestservice@windsortaiwan\.com.*', '', text)

    # 2. 移除旅行類型標籤
    text = re.sub(
        r'(商務人士|度假|家庭旅遊|其他)\s*[❘|]\s*(獨自旅行|夫妻/情侶|朋友|家庭|家人)',
        '', text
    )
    text = re.sub(r'(商務人士|度假|家庭旅遊)\s*(?=[^\w]|$)', '', text)

    # 3. 移除翻譯標注
    text = re.sub(r'\(?由 Google 提供翻譯\)?', '', text)
    text = re.sub(r'\(?原始評論\)?', '', text)

    # 4. 移除「其他 N 項」截斷標記
    text = re.sub(r'其他 \d+ 項', '', text)

    # 5. 移除「入住日期」、「餐飲地點」等元資料
    text = re.sub(r'入住日期[\d\.\-/年月日\s：:]+', '', text)
    text = re.sub(r'餐飲地點[^\s]{0,20}', '', text)
    text = re.sub(r'步行友善程度[^\s]{0,10}', '', text)

    # 6. 移除評論出處標記
    text = re.sub(r'評論出處：\s*Google', '', text)

    # 7. 移除夾在評論中的英文/拼音姓名（2-4個單字，首字大寫或全大寫，長度 < 30）
    # 例：「...很方便， Satya Jeet」「下午茶好吃🥰 Maximus Yuan」「yen fang 每年過年...」
    def is_name_like(m):
        s = m.group().strip()
        return '' if len(s) < 30 else m.group()

    # 全大寫英文姓名（如 HUNG YING LIN）
    text = re.sub(r'\b(?:[A-Z]{2,}\s){1,3}[A-Z]{2,}\b', is_name_like, text)
    # 首字大寫英文姓名（如 Viola Lu、Maximus Yuan、Albert Lai）
    text = re.sub(r'\b[A-Z][a-z]+(?:\s[A-Z][A-Za-z]*){1,3}\b', is_name_like, text)
    # 全小寫英文姓名（如 yen fang、mei chen wu）
    text = re.sub(r'\b[a-z]+(?:\s[a-z]+){1,2}\b', is_name_like, text)

    # 8. 整個 review 無中文且長度 < 40 → 清空（只剩名字/代碼）
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    if chinese_count == 0 and len(text) < 40:
        text = ''

    # 9. 移除開頭的中英混合人名殘留（如「Leco哈古將」「923a Chih」）
    text = re.sub(r'^[A-Za-z0-9\u4e00-\u9fff]{2,12}(?=\s+[\u4e00-\u9fff])', '', text).strip()

    # 10. 移除日期碼（如 20260122）
    text = re.sub(r'\b20\d{6}\b', '', text)

    # 11. 移除 CamelCase 英文名（如 WanHsuan Wu、ChungLi Chang）
    text = re.sub(r'\b[A-Z][a-z]+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b', is_name_like, text)

    # 12. 移除結尾的單字英文名（如「Fanool」）
    text = re.sub(r'\s+[A-Z][a-z]{2,10}$', '', text)

    # 13. 移除開頭的中英混合名殘留（如「Leco哈古將」「Chang張忠立」）
    # 只移除「英文+1-2個中文字」的短名字模式，避免誤刪「CP值高的飯店」等正常開頭
    text = re.sub(r'^[A-Za-z]{2,8}[\u4e00-\u9fff]{1,2}(?=\s|$)', '', text).strip()

    # 14. 移除英數混合的代碼殘留（如「923a Chih」）
    text = re.sub(r'\b[0-9]{1,4}[a-z]\s+[A-Z][a-z]+\b', '', text)

    # 15. 清理空括號
    text = re.sub(r'[（(]\s*[）)]', '', text)

    # 清理多餘空白
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()

    return text


def main():
    rows = []
    with open(INPUT_FILE, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['date'] = clean_date(row.get('date', ''))
            row['review'] = clean_review(row.get('review', ''))
            rows.append(row)

    # 移除 review 幾乎為空的列（清理後少於 5 字）
    before = len(rows)
    rows = [r for r in rows if len(r['review']) >= 5 or r['rating']]
    after = len(rows)
    print(f"清理前：{before} 筆，清理後：{after} 筆（移除 {before - after} 筆空評論）")

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['reviewer', 'rating', 'date', 'review'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"已儲存 → {OUTPUT_FILE}")

    # 預覽前 10 筆
    print("\n=== 預覽前 10 筆 ===")
    for i, r in enumerate(rows[:10], 1):
        review_preview = r['review'][:60] + '...' if len(r['review']) > 60 else r['review']
        print(f"{i:2}. [{r['rating']}★] {r['reviewer']:<15} | {r['date']:<10} | {review_preview}")


if __name__ == "__main__":
    main()
