# 公文發佈自動化 - 設定與修改教學

為了讓程式能適應各個學校的網站改版與不同模組，本程式導入了 `config.json` 外部設定檔。
未來若網頁有任何變動，您只需要修改 `config.json`，**不需要重新編譯或修改 Python 程式碼**！

## 1. 基礎設定說明

請用「記事本」或任何文字編輯器打開 `config.json`：

```json
{
  "school_url": "https://www.hsps.tp.edu.tw",
  "allowed_extensions": [".odt", ".ods", ".odp", ".pdf", ".jpg", ".png"],
  "categories": [
    "宣導與公告",
    "榮譽榜",
    "競賽與活動資訊",
    "研習進修"
  ],
  ...
}
```

* **`school_url`**: 貴校的首頁網址。
* **`allowed_extensions`**: 系統允許上傳的附檔名。只有在此清單內的檔案兩會被上傳，其餘（例如 .pde）將自動跳過。
* **`categories`**: 貴校網頁上用來發布公告的「區塊名稱」。程式會根據這裡的文字，自動產生讓您選擇的按鈕，也會用這個文字去尋找網頁上的對應區塊。如果學校只有三個區塊，就把多餘的刪除即可。

---

## 2. 進階：如何尋找與修改 XPath (定位器)

如果網頁大改版，導致程式跳出「找不到元素」的錯誤，您可以照著以下步驟自己修復 `config.json` 裡的 `xpath_templates`。

### 步驟一：打開瀏覽器的開發者工具
1. 使用 Google Chrome 進入貴校的網站並登入。
2. 在網頁空白處按下滑鼠「右鍵」，選擇「**檢查 (Inspect)**」，或者直接按鍵盤的 `F12`。
3. 畫面上會跳出一個充滿程式碼的面板（Elements）。

### 步驟二：尋找元素的特徵
1. 點擊開發者工具左上角的「小箭頭圖示 (Select an element in the page to inspect it)」。
2. 將滑鼠移動到您想讓程式點擊的按鈕（例如「新增公告」或「發布」），點擊左鍵。
3. 此時面板中會亮起一段 HTML 程式碼，例如：
   `<button class="btn-publish" type="button">發布</button>`

### 步驟三：改寫 XPath
在 `config.json` 中的 `xpath_templates` 使用的是「相對路徑」。這就像是在告訴程式「請幫我找一個內容有寫著『發布』的按鈕」，而不是告訴它「請去第1個資料夾的第5個抽屜找」。

常見的相對路徑寫法：
* **依賴文字 (最常用)**：`//button[contains(text(), '發布')]`
* **依賴提示詞 (Placeholder)**：`//input[@placeholder='請輸入標題']`
* **依賴特殊標籤 (aria-label)**：`//button[@aria-label='附件']`

> **重點提醒**：
> 關於「新增公告」按鈕，因為網頁上同時有好幾個「新增公告」，為了不點錯區塊，我們在 JSON 中使用了 `{category}` 當作變數：
> `"//div[contains(., '{category}')]//button[contains(text(), '新增公告')]"`
> 程式執行時，會自動把 `{category}` 替換成您選擇的區塊（例如「榮譽榜」），這樣它就會先找「榮譽榜的區塊」，再點選裡面的按鈕。如果您需要修改這行，請務必保留 `{category}` 這個字眼！
