import time
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

SEARCH_URL = "https://www.google.com/maps/search/%E8%A3%95%E5%85%83%E8%8A%B1%E5%9C%92%E9%85%92%E5%BA%97?hl=zh-TW"
OUTPUT_FILE = "reviews.csv"

# 點星評數（則評論）以打開評論面板
_REVIEW_COUNT_XPATH = (
    '//button[contains(@aria-label, "則評論") or contains(@aria-label, "reviews")]'
    '| //div[@jsaction and .//span[contains(., "則評論")]]'
    '| //span[@role="img" and contains(@aria-label, "顆星")]/following-sibling::span/button'
)

# 「展開全文」按鈕
_MORE_BTN_XPATH = (
    '//button[@aria-label="顯示更多內容" or @aria-label="See more"]'
    '[ancestor::div[@data-review-id]]'
)


def init_driver(headless=True):
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option(
        "prefs", {"intl.accept_languages": "zh-TW,zh"}
    )
    if headless:
        options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def expand_reviews(driver):
    try:
        for btn in driver.find_elements(By.XPATH, _MORE_BTN_XPATH):
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.3)
    except Exception:
        pass


def scroll_reviews(driver, panel, pause=1.5):
    last_height = driver.execute_script("return arguments[0].scrollHeight", panel)
    while True:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
        time.sleep(pause)
        expand_reviews(driver)
        new_height = driver.execute_script("return arguments[0].scrollHeight", panel)
        if new_height == last_height:
            break
        last_height = new_height


def parse_reviews(driver):
    reviews = []
    for card in driver.find_elements(By.XPATH, '//div[@data-review-id]'):
        try:
            reviewer = card.find_element(By.XPATH, './/div[@class="d4r55 "]').text.strip()
        except NoSuchElementException:
            reviewer = ""

        try:
            stars = card.find_element(By.XPATH, './/span[@role="img"]').get_attribute("aria-label")
            rating = int(''.join(filter(str.isdigit, stars[:2])))
        except (NoSuchElementException, ValueError):
            rating = None

        try:
            date = card.find_element(By.XPATH, './/span[@class="rsqaWe"]').text.strip()
        except NoSuchElementException:
            date = ""

        try:
            text = card.find_element(By.XPATH, './/span[@class="wiI7pd"]').text.strip()
        except NoSuchElementException:
            text = ""

        reviews.append({"reviewer": reviewer, "rating": rating, "date": date, "review": text})
    return reviews


def save_csv(reviews, path=OUTPUT_FILE):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["reviewer", "rating", "date", "review"])
        writer.writeheader()
        writer.writerows(reviews)
    print(f"已儲存 {len(reviews)} 筆評論 → {path}")


def scrape(output_path=OUTPUT_FILE, headless=True):
    driver = init_driver(headless=headless)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(SEARCH_URL)
        time.sleep(5)
        driver.save_screenshot("screenshot_1_loaded.png")

        # 點擊星評數字（「N 則評論」）打開評論面板
        try:
            review_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, _REVIEW_COUNT_XPATH))
            )
            review_btn.click()
        except TimeoutException:
            driver.save_screenshot("screenshot_2_fail.png")
            # 印出頁面所有可點擊的按鈕文字，方便診斷
            btns = [b.get_attribute("aria-label") or b.text for b in
                    driver.find_elements(By.XPATH, '//button')]
            raise RuntimeError(f"找不到評論入口。按鈕列表：{btns[:30]}")

        time.sleep(2)
        driver.save_screenshot("screenshot_2_reviews.png")

        panel = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]')))
        scroll_reviews(driver, panel)
        reviews = parse_reviews(driver)
        save_csv(reviews, output_path)
        return len(reviews)

    finally:
        driver.quit()


if __name__ == "__main__":
    # 本地執行時顯示瀏覽器視窗（headless=False）
    count = scrape(headless=False)
    print(f"共抓取 {count} 筆評論")
