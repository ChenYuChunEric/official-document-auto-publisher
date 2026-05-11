# 公文自動命名與發佈工具 (Official Document Auto-Publisher)

這是一個專為學校及機關設計的自動化工具，旨在簡化「公文處理」與「網站公告發佈」的流程。透過本工具，您可以自動從公文壓縮檔中擷取資訊、重命名檔案，並自動將內容發佈至校園網站。

## 🌟 主要功能

- **自動解壓與識別**：自動解壓公文 ZIP 檔，並識別其中的正文 PDF 與附件。
- **AI 資訊擷取**：利用 PyMuPDF 技術，自動從 PDF 正文中精準擷取「主旨」與「說明」內容。
- **智慧命名系統**：根據公文主旨自動重新命名資料夾與檔案，並支援「西元年」或「民國年」日期前綴。
- **雙軌穩健自動化 (v1.1.0 新功能)**：整合 Selenium `ActionChains` 與底層 `JavaScript` 事件驅動，**首創雙軌輸入機制**。確保在視窗正常狀態下使用模擬輸入，而在視窗縮小時自動切換為強制事件觸發，徹底解決發佈中斷或內容空白的問題。
- **智慧容器定位**：採用動態鎖定機制，能精準識別網站中不同分類的公告區塊，具備強大的跨網站適應能力。
- **自動化網頁發佈**：支援登入臺北市單一身分驗證 (SSO)，並自動將公文內容、附件填寫至網站公告系統。
- **靈活配置**：透過 `config.json` 即可自定義學校網址、公告分類及網頁元素定位 (XPath)。

## 🛠️ 系統需求

- Windows 作業系統
- Python 3.8 或以上版本
- Google Chrome 瀏覽器 (用於網頁自動化)

## 🚀 快速開始

### 1. 取得專案
```bash
git clone https://github.com/ChenYuChunEric/official-document-auto-publisher.git
cd official-document-auto-publisher
```

### 2. 環境設定
建議使用虛擬環境以確保依賴項獨立：
```powershell
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows)
.\venv\Scripts\activate

# 安裝所需套件
pip install -r requirements.txt
```

### 3. 執行程式
```powershell
python "公文改名稱及發佈.py"
```

## ⚙️ 配置說明 (`config.json`)

程式首次執行時會自動生成預設的 `config.json`，您可以根據需求修改：

- `school_url`: 您的學校/單位網站首頁網址。
- `categories`: 公告系統中的分類名稱 (例如：宣導與公告、榮譽榜)。
- `allowed_extensions`: 允許上傳的附件副檔名清單。
- `xpath_templates`: 針對不同網站架構的網頁元素定位設定。

## 📦 打包為執行檔 (.exe)

如果您希望在沒有 Python 環境的電腦上使用，可以使用 `PyInstaller` 進行打包：
```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=icon.ico "公文改名稱及發佈.py"
```

## 📝 版本更新紀錄

### v1.1.0 (2026-05-11)
- **新增**：雙軌自動化發佈機制（ActionChains + JS Fallback）。
- **優化**：大幅提升視窗縮小時的執行穩定性。
- **修正**：優化程式碼結構，提升維護性。
- **改進**：更新 README 文檔，新增功能詳解與使用須知。

### v1.0.1
- 正式版發佈：支援自動命名與網頁公告發佈。

## 🤝 貢獻與反饋

如果您在使用過程中遇到任何問題，或有功能上的建議，歡迎透過 GitHub 提交 [Issue](https://github.com/ChenYuChunEric/official-document-auto-publisher/issues) 或 Pull Request。

---
**作者**: Eric Chen (EricChenYuChun)  
**專案連結**: [GitHub Repository](https://github.com/ChenYuChunEric/official-document-auto-publisher)
