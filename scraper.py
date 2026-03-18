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

# 評論頁籤的可能文字（中文 / 英文 / 備用 aria-label）
_REVIEWS_TAB_XPATH = (
    '//button[@role="tab" and ('
    'contains(., "評論") or contains(., "Reviews") or '
    'contains(@aria-label, "評論") or contains(@aria-label, "Reviews"))]'
)
# 「展開」按鈕（中英文）
_MORE_BTN_XPATH = (
    '//button[contains(@aria-label, "更多") or contains(@aria-label, "More") '
    'or contains(., "更多") or contains(., "More")]'
    '[ancestor::div[@data-review-id]]'
)


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--accept-lang=zh-TW,zh;q=0.9")
    options.add_argument("--disable-notifications")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option(
        "prefs", {"intl.accept_languages": "zh-TW,zh"}
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def expand_reviews(driver):
    try:
        more_buttons = driver.find_elements(By.XPATH, _MORE_BTN_XPATH)
        for btn in more_buttons:
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
    cards = driver.find_elements(By.XPATH, '//div[@data-review-id]')
    for card in cards:
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

        reviews.append({
            "reviewer": reviewer,
            "rating": rating,
            "date": date,
            "review": text,
        })
    return reviews


def save_csv(reviews, path=OUTPUT_FILE):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["reviewer", "rating", "date", "review"])
        writer.writeheader()
        writer.writerows(reviews)
    print(f"已儲存 {len(reviews)} 筆評論 → {path}")


def scrape(output_path=OUTPUT_FILE):
    driver = init_driver()
    wait = WebDriverWait(driver, 30)

    try:
        # 1. 搜尋飯店
        driver.get(SEARCH_URL)
        time.sleep(4)
        driver.save_screenshot("screenshot_1_search.png")

        # 2. 點擊第一個搜尋結果，打開詳情面板
        first_result = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '(//a[@href and contains(@href,"/maps/place/")])[1]')
            )
        )
        first_result.click()
        time.sleep(3)
        driver.save_screenshot("screenshot_2_detail.png")

        # 3. 點擊「評論」頁籤
        try:
            reviews_tab = wait.until(EC.element_to_be_clickable((By.XPATH, _REVIEWS_TAB_XPATH)))
            reviews_tab.click()
        except TimeoutException:
            driver.save_screenshot("screenshot_3_tab_fail.png")
            tabs = driver.find_elements(By.XPATH, '//button[@role="tab"]')
            tab_texts = [t.text for t in tabs]
            raise RuntimeError(f"找不到評論頁籤。目前 tabs：{tab_texts}")

        time.sleep(2)
        driver.save_screenshot("screenshot_reviews.png")

        # 找到可捲動的評論面板
        panel = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )

        scroll_reviews(driver, panel)
        reviews = parse_reviews(driver)
        save_csv(reviews, output_path)
        return len(reviews)

    finally:
        driver.quit()


if __name__ == "__main__":
    count = scrape()
    print(f"共抓取 {count} 筆評論")
