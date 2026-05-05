import os
import sys
import json
import fitz  # PyMuPDF，用於處理 PDF
import zipfile
import re
import shutil
import datetime
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import traceback
import threading
import requests
import webbrowser

VERSION = "1.0.1"
GITHUB_REPO = "ChenYuChunEric/official-document-auto-publisher"

# ================================================
# 1. 讀取外部設定檔 config.json
# ================================================
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ 找不到設定檔：{CONFIG_FILE}，正在自動生成預設設定檔...")
        default_config = {
            "school_url": "https://www.hsps.tp.edu.tw",
            "categories": ["宣導與公告", "榮譽榜", "競賽與活動資訊", "研習進修"],
            "allowed_extensions": [".pdf", ".jpg", ".png", ".doc", ".docx", ".xls", ".xlsx"],
            "xpath_templates": {
                "category_tab": "//a[contains(text(), '{category}')]",
                "announcement_button": "(//*[contains(text(), '{category}')]/following::button[contains(text(), '新增公告')])[1]",
                "subject_title": "(//*[contains(text(), '{category}')]/following::input[@placeholder='輸入標題' or contains(@class, 'title')])[1]",
                "attachment_button": "(//*[contains(text(), '{category}')]/following::button[contains(text(), '附件') or @aria-label='附件'])[1]",
                "new_file_button": "(//*[contains(text(), '{category}')]/following::li[contains(text(), '新增檔案')])[1]",
                "upload_field": "(//*[contains(text(), '{category}')]/following::input[@type='file'])[{index}]",
                "content_announcement": "(//*[contains(text(), '{category}')]/following::div[contains(@class, 'editor-content') or @contenteditable='true'])[1]",
                "publish_button": "(//*[contains(text(), '{category}')]/following::button[contains(text(), '發布')])[1]"
            }
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            print(f"✅ 已成功生成 {CONFIG_FILE} 預設設定！")
        except Exception as e:
            print(f"❌ 建立 {CONFIG_FILE} 失敗：{e}")
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 讀取 {CONFIG_FILE} 失敗：{e}")
        sys.exit()

config = load_config()
school_url = config.get("school_url", "https://www.hsps.tp.edu.tw")
categories = config.get("categories", [])
allowed_extensions = [ext.lower() for ext in config.get("allowed_extensions", [])]
xpath_templates = config.get("xpath_templates", {})

if not categories:
    print("⚠️ config.json 中沒有設定 categories，請檢查設定檔！")
    sys.exit()

# ================================================
# 2. 其他輔助函式
# ================================================

def check_for_updates():
    if not GITHUB_REPO:
        return

    print(f"[INFO] 正在檢查 {GITHUB_REPO} 是否有新版本...")
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        r = requests.get(api_url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            latest_version = data.get("tag_name", "").lstrip("v")
            current_version = VERSION.lstrip("v")
            
            if latest_version and latest_version != current_version:
                print(f"[INFO] 發現新版本: v{latest_version} (目前版本: v{current_version})")
                release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
                
                def show_popup():
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    result = messagebox.askyesno("更新通知", f"發現新版本 v{latest_version} (目前: v{current_version})\n\n是否前往下載？")
                    if result:
                        webbrowser.open(release_url)
                    root.destroy()
                
                threading.Thread(target=show_popup, daemon=True).start()
            else:
                print(f"[INFO] 目前已是最新版本 (v{current_version})。")
        else:
            print("[DEBUG] 無法取得最新版本資訊，可能尚未發布 Release。")
    except Exception as e:
        print(f"[WARN] 檢查更新時發生網路或 API 錯誤: {e}")

def confirm_login():
    """彈出視窗讓使用者確認已於網頁輸入帳密"""
    root = tk.Tk()
    root.title("請自行於網頁上輸入帳密")
    root.geometry("300x100")
    tk.Label(root, text="請按下『確認登入』以繼續").pack(pady=10)
    tk.Button(root, text="確認登入", command=lambda: (root.destroy(), root.quit())).pack(pady=10)
    root.mainloop()

def clean_extracted_text(text):
    """移除雜項資訊並合併連續換行"""
    unwanted_patterns = [
        r"檔\s*號[:：].*?",
        r"保存年限[:：]\s*\d+\s*",
        r"\*\w+\*",
        r"第\s*\d+\s*頁，共\s*\d+\s*頁",
        r"[.\s]+$",
        r"裝[\s.]*訂[\s.]*線[\s.]*",
        r"\b\S+國小\s+\d{4,}\b",
    ]
    for pattern in unwanted_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def get_pdf_title_and_content(pdf_path):
    """從 PDF 擷取主旨與內文"""
    doc = fitz.open(pdf_path)
    text = " ".join(page.get_text("text") for page in doc)
    
    title_match = re.search(r"主旨：(.*?)說明：", text, re.DOTALL)
    content_match = re.search(r"主旨：(.*?)正本：", text, re.DOTALL)
    title = title_match.group(1).strip().replace("\n", "").replace("\r", "").replace("/", "-") if title_match else "未識別標題"
    content = f"主旨：{content_match.group(1).strip()}" if content_match else "⚠️ 未找到完整公告內容"
    content = clean_extracted_text(content)
    print(f"\n🚀【擷取公告主旨】\n{title}\n")
    print(f"📍【擷取公告內文】\n{content}\n")
    return title, content

def get_document_number(filename):
    """從檔名中提取流水編號"""
    match = re.match(r"(\d+)_\d+", filename)
    return match.group(1) if match else None

def get_minguo_date():
    """跳出一個視窗讓使用者選擇想要增加的日期格式"""
    today = datetime.date.today()
    result = None

    def on_western():
        nonlocal result
        result = f"{today.year:04d}{today.month:02d}{today.day:02d}"
        root.destroy()

    def on_minguo():
        nonlocal result
        minguo_year = today.year - 1911
        result = f"{minguo_year:03d}{today.month:02d}{today.day:02d}"
        root.destroy()

    def on_none():
        nonlocal result
        result = ""
        root.destroy()

    root = tk.Tk()
    root.title("日期格式選擇")
    label = tk.Label(root, text="請選擇想要增加的日期格式", font=("Arial", 12))
    label.pack(padx=20, pady=10)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    btn_western = tk.Button(button_frame, text="西元年", command=on_western, width=10)
    btn_western.grid(row=0, column=0, padx=5)

    btn_minguo = tk.Button(button_frame, text="民國年", command=on_minguo, width=10)
    btn_minguo.grid(row=0, column=1, padx=5)

    btn_none = tk.Button(button_frame, text="不增加", command=on_none, width=10)
    btn_none.grid(row=0, column=2, padx=5)

    root.mainloop()
    return result

# ================================================
# 3. 處理來文並建立公文資料夾
# ================================================
def process_documents():
    processed_cases = []
    
    root = tk.Tk()
    root.withdraw()
    extracted_folder = filedialog.askdirectory(title="選擇『野生的來文資料』資料夾")
    output_folder = filedialog.askdirectory(title="選擇『可以被看懂的來文資料』資料夾")
    root.destroy()
    
    if not extracted_folder or not output_folder:
        print("❌ 未選擇資料夾，程式結束")
        sys.exit()
    
    date_prefix = get_minguo_date()
    
    for file_name in os.listdir(extracted_folder):
        if file_name.endswith(".zip"):
            zip_path = os.path.join(extracted_folder, file_name)
            folder_name = os.path.splitext(file_name)[0]
            target_folder = os.path.join(extracted_folder, folder_name)
            os.makedirs(target_folder, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r', metadata_encoding='big5') as zf:
                zf.extractall(target_folder)
    print("✅ 所有ZIP檔案解壓完成！")
    
    for case_folder in os.listdir(extracted_folder):
        if case_folder.lower().endswith(".zip"):
            continue
        case_path = os.path.join(extracted_folder, case_folder)
        doc_folder = os.path.join(case_path, "來文")
        if not os.path.exists(doc_folder):
            print(f"⚠️ 找不到『來文』資料夾，跳過：{case_folder}")
            continue
        title, document_number = "未知來文", None
        first_pdf_found = False
        for doc_file in os.listdir(doc_folder):
            if (doc_file.lower().endswith(".pdf") and "_ATTCH" not in doc_file and
                "(opinion)" not in doc_file and "合併版" not in doc_file):
                document_number = get_document_number(doc_file)
                if document_number:
                    doc_path = os.path.join(doc_folder, doc_file)
                    title, content = get_pdf_title_and_content(doc_path)
                    first_pdf_found = True
                    break
        if not first_pdf_found:
            print(f"⚠️ 未找到正文PDF，跳過：{case_folder}")
            continue
            
        target_folder = os.path.join(output_folder, f"{date_prefix} {title}".strip())
        os.makedirs(target_folder, exist_ok=True)
        new_name = os.path.join(target_folder, f"{title}.pdf")
        
        try:
            shutil.copy(doc_path, new_name)
            processed_cases.append({
                "folder": f"{date_prefix} {title}".strip(),
                "folder_path": target_folder,
                "title": title,
                "content": content,
                "path": new_name,
                "attachments": []
            })
        except Exception as e:
            print(f"⚠️ 重新命名失敗：{doc_path} -> {new_name}，錯誤：{e}")
            
        # 處理附件（白名單過濾機制）
        for doc_file in os.listdir(doc_folder):
            if f"{document_number}" in doc_file and "_ATTCH" in doc_file:
                doc_path = os.path.join(doc_folder, doc_file)
                attachment_number = re.search(r"_ATTCH(\d+)", doc_file).group(1)
                
                # 取得副檔名並轉小寫，例如 '.jpg'
                ext = "." + doc_file.split(".")[-1].lower()
                
                # 如果不在白名單內，則直接跳過不複製
                if ext not in allowed_extensions:
                    print(f"⏭️ 忽略不支援的附件: {doc_file} (不包含在允許清單中)")
                    continue
                
                new_name = os.path.join(target_folder, f"{title}_附件_{attachment_number}{ext}")
                if not os.path.exists(doc_path):
                    print(f"❌ 附件檔案不存在：{doc_path}")
                    continue
                try:
                    shutil.copy(doc_path, new_name)
                    processed_cases[-1]["attachments"].append(new_name)
                except Exception as e:
                    print(f"⚠️ 附件重新命名失敗：{doc_path} -> {new_name}，錯誤：{e}")
    
    print("所有來文處理完成！✅")
    return processed_cases

# ================================================
# 4. 動態生成 GUI 讓使用者選擇公告區塊
# ================================================
def select_announcement_section(processed_cases):
    def set_section(case, section):
        if section == "跳過":
            print(f"⏭️ 公文 '{case['title']}' 已跳過發布")
        else:
            case["section"] = section
            print(f"✅ 公文 '{case['title']}' 已分類為【{section}】")
            stored_cases.append(case)
        next_case()
    
    def next_case():
        if processed_cases:
            case = processed_cases.pop(0)
            label.config(text=f"{case['title']}")
            for btn in buttons:
                btn.config(command=lambda s=btn.cget("text"): set_section(case, s))
        else:
            label.config(text="所有公文皆已分類完畢！")
            for btn in buttons:
                btn.config(state=tk.DISABLED)
            root_selection.destroy()
            root_selection.quit()
    
    stored_cases = []
    root_selection = tk.Tk()
    root_selection.title("公告區塊選擇 (自 config.json 載入)")
    label = tk.Label(root_selection, text="載入公文...", font=("PMingLiU", 10))
    label.pack(pady=10)
    
    button_frame = tk.Frame(root_selection)
    button_frame.pack()
    buttons = []
    
    # 從 config.json 的 categories 動態生成按鈕
    for sec in categories:
        btn = tk.Button(button_frame, text=sec, font=("PMingLiU", 10), width=12)
        btn.pack(side=tk.LEFT, padx=5, pady=5)
        buttons.append(btn)
        
    btn_skip = tk.Button(button_frame, text="跳過", font=("PMingLiU", 10), width=12, bg="lightgray")
    btn_skip.pack(side=tk.LEFT, padx=5, pady=5)
    buttons.append(btn_skip)
    
    next_case()
    root_selection.mainloop()
    return stored_cases

# ================================================
# 5. 網頁登入
# ================================================
def test_web_login():
    global driver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("detach", True)
    # 隱藏無關的系統日誌 (DEPRECATED_ENDPOINT 等)
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(school_url)
    try:
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '登入')]"))
        )
        driver.execute_script("arguments[0].click();", login_button)
        print("✅ 已成功點選『登入』按鈕")
        time.sleep(3)
        verification_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, '臺北市單一身分驗證')]"))
        )
        driver.execute_script("arguments[0].click();", verification_button)
        print("✅ 已成功點選『臺北市單一身分驗證』按鈕")
        time.sleep(3)
        confirm_login()
    except Exception as e:
        print(f"⚠️ 測試失敗，錯誤：{e}")

