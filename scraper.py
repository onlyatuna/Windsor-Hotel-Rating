import time
import csv
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

SEARCH_URL = "https://www.google.com/travel/hotels/entity/CgsI2ZfEg47M6-D5ARAB/reviews?q=%E8%A3%95%E5%85%83%E8%8A%B1%E5%9C%92%E9%85%92%E5%BA%97&hl=zh-Hant-TW&gl=tw"
OUTPUT_FILE = "reviews.csv"

# 點星評數（則評論）以打開評論面板
_REVIEW_COUNT_XPATH = (
    '//button[contains(@aria-label, "則評論") or contains(@aria-label, "reviews") or contains(@aria-label, "顆星")]'
    '| //div[@role="button" and contains(., "則評論")]'
    '| //*[contains(text(), "則評論")]'
)

# 「展開全文」按鈕
_MORE_BTN_XPATH = (
    '//button[@aria-label="顯示更多內容" or @aria-label="See more"]'
    '[ancestor::div[@data-review-id]]'
)


def init_driver(headless=True):
    options = uc.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option(
        "prefs", {"intl.accept_languages": "zh-TW,zh"}
    )
    return uc.Chrome(options=options, headless=headless, use_subprocess=False)


def expand_reviews(driver):
    try:
        for btn in driver.find_elements(By.XPATH, _MORE_BTN_XPATH):
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.3)
    except Exception:
        pass


def set_sort_to_latest(driver):
    """嘗試切換評論排序為「最新評論」。"""

    def _log_candidates(candidates):
        print(f"🔎 找到 {len(candidates)} 個可能排序選項（只印前 10 個）")
        for i, c in enumerate(candidates[:10], 1):
            print(f"  {i}. tag={c['tag']} text={c['text']!r} aria={c.get('aria')} role={c.get('role')}")

    # 1) 點擊「最有幫助」以展開排序選單
    try:
        candidates = driver.find_elements(By.XPATH, "//*[contains(normalize-space(text()), '最有幫助')]")
        if candidates:
            _log_candidates([{"tag": c.tag_name, "text": c.text, "aria": c.get_attribute('aria-label'), "role": c.get_attribute('role')} for c in candidates])
            driver.execute_script("arguments[0].click();", candidates[0])
            time.sleep(1.5)
            print("✓ 已點擊「最有幫助」展開排序選單")
        else:
            print("⚠️ 未找到含「最有幫助」的元素")
    except Exception as e:
        print(f"⚠️ 嘗試點擊『最有幫助』失敗: {e}")

    # 2) 在展開的選單中點擊「最新評論」（role=option）
    try:
        latest = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH,
                "//div[@role='option' and (.//span[normalize-space(text())='最新評論'] or .//span[contains(text(), '最新評論')])]")
        ))
        print(f"🔎 找到排序選項: {latest.text}")
        driver.execute_script("arguments[0].click();", latest)
        time.sleep(2)
        print("✓ 已切換到「最新評論」排序")
        return True
    except Exception as e:
        print(f"⚠️ 未能直接點擊『最新評論』(role=option): {e}")

    # 3) 嘗試用 JS 直接點擊 role=option 的「最新評論」項目
    try:
        found = driver.execute_script("""
            const candidates = Array.from(document.querySelectorAll("div[role='option']"));
            const latest = candidates.find(el => el.textContent && el.textContent.trim().includes('最新評論'));
            if (latest) { latest.click(); return true; }
            return false;
        """)
        if found:
            time.sleep(2)
            print("✓ 已透過 JS 切換到「最新評論」排序 (role=option)")
            return True
        else:
            print("⚠️ JS 模式未找到『最新評論』選項 (role=option)")
    except Exception as e:
        print(f"⚠️ JS 模式查找『最新評論』失敗 (role=option): {e}")

    print("⚠️ 無法切換到「最新評論」排序，將繼續使用預設排序")
    return False


