// 全域變數
let map;
let countyLayer;
let villageLayer;
let currentCounty = null;
let isVillageMode = false;
let selectedCountyLayer = null; // 儲存選中縣市的圖層
let villageMarkers = []; // 儲存村里標籤
let countyMarkers = []; // 儲存縣市標籤
let currentVillageData = null; // 儲存當前村里資料
let isBivariateMode = false; // 是否為雙變數模式

// 診所地標相關變數
let clinicMarkers = []; // 儲存診所標記
let clinicSpecialties = []; // 儲存診所科別資料
let selectedSpecialties = new Set(); // 儲存選中的科別

// 權重控制
let currentWeights = {
    income: 0.5,
    density: 0.5
};

// API 基礎 URL
const API_BASE_URL = 'http://localhost:8000';

// 工具函數：將hex顏色轉換為rgba格式
function hexToRgba(hex, alpha) {
    // 移除 # 符號
    hex = hex.replace('#', '');
    
    // 解析hex顏色
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// 薪資中位數漸層顏色（紅色系）
const INCOME_COLORS = [
    '#fee5d9', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d', '#4d0000'
];

// 人口密度漸層顏色（藍色系）  
const DENSITY_COLORS = [
    '#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'
];

// 初始化地圖
function initMap() {
    console.log('初始化地圖...');
    
    // 創建地圖實例，使用更精確的縮放設定
    map = L.map('map', {
        center: [23.8, 120.9], // 調整台灣本島中心位置
        zoom: 8, 
        minZoom: 6,
        maxZoom: 18,
        zoomControl: false,
        attributionControl: true
    });

    // 添加 OpenStreetMap 基礎圖層
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // 載入縣市資料
    loadCountyData();
    
    // 載入診所科別資料
    loadClinicSpecialties();
    


    // 監聽地圖縮放事件
    map.on('zoomend', function() {
        console.log('縮放事件觸發，當前縮放等級:', map.getZoom());
        handleZoomChange();
        
        // 更新村里界線粗細
        updateVillageLayerStyle();
    });
    
    // 監聽地圖點擊事件（關閉資料面板）
    map.on('click', function(e) {
        console.log('地圖點擊事件觸發');
        if (e.originalEvent && e.originalEvent.target === map._container) {
            closeDataPanel();
        }
    });
}

// 載入縣市資料
async function loadCountyData() {
    try {
        showLoading();
        console.log('開始載入縣市資料...');
        
        const response = await fetch(`${API_BASE_URL}/api/counties`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const countyData = await response.json();
        console.log('縣市資料載入成功，縣市數量:', countyData.features.length);
        
        // 創建縣市圖層
        countyLayer = L.geoJSON(countyData, {
            style: {
                fillColor: '#008000',
                weight: 2,
                opacity: 1,
                color: '#000000',
                fillOpacity: 0.7
            },
            onEachFeature: function(feature, layer) {
                console.log('添加縣市圖層:', feature.properties.name);
                
                // 添加點擊事件
                layer.on('click', function(e) {
                    console.log('縣市點擊事件觸發:', feature.properties.name);
                    e.originalEvent.stopPropagation(); // 防止事件冒泡
                    handleCountyClick(feature.properties.name);
                });
                
                // 只使用後端提供的準確座標
                let markerLat, markerLng;
                
                if (feature.properties.center_lat && feature.properties.center_lon) {
                    // 直接使用後端提供的正確座標
                    markerLat = parseFloat(feature.properties.center_lat);
                    markerLng = parseFloat(feature.properties.center_lon);
                    console.log(`${feature.properties.name} 使用後端座標: lat=${markerLat}, lng=${markerLng}`);
                } else {
                    console.error(`${feature.properties.name} 缺少後端座標資料`);
                    return; // 跳過沒有座標資料的標籤
                }
                
                const label = L.divIcon({
                    className: 'county-label',
                    html: feature.properties.name,
                    iconSize: [100, 20],
                    iconAnchor: [50, 10]
                });
                
                const marker = L.marker([markerLat, markerLng], {
                    icon: label
                }).addTo(map);
                countyMarkers.push(marker);
            }
        });
        
        countyLayer.addTo(map);
        console.log('縣市圖層已添加到地圖');
        
        // 確保地圖顯示台灣本島區域（排除離島）
        const taiwanBounds = L.latLngBounds(
            [22.0, 120.0], // 台灣本島西南角
            [25.0, 122.0]  // 台灣本島東北角
        );
        console.log('台灣本島邊界:', taiwanBounds);
        // 暫時移除自動 fitBounds，測試是否影響座標精度
        // map.fitBounds(taiwanBounds, { padding: [20, 20] });
        
        hideLoading();
        
    } catch (error) {
        console.error('載入縣市資料失敗:', error);
        hideLoading();
        alert('載入縣市資料失敗，請檢查後端服務是否正常運行。');
    }
}

// 處理縣市點擊事件
async function handleCountyClick(countyName) {
    console.log('處理縣市點擊:', countyName);
    try {
        showLoading();
        
        // 獲取縣市中心座標（最大區塊中心，不是幾何中心）
        let countyCenterLat = null;
        let countyCenterLng = null;
        
        if (countyLayer) {
            countyLayer.eachLayer(function(layer) {
                if (layer.feature && layer.feature.properties.name === countyName) {
                    if (layer.feature.properties.center_lat && layer.feature.properties.center_lon) {
                        countyCenterLat = parseFloat(layer.feature.properties.center_lat);
                        countyCenterLng = parseFloat(layer.feature.properties.center_lon);
                        console.log(`找到 ${countyName} 的中心座標: lat=${countyCenterLat}, lng=${countyCenterLng}`);
                    }
                }
            });
        }
        
        // 如果已經在村里模式下，先清除現有的村里圖層
        if (villageLayer) {
            map.removeLayer(villageLayer);
            villageLayer = null;
        }
        // 清除現有的村里標籤
        clearVillageMarkers();
        
        // 重置診所勾選狀態
        resetClinicSelections();
        
        // 載入該縣市的村里資料（包含權重參數）
        const response = await fetch(`${API_BASE_URL}/api/villages/${encodeURIComponent(countyName)}?income_weight=${currentWeights.income}&density_weight=${currentWeights.density}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const villageData = await response.json();
        console.log('村里資料載入成功，村里數量:', villageData.features.length);
        
        // 儲存當前村里資料
        currentVillageData = villageData;
        
        // 隱藏縣市標籤但保留縣市圖層
        clearCountyMarkers();
        
        // 先恢復之前隱藏的縣市色塊（如果有的話）
        showSelectedCountyLayer();
        
        // 隱藏新選中的縣市色塊
        hideSelectedCountyLayer(countyName);
        
        // 創建村里圖層
        villageLayer = L.geoJSON(villageData, {
            style: function(feature) {
                const zoomLevel = map.getZoom();
                // 根據縮放等級調整線條粗細
                let weight = 1;
                if (zoomLevel >= 15) weight = 2;
                if (zoomLevel >= 17) weight = 3;
                
                // 使用雙變數顏色或單變數顏色
                let fillColor = '#fee5d9'; // 預設顏色
                
                if (feature.properties.bivariate_color) {
                    // 使用後端計算的雙變數顏色，並加上透明度
                    fillColor = hexToRgba(feature.properties.bivariate_color, 0.75);
                } else {
                    // 使用原本的薪資顏色
                    const incomeLevel = feature.properties.income_level || 0;
                    fillColor = INCOME_COLORS[incomeLevel] || '#fee5d9';
                }
                
                return {
                    fillColor: fillColor,
                    weight: weight,
                    opacity: 1,
                    color: '#000000',
                    fillOpacity: 0.9
                };
            },
            onEachFeature: function(feature, layer) {
                console.log('添加村里圖層:', feature.properties.name);
                
                // 添加點擊事件
                layer.on('click', function(e) {
                    console.log('=== 村里點擊事件觸發 ===');
                    console.log('村里名稱:', feature.properties.name);
                    console.log('縣市名稱:', feature.properties.county);
                    console.log('區域名稱:', feature.properties.district);
                    console.log('完整屬性:', feature.properties);
                    e.originalEvent.stopPropagation(); // 防止事件冒泡
                    
                    // 確認參數不為空
                    if (!feature.properties.name || !feature.properties.county || !feature.properties.district) {
                        console.error('缺少必要參數！');
                        alert('缺少村里資料，無法載入薪資資訊');
                        return;
                    }
                    
                    console.log('準備呼叫 handleVillageClick...');
                    handleVillageClick(feature.properties.name, feature.properties.county, feature.properties.district);
                });
                
                // 只使用後端提供的準確座標
                let markerLat, markerLng;
                
                // 直接使用後端提供的正確座標
                if (feature.properties.center_lat && feature.properties.center_lon) {
                    markerLat = parseFloat(feature.properties.center_lat);
                    markerLng = parseFloat(feature.properties.center_lon);
                    console.log(`${feature.properties.name} 使用後端座標: lat=${markerLat}, lng=${markerLng}`);
                } else {
                    console.error(`${feature.properties.name} 缺少後端座標資料`);
                    return; // 跳過沒有座標資料的標籤
                }
                
                const label = L.divIcon({
                    className: 'village-label',
                    html: feature.properties.name,
                    iconSize: [80, 16],
                    iconAnchor: [40, 8]
                });
                
                const marker = L.marker([markerLat, markerLng], {
                    icon: label
                }).addTo(map);
                villageMarkers.push(marker);
            }
        });
        
        villageLayer.addTo(map);
        
        // 使用縣市中心座標設定視野，而不是幾何中心
        if (countyCenterLat && countyCenterLng) {
            // 使用縣市的最大區塊中心（標籤位置）作為視野中心
            console.log(`使用 ${countyName} 的中心座標設定視野: lat=${countyCenterLat}, lng=${countyCenterLng}`);
            map.setView([countyCenterLat, countyCenterLng], 11, {
                animate: true,
                duration: 0.8
            });
        } else {
            // 備用方案：如果沒有中心座標，使用原來的fitBounds方法
            console.warn(`無法找到 ${countyName} 的中心座標，使用fitBounds作為備用方案`);
        const countyBounds = villageLayer.getBounds();
        map.fitBounds(countyBounds, { 
            padding: [20, 20],
                maxZoom: 20
        });
        }
        
        currentCounty = countyName;
        isVillageMode = true;
        
        // 顯示控制組件
        document.getElementById('back-to-counties-btn').style.display = 'block';
        document.getElementById('bivariate-controls').style.display = 'block';
        document.getElementById('clinic-controls').style.display = 'block';
        
        // 設為雙變數模式並更新圖例
        isBivariateMode = true;
        updateBivariateLegend();
        

        
        hideLoading();
        
    } catch (error) {
        console.error('載入村里資料失敗:', error);
        hideLoading();
        alert('載入村里資料失敗，請稍後再試。');
    }
}

// 處理縮放變化事件
function handleZoomChange() {
    const zoomLevel = map.getZoom();
    console.log('處理縮放變化，當前縮放等級:', zoomLevel, '村里模式:', isVillageMode);
    
    // 更新地圖容器的縮放等級屬性，用於CSS縮放控制
    const mapContainer = document.getElementById('map');
    if (mapContainer) {
        mapContainer.setAttribute('data-zoom', zoomLevel);
    }
    
    if (zoomLevel < 9 && isVillageMode) {
        // 縮放等級小於 9 時，返回縣市視圖
        console.log('縮放等級 < 9，返回縣市視圖');
        backToCounties();
    } else if (zoomLevel >= 9 && isVillageMode) {
        // 在村里模式下，縮放等級 >= 9 時隱藏縣市標籤
        clearCountyMarkers();
    } else if (!isVillageMode) {
        // 在縣市模式下，始終顯示縣市標籤（不論縮放等級）
        if (countyMarkers.length === 0 && countyLayer) {
            showCountyLabels();
        }
    }
}

// 顯示縣市標籤
function showCountyLabels() {
    console.log('顯示縣市標籤');
    // 縣市標籤在載入時就已經添加，這裡可以控制可見性
    countyMarkers.forEach(marker => {
        if (!map.hasLayer(marker)) {
            map.addLayer(marker);
        }
    });
}

// 處理村里點擊事件
async function handleVillageClick(villageName, countyName, districtName) {
    console.log('=== 步驟 2：開始處理村里點擊 ===');
    console.log('接收參數:', { villageName, countyName, districtName });
    
    try {
        showLoading();
        
        // 並行載入薪資和人口資料
        const salaryUrl = `${API_BASE_URL}/api/village_salary/${encodeURIComponent(villageName)}?county_name=${encodeURIComponent(countyName)}&district_name=${encodeURIComponent(districtName)}`;
        const populationUrl = `${API_BASE_URL}/api/village_population/${encodeURIComponent(villageName)}?county_name=${encodeURIComponent(countyName)}&district_name=${encodeURIComponent(districtName)}`;
        
        console.log('薪資 API URL:', salaryUrl);
        console.log('人口 API URL:', populationUrl);
        
        console.log('正在並行載入薪資和人口資料...');
        const [salaryResponse, populationResponse] = await Promise.all([
            fetch(salaryUrl),
            fetch(populationUrl)
        ]);
        
        console.log('薪資API 回應狀態:', salaryResponse.status, salaryResponse.statusText);
        console.log('人口API 回應狀態:', populationResponse.status, populationResponse.statusText);
        
        if (!salaryResponse.ok) {
            const errorText = await salaryResponse.text();
            console.error('薪資API 錯誤回應:', errorText);
            throw new Error(`薪資資料載入失敗! status: ${salaryResponse.status}, message: ${errorText}`);
        }
        
        if (!populationResponse.ok) {
            const errorText = await populationResponse.text();
            console.error('人口API 錯誤回應:', errorText);
            throw new Error(`人口資料載入失敗! status: ${populationResponse.status}, message: ${errorText}`);
        }
        
        const salaryData = await salaryResponse.json();
        const populationData = await populationResponse.json();
        console.log('薪資資料載入成功:', salaryData);
        console.log('人口資料載入成功:', populationData);
        
        // 顯示資料面板
        showDataPanel(villageName, countyName, salaryData, districtName, populationData);
        
        hideLoading();
        
    } catch (error) {
        console.error('載入村里資料失敗:', error);
        console.error('錯誤詳情:', error.message);
        hideLoading();
        
        // 顯示更詳細的錯誤信息
        if (error.message.includes('404')) {
            alert(`找不到 ${countyName}${districtName}${villageName} 的資料`);
        } else {
            alert('載入村里資料失敗，請稍後再試。錯誤: ' + error.message);
        }
    }
}

// 顯示資料面板
// 全域變數儲存圖表實例
let salaryChart = null;

function showDataPanel(villageName, countyName, salaryData, districtName, populationData = null) {
    console.log('顯示資料面板:', villageName, countyName, districtName);
    console.log('薪資資料:', salaryData);
    console.log('人口資料:', populationData);
    
    const panel = document.getElementById('data-panel');
    const title = document.getElementById('panel-title');
    const content = document.getElementById('panel-content');
    
    title.textContent = `${countyName}${districtName}${villageName} 薪資與人口資料`;
    
    // 重新調整佈局：圖表在上方，表格並排在下方
    let tableHTML = '';
    
    // 添加圖表容器到最上方
    tableHTML += `
        <div class="data-section chart-section">
            <div id="chart-container" class="chart-container">
                <canvas id="combined-chart"></canvas>
            </div>
        </div>
    `;
    
    // 建立並排表格容器
    tableHTML += `
        <div class="tables-container">
            <div class="table-column">
                <div class="data-section compact">
                    <h4>薪資資料</h4>
                    <table class="data-table salary-table compact">
                        <thead>
                            <tr>
                                <th>年份</th>
                                <th>中位數</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    salaryData.forEach(item => {
        tableHTML += `
            <tr>
                <td>${item.年份}</td>
                <td>${formatSalaryNumber(item.中位數)}</td>
            </tr>
        `;
    });
    
    tableHTML += `
                        </tbody>
                    </table>
                </div>
            </div>
    `;
    
    // 人口資料表格（如果有人口資料）
    if (populationData && populationData.length > 0) {
        tableHTML += `
            <div class="table-column">
                <div class="data-section compact">
                    <h4>人口資料</h4>
                    <table class="data-table population-table compact">
                        <thead>
                            <tr>
                                <th>統計年月</th>
                                <th>戶數</th>
                                <th>人口數</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        populationData.forEach(item => {
            tableHTML += `
                <tr>
                    <td>${item.統計年月}</td>
                    <td>${formatPopulationNumber(item.戶數)}</td>
                    <td>${formatPopulationNumber(item.人口數)}</td>
                </tr>
            `;
        });
        
        tableHTML += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    tableHTML += `</div>`; // 結束 tables-container
    
    content.innerHTML = tableHTML;
    
    // 創建合併的折線圖（雙Y軸）
    createCombinedChart(salaryData, populationData, `${countyName}${districtName}${villageName}`);
    
    // 顯示面板
    panel.classList.add('show');
    

}

// 關閉資料面板
function closeDataPanel() {
    console.log('關閉資料面板');
    const panel = document.getElementById('data-panel');
    panel.classList.remove('show');
    
    // 銷毀現有圖表
    if (salaryChart) {
        salaryChart.destroy();
        salaryChart = null;
    }
}

// 創建合併的雙Y軸折線圖
function createCombinedChart(salaryData, populationData, villageName) {
    console.log('創建合併圖表:', villageName, salaryData, populationData);
    
    // 銷毀現有圖表
    if (salaryChart) {
        salaryChart.destroy();
        salaryChart = null;
    }
    
    // 準備圖表數據
    const salaryYears = salaryData.map(item => item.年份).sort((a, b) => a - b);
    const medianSalaries = salaryYears.map(year => {
        const item = salaryData.find(data => data.年份 === year);
        return item ? item.中位數 : null;
    });
    
    // 準備人口資料（如果有的話）
    let populationYears = [];
    let populationNumbers = [];
    
    if (populationData && populationData.length > 0) {
        // 按年份分組並取每年的平均值（如果有多個月份）
        const populationByYear = {};
        populationData.forEach(item => {
            if (!populationByYear[item.年份]) {
                populationByYear[item.年份] = [];
            }
            populationByYear[item.年份].push(item.人口數);
        });
        
        populationYears = Object.keys(populationByYear).map(year => parseInt(year)).sort((a, b) => a - b);
        populationNumbers = populationYears.map(year => {
            const values = populationByYear[year];
            // 取平均值
            return values.reduce((sum, val) => sum + val, 0) / values.length;
        });
    }
    
    // 合併所有年份，找出範圍
    const allYears = [...new Set([...salaryYears, ...populationYears])].sort((a, b) => a - b);
    
    // 獲取圖表容器
    const ctx = document.getElementById('combined-chart');
    if (!ctx) {
        console.error('找不到圖表容器');
        return;
    }
    
    // 準備資料集
    const datasets = [{
        label: '薪資中位數 (萬元)',
        data: allYears.map(year => {
            const salaryItem = salaryData.find(data => data.年份 === year);
            return salaryItem ? salaryItem.中位數 : null;
        }),
        borderColor: '#dc3545',
        backgroundColor: 'rgba(220, 53, 69, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointBackgroundColor: '#dc3545',
        pointBorderColor: '#dc3545',
        pointRadius: 4,
        pointHoverRadius: 6,
        yAxisID: 'y-salary'
    }];
    
    // 添加人口資料集（如果有的話）
    if (populationData && populationData.length > 0) {
        datasets.push({
            label: '人口數 (人)',
            data: allYears.map(year => {
                const populationByYear = {};
                populationData.forEach(item => {
                    if (!populationByYear[item.年份]) {
                        populationByYear[item.年份] = [];
                    }
                    populationByYear[item.年份].push(item.人口數);
                });
                
                if (populationByYear[year]) {
                    return populationByYear[year].reduce((sum, val) => sum + val, 0) / populationByYear[year].length;
                }
                return null;
            }),
            borderColor: '#007bff',
            backgroundColor: 'rgba(0, 123, 255, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointBackgroundColor: '#007bff',
            pointBorderColor: '#007bff',
            pointRadius: 4,
            pointHoverRadius: 6,
            yAxisID: 'y-population'
        });
    }
    
    // 創建圖表
    salaryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allYears,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `${villageName} 薪資與人口趨勢圖`,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    color: '#333'
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '年份',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                'y-salary': {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '薪資中位數 (萬元)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        color: '#dc3545'
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0,0,0,0.1)'
                    },
                    // 調整縱軸範圍以增加線條斜度
                    suggestedMin: function(context) {
                        const data = context.chart.data.datasets[0].data.filter(v => v !== null);
                        if (data.length > 0) {
                            const min = Math.min(...data);
                            const max = Math.max(...data);
                            const range = max - min;
                            return Math.max(0, min - range * 0.1); // 設定最小值，增加視覺變化
                        }
                        return 0;
                    },
                    suggestedMax: function(context) {
                        const data = context.chart.data.datasets[0].data.filter(v => v !== null);
                        if (data.length > 0) {
                            const min = Math.min(...data);
                            const max = Math.max(...data);
                            const range = max - min;
                            return max + range * 0.1; // 設定最大值，增加視覺變化
                        }
                        return 100;
                    },
                    ticks: {
                        color: '#dc3545',
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                'y-population': {
                    type: 'linear',
                    display: populationData && populationData.length > 0,
                    position: 'right',
                    title: {
                        display: true,
                        text: '人口數 (人)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        color: '#007bff'
                    },
                    grid: {
                        drawOnChartArea: false, // 只顯示左側網格線
                        color: 'rgba(0,0,0,0.1)'
                    },
                    // 調整人口數縱軸範圍以增加線條斜度
                    suggestedMin: function(context) {
                        const populationDataset = context.chart.data.datasets.find(ds => ds.yAxisID === 'y-population');
                        if (populationDataset) {
                            const data = populationDataset.data.filter(v => v !== null);
                            if (data.length > 0) {
                                const min = Math.min(...data);
                                const max = Math.max(...data);
                                const range = max - min;
                                return Math.max(0, min - range * 0.1);
                            }
                        }
                        return 0;
                    },
                    suggestedMax: function(context) {
                        const populationDataset = context.chart.data.datasets.find(ds => ds.yAxisID === 'y-population');
                        if (populationDataset) {
                            const data = populationDataset.data.filter(v => v !== null);
                            if (data.length > 0) {
                                const min = Math.min(...data);
                                const max = Math.max(...data);
                                const range = max - min;
                                return max + range * 0.1;
                            }
                        }
                        return 10000;
                    },
                    ticks: {
                        color: '#007bff',
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            elements: {
                point: {
                    hoverBorderWidth: 2
                }
            }
        }
    });
    
    console.log('合併圖表創建完成');
}

// 返回縣市界
function backToCounties() {
    console.log('返回縣市界');
    // 移除村里圖層和標籤
    if (villageLayer) {
        map.removeLayer(villageLayer);
        villageLayer = null;
    }
    // 清除村里標籤
    clearVillageMarkers();
    
    // 恢復縣市色塊顯示
    showSelectedCountyLayer();
    
    // 重新顯示縣市標籤
    showCountyLabels();
    
    // 確保顯示完整的台灣本島區域
    const taiwanBounds = L.latLngBounds(
        [22.0, 120.0], // 台灣本島西南角
        [25.0, 122.0]  // 台灣本島東北角
    );
    console.log('返回台灣本島邊界:', taiwanBounds);
    map.fitBounds(taiwanBounds, { padding: [20, 20] });
    
    // 隱藏控制組件
    document.getElementById('back-to-counties-btn').style.display = 'none';
    document.getElementById('bivariate-controls').style.display = 'none';
    document.getElementById('clinic-controls').style.display = 'none';
    
    // 清除診所地標
    clearClinicMarkers();
    
    // 隱藏雙變數圖例
    const bivariateLegend = document.getElementById('bivariate-legend');
    if (bivariateLegend) {
        bivariateLegend.classList.remove('show');
    }
    
    currentCounty = null;
    isVillageMode = false;
    isBivariateMode = false;
    currentVillageData = null;
    
    // 關閉資料面板
    closeDataPanel();
}



// 清除縣市標籤
function clearCountyMarkers() {
    console.log('清除縣市標籤，數量:', countyMarkers.length);
    countyMarkers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    countyMarkers = [];
}

// 隱藏選中的縣市色塊
function hideSelectedCountyLayer(countyName) {
    console.log('隱藏縣市色塊:', countyName);
    if (!countyLayer) return;
    
    countyLayer.eachLayer(function(layer) {
        if (layer.feature && layer.feature.properties && layer.feature.properties.name === countyName) {
            selectedCountyLayer = layer;
            layer.setStyle({
                fillOpacity: 0,
                opacity: 0
            });
        }
    });
}

// 恢復選中的縣市色塊顯示
function showSelectedCountyLayer() {
    console.log('恢復縣市色塊顯示');
    if (selectedCountyLayer) {
        selectedCountyLayer.setStyle({
            fillOpacity: 0.7,
            opacity: 1
        });
        selectedCountyLayer = null;
    }
}

// 清除村里標籤
function clearVillageMarkers() {
    console.log('清除村里標籤，數量:', villageMarkers.length);
    villageMarkers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    villageMarkers = [];
}

// 顯示縣市標籤
function showCountyLabels() {
    console.log('顯示縣市標籤');
    if (!countyLayer) return;
    
    // 先清除現有標籤
    clearCountyMarkers();
    
    countyLayer.eachLayer(function(layer) {
        if (layer.feature && layer.feature.properties) {
            const feature = layer.feature;
            
            // 使用與初始載入相同的邏輯：優先使用後端提供的座標
            let markerLat, markerLng;
            
            if (feature.properties.center_lat && feature.properties.center_lon) {
                // 直接使用後端提供的正確座標
                markerLat = parseFloat(feature.properties.center_lat);
                markerLng = parseFloat(feature.properties.center_lon);
                console.log(`${feature.properties.name} 重新顯示，使用後端座標: lat=${markerLat}, lng=${markerLng}`);
            } else {
                console.error(`${feature.properties.name} 缺少後端座標資料`);
                return; // 跳過沒有座標資料的標籤
            }
            
            const label = L.divIcon({
                className: 'county-label',
                html: feature.properties.name,
                iconSize: [100, 20],
                iconAnchor: [50, 10]
            });
            
            const marker = L.marker([markerLat, markerLng], {
                icon: label
            }).addTo(map);
            countyMarkers.push(marker);
        }
    });
}

// 格式化數字
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    } else {
        return num.toLocaleString();
    }
}

// 格式化人口數據（完整顯示，不使用K簡化）
function formatPopulationNumber(num) {
    return parseInt(num).toLocaleString();
}

// 格式化薪資數字（單位：萬元）
function formatSalaryNumber(num) {
    return Math.round(num).toLocaleString();
}

// 顯示載入指示器
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

// 隱藏載入指示器
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// 更新村里圖層樣式
function updateVillageLayerStyle() {
    if (villageLayer && isVillageMode) {
        const zoomLevel = map.getZoom();
        let weight = 1;
        if (zoomLevel >= 15) weight = 2;
        if (zoomLevel >= 17) weight = 3;
        
        villageLayer.setStyle({
            weight: weight,
            opacity: 1,
            color: '#000000',
            fillOpacity: 0.7
        });
        
        console.log(`更新村里界線粗細: ${weight} (縮放等級: ${zoomLevel})`);
    }
}

// 更新圖例顯示薪資範圍
function updateLegendWithSalaryRanges(villageData) {
    // 此函數已棄用，因為單變數圖例已移除
    // 保留函數以避免其他地方的調用錯誤
    return;
}

// 檢查 API 連線狀態
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (response.ok) {
            const health = await response.json();
            console.log('API 健康狀態:', health);
            return true;
        }
    } catch (error) {
        console.error('API 連線失敗:', error);
        return false;
    }
    return false;
}

// 更新雙變數圖例
async function updateBivariateLegend() {
    if (!isBivariateMode) return;
    
    try {
        // 獲取雙變數色彩矩陣
        const response = await fetch(`${API_BASE_URL}/api/bivariate_colors?income_weight=${currentWeights.income}&density_weight=${currentWeights.density}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const colorData = await response.json();
        
        // 顯示雙變數圖例
        const bivariateLegend = document.getElementById('bivariate-legend');
        bivariateLegend.style.display = 'block';
        bivariateLegend.classList.add('show');
        
        // 更新色彩矩陣
        const matrixContainer = document.getElementById('bivariate-matrix');
        matrixContainer.innerHTML = '';
        
        for (let densityLevel = 8; densityLevel >= 0; densityLevel--) { // 從高到低（上到下）
            for (let incomeLevel = 0; incomeLevel < 9; incomeLevel++) { // 從低到高（左到右）
                const cell = document.createElement('div');
                cell.className = 'matrix-cell';
                cell.style.backgroundColor = colorData.color_matrix[incomeLevel][densityLevel];
                cell.title = `薪資等級: ${incomeLevel}, 人口密度等級: ${densityLevel}`;
                matrixContainer.appendChild(cell);
            }
        }
        
    } catch (error) {
        console.error('更新雙變數圖例失敗:', error);
    }
}

// 重新載入村里資料並更新顏色
async function reloadVillageColors() {
    if (!currentCounty || !isVillageMode) return;
    
    try {
        showLoading();
        
        // 重新載入資料
        const response = await fetch(`${API_BASE_URL}/api/villages/${encodeURIComponent(currentCounty)}?income_weight=${currentWeights.income}&density_weight=${currentWeights.density}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const villageData = await response.json();
        currentVillageData = villageData;
        
        // 更新現有圖層的顏色
        if (villageLayer) {
            villageLayer.eachLayer(function(layer) {
                if (layer.feature && layer.feature.properties) {
                    const feature = layer.feature;
                    // 尋找對應的更新資料
                    const updatedFeature = villageData.features.find(f => 
                        f.properties.name === feature.properties.name &&
                        f.properties.district === feature.properties.district
                    );
                    
                    if (updatedFeature && updatedFeature.properties.bivariate_color) {
                        // 將hex顏色轉換為rgba並加上透明度
                        const fillColor = hexToRgba(updatedFeature.properties.bivariate_color, 0.4);
                        layer.setStyle({
                            fillColor: fillColor,
                            fillOpacity: 0.9  // 使用固定透明度0.9
                        });
                    }
                }
            });
        }
        
        // 更新圖例
        updateBivariateLegend();
        
        hideLoading();
        
    } catch (error) {
        console.error('重新載入村里顏色失敗:', error);
        hideLoading();
    }
}

// 滑桿事件處理
function setupSliderEvents() {
    const incomeSlider = document.getElementById('income-weight');
    const densitySlider = document.getElementById('density-weight');
    const incomeValue = document.getElementById('income-weight-value');
    const densityValue = document.getElementById('density-weight-value');
    
    // 更新顯示值和互補權重
    function updateValues(changedSlider) {
        let incomeWeight, densityWeight;
        
        if (changedSlider === 'income') {
            incomeWeight = parseFloat(incomeSlider.value);
            densityWeight = 100 - incomeWeight;
            densitySlider.value = densityWeight;
        } else if (changedSlider === 'density') {
            densityWeight = parseFloat(densitySlider.value);
            incomeWeight = 100 - densityWeight;
            incomeSlider.value = incomeWeight;
        } else {
            // 初始化
            incomeWeight = parseFloat(incomeSlider.value);
            densityWeight = parseFloat(densitySlider.value);
        }
        
        // 更新顯示文字
        incomeValue.textContent = Math.round(incomeWeight) + '%';
        densityValue.textContent = Math.round(densityWeight) + '%';
        
        // 更新全域權重（歸一化到0-1）
        currentWeights.income = incomeWeight / 100;
        currentWeights.density = densityWeight / 100;
        
        console.log(`權重更新: 薪資=${currentWeights.income.toFixed(2)}, 人口密度=${currentWeights.density.toFixed(2)}`);
    }
    
    // 防抖函數
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // 建立防抖更新函數
    const debouncedReload = debounce(reloadVillageColors, 300);
    
    // 事件監聽器
    incomeSlider.addEventListener('input', function() {
        updateValues('income');
        debouncedReload();
    });
    
    densitySlider.addEventListener('input', function() {
        updateValues('density');
        debouncedReload();
    });
    
    // 初始化權重顯示
    updateValues();
}

// 頁面載入完成後初始化
document.addEventListener('DOMContentLoaded', async function() {
    console.log('頁面載入完成，開始初始化...');
    
    // 檢查 API 連線
    const isAPIHealthy = await checkAPIHealth();
    if (!isAPIHealthy) {
        alert('無法連接到後端 API，請確保後端服務正在運行。');
        return;
    }
    
    // 設定滑桿事件
    setupSliderEvents();
    
    // 初始化地圖
    initMap();
});

// === 診所地標相關功能 ===

// 載入診所科別資料
async function loadClinicSpecialties() {
    try {
        console.log('載入診所科別資料...');
        const response = await fetch(`${API_BASE_URL}/api/clinic_specialties`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        clinicSpecialties = data.specialties;
        console.log('診所科別載入成功:', clinicSpecialties);
        
        // 創建科別勾選框
        createSpecialtyCheckboxes();
        
    } catch (error) {
        console.error('載入診所科別失敗:', error);
        document.getElementById('specialty-checkboxes').innerHTML = 
            '<div class="loading-specialties" style="color: #ff4444;">載入科別失敗</div>';
    }
}

// 創建科別勾選框
function createSpecialtyCheckboxes() {
    const container = document.getElementById('specialty-checkboxes');
    container.innerHTML = '';
    
    clinicSpecialties.forEach(specialty => {
        const checkboxDiv = document.createElement('div');
        checkboxDiv.className = 'specialty-checkbox';
        
        checkboxDiv.innerHTML = `
            <input type="checkbox" id="specialty-${specialty.name}" value="${specialty.name}">
            <span class="specialty-icon">${specialty.icon}</span>
            <span class="specialty-name">${specialty.name}</span>
        `;
        
        // 只為checkbox添加點擊事件
        const checkbox = checkboxDiv.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', (event) => {
            event.stopPropagation();
            toggleSpecialty(specialty.name, checkboxDiv, event);
        });
        
        container.appendChild(checkboxDiv);
    });
    
    console.log(`已創建 ${clinicSpecialties.length} 個科別勾選框`);
}

// 切換科別勾選狀態
function toggleSpecialty(specialtyName, checkboxDiv, event) {
    // 防止事件冒泡
    if (event) {
        event.stopPropagation();
    }
    
    const checkbox = checkboxDiv.querySelector('input[type="checkbox"]');
    
    if (checkbox.checked) {
        selectedSpecialties.add(specialtyName);
        checkboxDiv.classList.add('checked');
    } else {
        selectedSpecialties.delete(specialtyName);
        checkboxDiv.classList.remove('checked');
    }
    
    console.log('選中的科別:', Array.from(selectedSpecialties));
    
    // 更新診所地標顯示
    if (currentCounty && isVillageMode) {
        updateClinicMarkers();
    }
}

// 載入並顯示診所地標
async function updateClinicMarkers() {
    if (!currentCounty || selectedSpecialties.size === 0) {
        clearClinicMarkers();
        return;
    }
    
    try {
        showLoading();
        
        const specialtiesParam = Array.from(selectedSpecialties).join(',');
        const response = await fetch(`${API_BASE_URL}/api/clinics/${encodeURIComponent(currentCounty)}?specialties=${encodeURIComponent(specialtiesParam)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const clinicData = await response.json();
        console.log(`載入 ${currentCounty} 的診所地標:`, clinicData.features.length, '個');
        
        // 先清除現有的診所標記
        clearClinicMarkers();
        
        // 添加測試多科別診所（測試雙標記系統）
        if (clinicData.features.length > 0) {
            const testClinic = {...clinicData.features[0]};
            testClinic.properties = {
                ...testClinic.properties,
                name: "測試雙標記系統",
                specialties: ["耳鼻喉科", "家庭醫學科", "內科", "眼科"]
            };
            clinicData.features.push(testClinic);
            console.log("已添加測試診所（雙標記系統）");
        }
        
        // 添加新的診所標記
        clinicData.features.forEach(clinic => {
            // 根據診所的科別選擇合適的圖示（選擇最高優先級的科別）
            const clinicSpecialtyNames = clinic.properties.specialties;
            let markerIcon = '🏥'; // 預設圖示
            let highestPrioritySpecialty = null;
            let lowestOrder = 999;
            
            // 找出最高優先級的科別（order值最小）
            for (const specialtyName of clinicSpecialtyNames) {
                const specialty = clinicSpecialties.find(s => s.name === specialtyName);
                if (specialty && specialty.order < lowestOrder) {
                    lowestOrder = specialty.order;
                    highestPrioritySpecialty = specialty;
                    markerIcon = specialty.icon;
                }
            }
            
            // 計算總科別數量（用於數字標記）
            const totalSpecialties = clinicSpecialtyNames.length;
            console.log(`診所: ${clinic.properties.name}, 科別數量: ${totalSpecialties}, 使用雙標記系統`);
            
            // 雙標記系統：主圖標(純文本) + 數字標記(獨立標記)
            const lat = clinic.geometry.coordinates[1];
            const lng = clinic.geometry.coordinates[0];
            
            // 主圖標：純文本，定位絕對準確
            const marker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'clinic-marker',
                    html: markerIcon,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12],
                    popupAnchor: [0, -12]
                })
            });
            
            // 將主圖標添加到地圖和標記數組
            marker.addTo(map);
            clinicMarkers.push(marker);
            
            // 如果是多科別，添加獨立的數字標記（精確偏移到右上角）
            if (totalSpecialties > 1) {
                console.log(`多科別診所: ${clinic.properties.name}, 添加數字標記: ${totalSpecialties}`);
                const badgeMarker = L.marker([lat, lng], {
                    icon: L.divIcon({
                        className: 'clinic-badge',
                        html: totalSpecialties.toString(),
                        iconSize: [12, 12],
                        iconAnchor: [-6, 18] // 精確計算：右上角位置
                    })
                });
                badgeMarker.addTo(map);
                clinicMarkers.push(badgeMarker);
            }
            
            // 創建豐富的彈出窗口內容，包含所有科別及其圖標
            let specialtiesHtml = '';
            clinicSpecialtyNames.forEach(specialtyName => {
                const specialty = clinicSpecialties.find(s => s.name === specialtyName);
                const icon = specialty ? specialty.icon : '🏥';
                specialtiesHtml += `<span class="specialty-item">${icon} ${specialtyName}</span>`;
            });
            
            const popupContent = `
                <div class="clinic-popup">
                    <div class="clinic-name">📍 ${clinic.properties.name}</div>
                    <div class="clinic-address">📍 ${clinic.properties.address}</div>
                    <div class="clinic-specialties-header">🏥 提供科別：</div>
                    <div class="clinic-specialties">
                        ${specialtiesHtml}
                    </div>
                </div>
            `;
            
            marker.bindPopup(popupContent);
        });
        
        console.log(`已添加 ${clinicMarkers.length} 個診所標記`);
        hideLoading();
        
    } catch (error) {
        console.error('載入診所地標失敗:', error);
        hideLoading();
    }
}

// 清除所有診所標記
function clearClinicMarkers() {
    console.log('清除診所標記，數量:', clinicMarkers.length);
    clinicMarkers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    clinicMarkers = [];
}

// 重置診所勾選狀態
function resetClinicSelections() {
    console.log('重置診所勾選狀態');
    
    // 清除選中的科別集合
    selectedSpecialties = new Set();
    
    // 重置所有勾選框的視覺狀態
    const checkboxes = document.querySelectorAll('.specialty-checkbox');
    checkboxes.forEach(checkboxDiv => {
        const checkbox = checkboxDiv.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.checked = false;
        }
        checkboxDiv.classList.remove('checked');
    });
    
    // 清除診所標記
    clearClinicMarkers();
}