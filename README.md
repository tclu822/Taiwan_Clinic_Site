# 台灣互動式地圖應用程式

這是一個結合 Leaflet.js 前端和 FastAPI 後端的互動式台灣地圖應用程式，用於視覺化台灣縣市和村里的薪資所得資料。

## 功能特色

- **互動式地圖**: 使用 Leaflet.js 提供流暢的地圖互動體驗
- **縣市視圖**: 顯示台灣各縣市界線，點擊可進入村里視圖
- **村里視圖**: 基於薪資中位數的七等分紅色漸層渲染
- **薪資資料查詢**: 點擊村里可查看該村里 2011-2023 年的薪資資料
- **響應式設計**: 支援桌面和行動裝置

## 專案結構

```
CLINIC SITE PROJECT/
├── backend/
│   └── main.py              # FastAPI 後端主程式
├── frontend/
│   ├── index.html           # 前端 HTML 檔案
│   ├── styles.css           # CSS 樣式檔案
│   └── script.js            # JavaScript 互動邏輯
├── requirements.txt          # Python 依賴套件
├── taiwan_country_border/   # 縣市界地理資料
├── taiwan_village_border/   # 村里界地理資料
├── salary-gh-pages/         # 薪資資料
└── README.md               # 專案說明文件
```

## 環境需求

- Python 3.13.5
- Node.js (用於本地伺服器，可選)

## 安裝步驟

### 1. 安裝 Python 依賴套件

```bash
pip install -r requirements.txt
```

### 2. 啟動後端服務

```bash
cd backend
python main.py
```

後端服務將在 `http://localhost:8000` 啟動。

### 3. 啟動前端服務

您可以使用任何 HTTP 伺服器來提供前端檔案。例如：

使用 Python 內建伺服器：
```bash
cd frontend
python -m http.server 8080
```

或使用 Node.js 的 http-server：
```bash
npm install -g http-server
cd frontend
http-server -p 8080
```

前端應用程式將在 `http://localhost:8080` 啟動。

## API 端點

### 縣市資料
- `GET /api/counties` - 返回全台灣縣市的 GeoJSON 資料

### 村里資料
- `GET /api/villages/{county_name}` - 返回指定縣市的所有村里 GeoJSON 資料

### 薪資資料
- `GET /api/village_salary/{village_name}?county_name={county_name}` - 返回指定村里的薪資資料

### 健康檢查
- `GET /api/health` - 檢查 API 服務狀態

## 使用說明

### 基本操作

1. **縣市視圖**: 地圖載入後會顯示台灣各縣市界線
2. **點擊縣市**: 點擊任何縣市會縮放到該縣市並顯示村里界線
3. **村里視圖**: 村里根據 2023 年薪資中位數進行七等分紅色漸層渲染
4. **點擊村里**: 點擊村里會在右側顯示該村里 2011-2023 年的薪資資料
5. **返回縣市界**: 點擊左上角的「返回縣市界」按鈕可回到縣市視圖

### 互動功能

- **縮放控制**: 地圖縮放等級 6-18
- **自動切換**: 縮放等級 ≥ 10 時自動顯示村里視圖，< 10 時返回縣市視圖
- **資料面板**: 點擊村里後右側會顯示詳細薪資資料表格
- **響應式設計**: 支援不同螢幕尺寸

## 資料來源

- **地理資料**: 台灣縣市界和村里界 GeoJSON 檔案
- **薪資資料**: 2011-2023 年村里綜合所得稅資料 (CSV 格式)

## 技術架構

### 後端 (FastAPI)
- **框架**: FastAPI
- **地理處理**: GeoPandas, Shapely
- **資料處理**: Pandas
- **CORS**: 支援跨域請求

### 前端 (Leaflet.js)
- **地圖引擎**: Leaflet.js
- **基礎圖層**: OpenStreetMap
- **互動功能**: 自定義 JavaScript
- **樣式**: 自定義 CSS

## 效能優化

1. **資料預處理**: 後端啟動時載入所有地理和薪資資料
2. **分層載入**: 縣市和村里資料按需載入
3. **快取機制**: 已載入的資料會暫存在記憶體中
4. **壓縮傳輸**: GeoJSON 資料經過優化處理

## 故障排除

### 常見問題

1. **後端無法啟動**
   - 檢查 Python 版本是否為 3.13.5
   - 確認所有依賴套件已正確安裝
   - 檢查地理資料檔案路徑是否正確

2. **前端無法連接到後端**
   - 確認後端服務在 `http://localhost:8000` 運行
   - 檢查瀏覽器控制台是否有 CORS 錯誤
   - 確認 API 端點是否正常回應

3. **地圖無法載入**
   - 檢查網路連線
   - 確認 OpenStreetMap 服務可正常存取
   - 檢查瀏覽器是否支援 Leaflet.js

### 除錯模式

啟動後端時可以查看詳細的載入日誌：
```bash
python main.py
```

## 開發說明

### 添加新功能

1. **新增 API 端點**: 在 `backend/main.py` 中添加新的路由
2. **修改前端互動**: 在 `frontend/script.js` 中添加新的 JavaScript 函數
3. **更新樣式**: 在 `frontend/styles.css` 中修改 CSS 樣式

### 資料更新

1. **更新地理資料**: 替換對應的 GeoJSON 檔案
2. **更新薪資資料**: 替換 CSV 檔案並重新啟動後端服務

## 授權

本專案僅供學習和研究使用。

## 聯絡資訊

如有問題或建議，請聯繫開發團隊。 