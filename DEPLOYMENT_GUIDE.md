# 台灣互動式地圖應用程式 - 部署指南

本指南將引導您將這個台灣互動式地圖應用程式部署到生產環境。

## 📋 部署總覽

這個應用程式包含：
- **前端**: 使用Leaflet.js的地圖介面，部署到GitHub Pages
- **後端**: FastAPI應用程式，提供地理資料API，部署到Railway

## 🚀 部署步驟

### 步驟1: 在GitHub上創建Repository

1. 前往 [GitHub](https://github.com) 並登入您的帳號
2. 點擊右上角的 "+" 按鈕，選擇 "New repository"
3. 設定Repository資訊：
   - **Repository name**: `taiwan-interactive-map` (或您喜歡的名稱)
   - **Description**: 台灣互動式地圖應用程式 - 薪資所得視覺化
   - **Visibility**: Public (GitHub Pages需要公開repository)
4. **不要**勾選 "Add a README file" 或其他選項
5. 點擊 "Create repository"

### 步驟2: 上傳程式碼到GitHub

開啟命令提示字元或PowerShell，執行以下命令：

```bash
# 添加遠端repository (請將 YOUR_USERNAME 替換為您的GitHub用戶名)
git remote add origin https://github.com/YOUR_USERNAME/taiwan-interactive-map.git

# 推送程式碼到GitHub
git branch -M main
git push -u origin main
```

### 步驟3: 啟用GitHub Pages

1. 在您的GitHub repository頁面，點擊 "Settings" 標籤
2. 在左側選單中找到 "Pages"
3. 在 "Source" 下拉選單中選擇 "GitHub Actions"
4. 保存設定

### 步驟4: 部署後端到Railway

1. 前往 [Railway](https://railway.app) 並登入（支援GitHub登入）
2. 點擊 "New Project"
3. 選擇 "Deploy from GitHub repo"
4. 授權Railway存取您的GitHub帳號
5. 找到並選擇您的 `taiwan-interactive-map` repository
6. Railway會自動檢測到這是Python專案並開始部署

部署完成後，Railway會提供一個URL，例如：`https://your-project-name.up.railway.app`

### 步驟5: 更新前端配置

1. 在GitHub上編輯 `frontend/script.js` 檔案
2. 找到第25-27行的API配置：
   ```javascript
   const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
       ? 'http://localhost:8000'
       : 'https://your-backend-url.vercel.app'; // 將在部署時替換為實際的後端URL
   ```
3. 將 `'https://your-backend-url.vercel.app'` 替換為您的Railway後端URL
4. 提交變更

### 步驟6: 等待自動部署

一旦您推送了前端配置的變更：
1. GitHub Actions會自動開始部署前端到GitHub Pages
2. 您可以在repository的 "Actions" 標籤中查看部署進度
3. 部署成功後，您的應用程式將可以在 `https://YOUR_USERNAME.github.io/taiwan-interactive-map/` 存取

## 🔧 疑難排解

### 後端部署問題

如果Railway部署失敗，請檢查：
1. 確保 `requirements.txt` 中的所有依賴都正確
2. 檢查Railway的部署日誌以獲取詳細錯誤資訊
3. 確保所有資料檔案都存在且路徑正確

### 前端部署問題

如果GitHub Pages部署失敗：
1. 檢查GitHub Actions工作流程是否有錯誤
2. 確保前端檔案路徑正確
3. 檢查瀏覽器控制台是否有CORS錯誤

### API連線問題

如果前端無法連接到後端：
1. 確保Railway後端正在運行
2. 檢查CORS設定是否正確
3. 驗證前端的API_BASE_URL配置是否正確

## 📊 監控和維護

### 健康檢查
您可以通過以下端點檢查服務狀態：
- 後端健康檢查: `https://your-railway-url.up.railway.app/api/health`
- 前端應用程式: `https://YOUR_USERNAME.github.io/taiwan-interactive-map/`

### 更新應用程式
要更新應用程式：
1. 在本地進行變更
2. 提交並推送變更到GitHub
3. Railway會自動重新部署後端
4. GitHub Actions會自動重新部署前端

## 💰 成本估計

- **GitHub Pages**: 完全免費
- **Railway**: 免費額度通常足夠小型應用程式使用
- **總成本**: 基本上免費，除非您的應用程式有大量流量

## 🎯 下一步

部署完成後，您的應用程式將可以：
- 在任何裝置上存取
- 提供穩定的服務
- 自動處理流量波動
- 輕鬆進行更新和維護

恭喜！您的台灣互動式地圖應用程式現在已經成功上線了！🎉
