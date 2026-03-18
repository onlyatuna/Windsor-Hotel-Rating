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

GOOGLE_MAPS_URL = "https://www.google.com/maps/place/%E8%A3%95%E5%85%83%E8%8A%B1%E5%9C%92%E9%85%92%E5%BA%97/@24.1391,120.6837,17z"
OUTPUT_FILE = "reviews.csv"


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-notifications")
    # 如果不想看到瀏覽器視窗，取消下行的註解
    # options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.maximize_window()
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


def main():
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

        print("開始捲動載入評論...")
        scroll_reviews(driver, panel)

        reviews = parse_reviews(driver)
        print(f"共抓取 {len(reviews)} 筆評論")
        save_csv(reviews)

    except TimeoutException as e:
        print(f"逾時錯誤：{e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
