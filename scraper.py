import time
import csv
import os
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

GOOGLE_MAPS_URL = "https://www.google.com/maps/place/%E8%A3%95%E5%85%83%E8%8A%B1%E5%9C%92%E9%85%92%E5%BA%97/@24.1391,120.6837,17z"
OUTPUT_FILE = "reviews.csv"

IS_LINUX = platform.system() == "Linux"


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-notifications")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    if IS_LINUX:
        # Streamlit Cloud 使用系統 Chromium
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    return driver


def expand_reviews(driver):
    """點開所有「更多」按鈕以顯示完整評論"""
    try:
        more_buttons = driver.find_elements(By.XPATH, '//button[@aria-label="顯示更多內容"]')
        for btn in more_buttons:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.3)
    except Exception:
        pass


def scroll_reviews(driver, panel, pause=1.5):
    """在評論面板中持續捲動直到無新內容"""
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
    """爬取評論並儲存至 CSV，回傳筆數。供 app.py 呼叫。"""
    driver = init_driver()
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(GOOGLE_MAPS_URL)

        # 點擊「評論」頁籤
        reviews_tab = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[@role="tab" and contains(., "評論")]')
            )
        )
        reviews_tab.click()
        time.sleep(2)

        # 找到可捲動的評論面板
        panel = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@role="feed" and @tabindex]')
            )
        )

        scroll_reviews(driver, panel)
        reviews = parse_reviews(driver)
        save_csv(reviews, output_path)
        return len(reviews)

    except TimeoutException as e:
        raise RuntimeError(f"逾時錯誤：{e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    count = scrape()
    print(f"共抓取 {count} 筆評論")
