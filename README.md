# PGY 排班系統部署

此專案採用 GitHub Pages 提供前端、Render 提供排班 API。

## 1. 部署 Python 後端到 Render

1. 將此資料夾推送至 GitHub repository。
2. 在 Render 選擇 **New +** → **Blueprint**，連結該 repository，並建立服務。
   Render 會讀取 `render.yaml`，安裝 Python 套件並以 `uvicorn` 啟動 `app.py`。
3. 等待部署完成，開啟 `https://你的-render-網址/health`；應顯示 `{\"status\":\"ok\"}`。
4. 複製 Render 的服務網址，例如 `https://pgy-scheduler-api.onrender.com`。

## 2. 連接前端與後端

1. 修改 `config.js` 的 `API_BASE_URL` 為上一步取得的 Render 網址（不加結尾 `/`）。
2. 重新推送這個變更到 GitHub。
3. 回到 Render 的環境變數，設定 `ALLOWED_ORIGINS` 為你的 GitHub Pages 網址，例如 `https://你的帳號.github.io`。
   若 repository 網址包含專案名稱，仍只填網域，不填 `/repository-name`。
4. 儲存後讓 Render 重新部署。

## 3. 啟用 GitHub Pages

1. 在 GitHub repository 依序進入 **Settings** → **Pages**。
2. 在 **Build and deployment** 選擇 **Deploy from a branch**。
3. 選擇要發布的分支（通常是 `main`）和資料夾 **/(root)**，然後儲存。
4. GitHub 顯示的網址就是網站入口。根目錄的 `index.html` 會自動開啟排班系統。

## 本機測試

執行 `python app.py` 後，以瀏覽器開啟 HTML 檔。部署前 `config.js` 維持本機網址即可；要發布 GitHub Pages 前，務必改成 Render 網址。