def scroll_reviews(driver, panel, pause=3):
    """向下滾動評論面板以載入新評論"""
    try:
        # 先試著清空任何現有的狀態
        driver.execute_script("window.scrollTo(0, window.scrollY);")
        time.sleep(0.5)
        
        # 檢查合適的滾動目標
        scroll_by = driver.execute_script("""
            // 檢查是否有特定的滾動容器（如評論區域）
            const feedContainers = document.querySelectorAll('[role="feed"], [role="region"]');
            if (feedContainers.length > 0 && feedContainers[0].scrollHeight > window.innerHeight) {
                return 'container';
            }
            // 否則使用整頁滾動
            if (document.documentElement.scrollHeight > window.innerHeight) {
                return 'page';
            }
            return 'body';
        """)
        
        print(f"📍 滾動目標: {scroll_by}")
        
        if scroll_by == 'container':
            # 滾動指定容器
            last_height = driver.execute_script("""
                const feed = document.querySelector('[role="feed"]') || document.querySelector('[role="region"]');
                return feed ? feed.scrollHeight : 0;
            """)
            print(f"  容器初始高度: {last_height}")
            
            for i in range(5):  # 最多滾動5次
                driver.execute_script("""
                    const feed = document.querySelector('[role="feed"]') || document.querySelector('[role="region"]');
                    if (feed) {
                        feed.scrollTop = feed.scrollHeight;
                    }
                """)
                print(f"  ↓ 滾動({i+1}/5)...", end="")
                time.sleep(pause)
                expand_reviews(driver)
                time.sleep(0.5)
                
                new_height = driver.execute_script("""
                    const feed = document.querySelector('[role="feed"]') || document.querySelector('[role="region"]');
                    return feed ? feed.scrollHeight : 0;
                """)
                
                if new_height > last_height:
                    print(f" ✓ 載入新內容 ({last_height} → {new_height})")
                    last_height = new_height
                else:
                    print(f" ✗ 無新內容")
                    
        else:
            # 滾動整個頁面
            last_height = driver.execute_script("return document.documentElement.scrollHeight || document.body.scrollHeight")
            print(f"  頁面初始高度: {last_height}")
            
            last_count = driver.execute_script("return (document.body.innerText.match(/發表時間/g) || []).length")
            print(f"  初始評論數量: {last_count}")
            plateau = 0
            max_plateau = 6
            
            for i in range(40):  # 最多滾動40次（每次滾動較少）
                # 先往上拉一點再往下滾，讓 lazy load/滾動偵測觸發
                driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.2)
                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.4)
                expand_reviews(driver)
                time.sleep(0.4)

                new_count = driver.execute_script("return (document.body.innerText.match(/發表時間/g) || []).length")
                new_height = driver.execute_script("return document.documentElement.scrollHeight || document.body.scrollHeight")

                print(f"  ↓ 滾動({i+1}/40) 高度 {new_height} 評論數 {new_count}", end="")

                if new_count > last_count:
                    plateau = 0
                    print(f" ✓ (+{new_count - last_count})")
                    last_count = new_count
                    last_height = new_height
                else:
                    plateau += 1
                    print(f" ✗ (無新增, plateau={plateau})")
                    if plateau >= max_plateau:
                        print("  ▶ 停止滾動：連續多次未新增評論")
                        break
            
            print(f"  最終評論數量: {last_count}")
                    
    except Exception as e:
        print(f"⚠️ 滾動過程中出錯: {e}")


