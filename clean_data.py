import csv
import re

INPUT_FILE = "reviews.csv"
OUTPUT_FILE = "reviews_clean.csv"


def clean_date(date_str):
    d = date_str.strip()
    d = re.sub(r'上次編輯：', '', d)
    d = re.sub(r'，評論出處：.*', '', d)
    d = re.sub(r',.*', '', d)
    return d.strip()


def _is_name_like(m):
    """比對到的字串若短於 30 字，視為姓名並移除"""
    return '' if len(m.group().strip()) < 30 else m.group()


def clean_review(text):
    if not text or str(text).lower() == 'nan':
        return ""

    # 1. 移除 Google 翻譯標籤
    text = re.sub(r'\(?由 Google 提供翻譯\)?', '', text)
    text = re.sub(r'\(?原始評論\)?', '', text)

    # 2. 移除旅行類型標籤（商務人士 ❘ 獨自旅行 等）
    text = re.sub(r'[^\s]+\s*[❘|]\s*[^\s]+', '', text)

    # 3. 飯店回覆截斷：找到關鍵字就切掉其後全部
    match = re.search(
        r'親愛的|謝謝您的回饋|很抱歉這次|'
        r'這是裕元花園酒店的客服信箱|guestservice@|'
        r'祝您身體健康|期待您下次|竭盡所能協助您',
        text
    )
    if match:
        text = text[:match.start()]

    # 4. 移除「其他 N 項」及其後內容
    text = re.sub(r'其他 \d+ 項.*', '', text)

    # 5. 移除評論出處、入住日期、日期碼等元資料
    text = re.sub(r'評論出處：\s*Google', '', text)
    text = re.sub(r'入住日期[\d\.\-/年月日\s：:]+', '', text)
    text = re.sub(r'餐飲地點[^\s]{0,20}', '', text)
    text = re.sub(r'\b20\d{6}\b', '', text)

    # 6. 移除英文人名（全大寫、首字大寫、全小寫、CamelCase）
    text = re.sub(r'\b(?:[A-Z]{2,}\s){1,3}[A-Z]{2,}\b', _is_name_like, text)   # 全大寫
    text = re.sub(r'\b[A-Z][a-z]+(?:\s[A-Z][A-Za-z]*){1,3}\b', _is_name_like, text)  # 首字大寫
    text = re.sub(r'\b[a-z]+(?:\s[a-z]+){1,2}\b', _is_name_like, text)          # 全小寫
    text = re.sub(r'\b[A-Z][a-z]+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b', _is_name_like, text)  # CamelCase

    # 7. 移除英數混合代碼（如「923a Chih」）
    text = re.sub(r'\b[0-9]{1,4}[a-z]\s+[A-Z][a-z]+\b', '', text)

    # 先清除多餘空白，確保後續 ^ 錨點正確
    text = text.strip()

    # 8. 移除結尾的單字英文名（如 Fanool、Ponrt）
    text = re.sub(r'\s+[A-Z][a-z]{2,12}$', '', text)
    # 移除開頭的中英混合短名（如「Leco哈古將」）
    text = re.sub(r'^[A-Za-z]{2,6}[\u4e00-\u9fff]{1,5}\s+', '', text)

    # 9. 清理空括號
    text = re.sub(r'[（(]\s*[）)]', '', text)

    # 9. 清理多餘空白
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()

    # 10. 清理後無中文且長度 < 40 → 視為空（只剩英文名/代碼）
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
    if not has_chinese and len(text) < 40:
        return ""

    # 11. 只剩短中文人名（≤8字、無句子標點、無空格）→ 視為空
    has_sent_punct = bool(re.search(r'[，。！？、；：,!?]', text))
    if has_chinese and len(text) <= 8 and not has_sent_punct:
        return ""

    return text


def main():
    rows = []
    with open(INPUT_FILE, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['date'] = clean_date(row.get('date', ''))
            row['review'] = clean_review(row.get('review', ''))
            rows.append(row)

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['reviewer', 'rating', 'date', 'review'])
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    empty = sum(1 for r in rows if not r['review'])
    print(f"完成：{total} 筆，有評論 {total - empty} 筆，空評論 {empty} 筆 → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