# ================================================
# 6. 發布公告流程 (智慧容器通用版)
# ================================================
def publish_announcements(cases):
    total = len(cases)
    print(f"\n📢 準備發布 {total} 篇公告...")

    for idx, case in enumerate(cases, 1):
        section = case["section"]
        title = case["title"]
        content = case["content"]
        folder_path = case.get("folder_path", "")
        
        print(f"\n🚀 [{idx}/{total}] 正在處理分類：【{section}】")
        print(f"   主旨：{title}")

        try:
            # --- 0. 關鍵修正：確保回到管理首頁 ---
            # 避免上一篇發布後停留在跳轉頁面，導致這一篇找不到區塊
            driver.get(school_url)
            time.sleep(3) 

            # --- 1. 智慧鎖定該分類的「容器區塊」 ---
            print(f"   🔍 正在定位區塊...")
            section_container = None
            
            # 找尋分類標題：排除公告列表內的連結
            xpath_anchor = f"//*[(self::h1 or self::h2 or self::h3 or self::h4 or self::span or self::div) and not(ancestor::a) and not(ancestor::table) and not(ancestor::li) and (text()='{section}' or .='{section}')]"
            anchors = [el for el in driver.find_elements(By.XPATH, xpath_anchor) if el.is_displayed()]
            
            if not anchors:
                xpath_anchor_fallback = f"//*[(self::h1 or self::h2 or self::h3 or self::h4) and contains(., '{section}')]"
                anchors = [el for el in driver.find_elements(By.XPATH, xpath_anchor_fallback) if el.is_displayed()]

            for anchor in anchors:
                curr = anchor
                for _ in range(6):
                    try:
                        curr = curr.find_element(By.XPATH, "..")
                        if curr.find_elements(By.XPATH, ".//button[contains(text(), '新增公告')]"):
                            section_container = curr
                            break
                    except:
                        break
                if section_container: break

            if not section_container:
                print(f"   ❌ 找不到 [{section}] 容器，跳過此篇。")
                continue

            # --- 2. 執行發布動作 (參考 14.py 穩定流程) ---
            ann_btn = section_container.find_element(By.XPATH, ".//button[contains(text(), '新增公告')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", ann_btn)
            time.sleep(1)
            ann_btn.click()
            time.sleep(3)
            
            # 標題
            subj_field = WebDriverWait(driver, 10).until(
                lambda d: section_container.find_element(By.XPATH, ".//input[not(@type='button' or @type='submit' or @type='checkbox')]")
            )
            subj_field.click()
            subj_field.clear()
            subj_field.send_keys(title)
            
            # 附件
            if folder_path and os.path.isdir(folder_path):
                files = sorted([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
                if files:
                    for i, fname in enumerate(files):
                        attach_btn = section_container.find_element(By.XPATH, ".//button[contains(., '附件') or contains(@class, 'attach')]")
                        attach_btn.click()
                        time.sleep(1)
                        newfile_btn = section_container.find_element(By.XPATH, ".//li[contains(., '新增檔案')]")
                        newfile_btn.click()
                        time.sleep(1)
                        file_path = os.path.abspath(os.path.join(folder_path, fname))
                        inputs = section_container.find_elements(By.XPATH, ".//input[@type='file']")
                        if len(inputs) > i:
                            inputs[i].send_keys(file_path)
                            print(f"   📎 附件已上傳: {fname}")
                        time.sleep(1)
            
            # 內文 (ActionChains)
            content_field = section_container.find_element(By.XPATH, ".//div[@contenteditable='true' or contains(@class, 'editor')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", content_field)
            time.sleep(0.5)
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).move_to_element(content_field).click().send_keys(content).perform()
            time.sleep(1)
            
            # 發布
            publish_btn = section_container.find_element(By.XPATH, ".//button[contains(., '發') and contains(., '布')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", publish_btn)
            time.sleep(1)
            try: publish_btn.click()
            except: driver.execute_script("arguments[0].click();", publish_btn)
            
            print(f"   ✅ [{section}] 發布指令成功！")
            time.sleep(5) # 確保發布流程跑完

        except Exception as e:
            print(f"   ⚠️ [{section}] 發布中斷！原因: {e}")
            traceback.print_exc()
            time.sleep(2) # 錯誤後緩衝，準備下一篇

# ================================================
# 主程式
# ================================================
def main():
    print(f"🚀 程式啟動 (版本: v{VERSION})")
    check_for_updates()
    
    processed_cases = process_documents()
    selected_cases = select_announcement_section(processed_cases)
    if selected_cases:
        test_web_login()
        publish_announcements(selected_cases)
    else:
        print("無需發布公告的公文。")
    
    print("所有操作完成！✅")
    input("請按 Enter 鍵以結束...")
    sys.exit()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] 程式發生未預期的嚴重錯誤: {e}")
        traceback.print_exc()
        input("\n按 Enter 鍵結束程式...")
        sys.exit(1)