def parse_reviews(driver):
    reviews = []
    
    # 使用更精確的 JavaScript 方法
    try:
        review_data = driver.execute_script("""
        const reviews = [];
        
        // Google Hotels 的評論頁面結構：每個評論是一個特定的容器
        // 我們尋找包含完整評論信息的最小單位
        
        // 方法：尋找所有包含"發表時間"和"/5"星級的分組
        const textContent = document.body.innerText;
        const lines = textContent.split('\\n').map(l => l.trim()).filter(l => l);
        
        let i = 0;
        while (i < lines.length) {
            const line = lines[i];
            
            // 檢查是否是評論者名字行（通常是短字符串，後面跟發表時間）
            if (i + 1 < lines.length) {
                const nextLine = lines[i + 1];
                const nextNextLine = i + 2 < lines.length ? lines[i + 2] : '';
                
                // 評論的典型模式：名字 -> 時間 -> 評分（如 "1/5" 或 "4/5"）
                if ((nextLine.includes('發表時間') || nextLine.includes('個月前') || nextLine.includes('週前')) &&
                    (nextNextLine.match(/\\d\\/5/) || nextLine.match(/\\d\\/5/))) {
                    
                    const reviewer = line;
                    let rating = null;
                    let date = '';
                    let reviewText = [];
                    
                    // 從下一行開始收集信息
                    let j = i + 1;
                    let foundRating = false;
                    
                    while (j < lines.length && j < i + 50) {  // 最多讀50行
                        const current = lines[j];
                        
                        // 提取評分
                        if (current.match(/^\\d\\/5$/)) {
                            rating = parseInt(current[0]);
                            foundRating = true;
                            j++;
                            break;
                        }
                        
                        // 提取日期
                        if (current.includes('發表時間') && !date) {
                            date = current.replace('發表時間：', '').replace('發表時間', '').trim();
                        }
                        
                        j++;
                    }
                    
                    // 收集評論文本（跳過元數據）
                    while (j < lines.length && j < i + 100) {
                        const current = lines[j];
                        
                        // 停止條件：遇到下一個評論者（通常是下一個"發表時間"之前的短行）
                        if (current.length > 2 && j > i + 10 &&
                            (j + 1 < lines.length) && 
                            (lines[j + 1].includes('發表時間') || 
                             (lines[j + 1].match(/\\d\\/5/) && current.length < 20))) {
                            break;
                        }
                        
                        // 跳過元數據行
                        if (current.includes('度假') || current.includes('家庭') || 
                            current.includes('業主回應') || current.includes('相片') ||
                            current.includes('客房') || current.includes('服務') ||
                            current.includes('位置') || current.includes('飯店特色') ||
                            current.includes('發表時間') || current.match(/^\\d\\/5$/) ||
                            current.includes('評論出處')) {
                            j++;
                            continue;
                        }
                        
                        if (current.length > 5 && !current.includes('閱讀完整')) {
                            reviewText.push(current);
                        }
                        j++;
                    }
                    
                    // 只有當有有效數據時才保存
                    if ((reviewer && reviewer.length < 30) && foundRating) {
                        reviews.push({
                            reviewer: reviewer,
                            rating: rating,
                            date: date.substring(0, 100),
                            review: reviewText.join(' ').substring(0, 1000)
                        });
                    }
                    
                    i = j;
                    continue;
                }
            }
            
            i++;
        }
        
        return reviews;
        """)
        
        if review_data and len(review_data) > 0:
            print(f"✓ JavaScript 提取了 {len(review_data)} 筆評論")
            reviews = review_data
        else:
            print("⚠ JavaScript 未能提取評論")
    except Exception as e:
        print(f"JavaScript 提取失敗: {e}")
    
    # 如果 JavaScript 方法失敗，嘗試備用方法
    if not reviews:
        print("嘗試備用方法：掃描頁面文本...")
        page_text = driver.execute_script("return document.body.innerText")
        
        # 檢查頁面上是否有評論
        if "發表時間" in page_text:
            print("✓ 頁面確實包含評論")
            # 簡單地將任何包含評論指示的元素視為評論卡片
            try:
                # 尋找所有可能是評論卡片的容器
                for container in driver.find_elements(By.XPATH, '//div[contains(text(), "發表時間")]'):
                    container_text = container.text.strip()
                    if container_text:
                        lines = container_text.split('\n')
                        reviewer = lines[0] if lines else ""
                        rating = None
                        date = ""
                        review = ""
                        
                        # 快速解析
                        for line in lines:
                            if "/5" in line:
                                try:
                                    rating = int(line.split("/5")[0].split()[-1])
                                except:
                                    pass
                            if "發表時間" in line:
                                date_part = line.split("發表時間")[-1].strip()
                                date = date_part.replace("評論出處： Google", "").strip()
                        
                        if reviewer:
                            reviews.append({
                                "reviewer": reviewer,
                                "rating": rating,
                                "date": date,
                                "review": container_text
                            })
            except:
                pass
    
    print(f"\n✅ 共提取 {len(reviews)} 筆評論")
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

    try:
        print(f"正在訪問: {SEARCH_URL}")
        driver.get(SEARCH_URL)
        print("📋 頁面正在加載中... (等待 5 秒)")
        time.sleep(5)
        
        # 檢查當前頁面是否已加載
        current_height = driver.execute_script("return document.body.scrollHeight")
        print(f"✓ 頁面已加載，初始高度: {current_height} px")
        driver.save_screenshot("screenshot_1_loaded.png")

        # 儘可能切換到「最新」排序（可顯示更多評論）
        set_sort_to_latest(driver)
        time.sleep(2)

        # 不嚴格等待特定元素，直接開始滾動頁面
        print("📍 準備開始滾動...")
        panel = None
        try:
            # 嘗試找到評論的主容器（但不強制等待）
            containers = driver.find_elements(By.XPATH, 
                '//*[@role="feed"] | '
                '//div[contains(@class, "review-container")] | '
                '//main | '
                '//div[@role="main"]'
            )
            if containers:
                panel = containers[0]
                print(f"✓ 找到評論容器")
            else:
                panel = driver.find_element(By.TAG_NAME, 'body')
                print("📍 將在整頁進行滾動")
        except:
            panel = driver.find_element(By.TAG_NAME, 'body')
            print("📍 使用頁面主體作為滾動目標")

        time.sleep(1)
        
        # 多次滾動加載評論
        print("\n" + "=" * 60)
        print("📜 開始向下滾動載入評論...")
        print("=" * 60)
        
        for round_num in range(5):  # 最多5輪滾動
            print(f"\n【第 {round_num + 1} 輪滾動】")
            scroll_reviews(driver, panel, pause=3)
            time.sleep(1.5)
        
        print("\n" + "=" * 60)
        print("✓ 滾動完成")
        time.sleep(2)
        driver.save_screenshot("screenshot_2_reviews.png")
        print("✓ 截圖已保存")
        
        print("\n🔎 開始解析評論...")
        # 解析並保存評論
        reviews = parse_reviews(driver)
        save_csv(reviews, output_path)
        return len(reviews)

    except Exception as e:
        print(f"\n發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        print("\n關閉瀏覽器...")
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    # 本地執行時顯示瀏覽器視窗（headless=False）
    # 這樣可以看到滾動過程
    print("啟動爬蟲 (非 Headless 模式 - 會顯示瀏覽器窗口)")
    print("=" * 60)
    count = scrape(headless=False)
    print("=" * 60)
    print(f"✅ 共抓取 {count} 筆評論")
