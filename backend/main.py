from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import geopandas as gpd
import pandas as pd
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from shapely.geometry import mapping
import warnings
warnings.filterwarnings('ignore')

# 雙變數顏色矩陣定義 (9x9)
# 行：薪資等級 (0-8)，列：人口密度等級 (0-8)
# 薪資色系：紅色系，人口密度色系：藍色系
# 左下角（低薪資，低人口密度）：淺色，右上角（高薪資，高人口密度）：深紫色
BIVARIATE_COLOR_MATRIX = [
    # 薪資等級 0 (最低) - 從淺灰到純藍色
    ['#f7f7f7', '#e8f2ff', '#d4e7fd', '#bfdcfa', '#aad1f7', '#95c6f4', '#80bbf1', '#6baeed', '#559fea'],
    # 薪資等級 1 - 從淺粉紅到藍紫
    ['#fff0f0', '#f0e8ff', '#e1d4fd', '#d2bffa', '#c3aaf7', '#b495f4', '#a580f1', '#966bed', '#8756ea'],
    # 薪資等級 2 - 從粉紅到紫色  
    ['#ffe8e8', '#f5d4f5', '#ebbfeb', '#e1aae1', '#d795d7', '#cd80cd', '#c36bc3', '#b956b9', '#af41af'],
    # 薪資等級 3 - 從淺紅到紅紫
    ['#ffe0e0', '#f7c1c1', '#efa2a2', '#e78383', '#df6464', '#d74545', '#cf2626', '#c70707', '#bf0000'],
    # 薪資等級 4 - 從紅到深紅紫
    ['#ffd8d8', '#f5adad', '#eb8282', '#e15757', '#d72c2c', '#cd0101', '#c30000', '#b90000', '#af0000'],
    # 薪資等級 5 - 中等紅色系
    ['#ffd0d0', '#f2999a', '#e56264', '#d82b2e', '#cb0000', '#be0000', '#b10000', '#a40000', '#970000'],
    # 薪資等級 6 - 深紅色系
    ['#ffc8c8', '#ef8587', '#df424a', '#cf000d', '#bf0000', '#af0000', '#9f0000', '#8f0000', '#7f0000'],
    # 薪資等級 7 - 更深紅色
    ['#ffc0c0', '#ec7174', '#d92227', '#c60000', '#b30000', '#a00000', '#8d0000', '#7a0000', '#670000'],
    # 薪資等級 8 (最高) - 最深紅色  
    ['#ffb8b8', '#e95d61', '#d30204', '#bd0000', '#a70000', '#910000', '#7b0000', '#650000', '#4f0000']
]

def get_bivariate_color(income_level, density_level, income_weight=0.5, density_weight=0.5):
    """
    根據收入等級、人口密度等級和權重計算雙變數顏色
    簡化版：直接根據權重線性混合紅色系（薪資）和藍色系（人口密度）
    
    Args:
        income_level (int): 薪資等級 (0-8)
        density_level (int): 人口密度等級 (0-8)  
        income_weight (float): 薪資權重 (0-1)
        density_weight (float): 人口密度權重 (0-1)，應滿足 income_weight + density_weight = 1
    
    Returns:
        str: hex 顏色代碼
    """
    # 確保等級在有效範圍內
    income_level = max(0, min(8, int(income_level)))
    density_level = max(0, min(8, int(density_level)))
    
    # 正規化權重（確保總和為1）
    total_weight = income_weight + density_weight
    if total_weight == 0:
        return '#f7f7f7'  # 灰色，當兩個權重都為0時
    
    income_weight_norm = income_weight / total_weight
    density_weight_norm = density_weight / total_weight
    
    # 定義薪資色系（紅色系）和人口密度色系（藍色系）
    income_colors = ['#fee5d9', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d', '#4d0000']
    density_colors = ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b']
    
    # 獲取對應等級的基礎顏色
    income_color = income_colors[income_level]
    density_color = density_colors[density_level]
    
    # 直接根據權重進行線性混合
    # income_weight_norm 接近 1 時顯示紅色系
    # density_weight_norm 接近 1 時顯示藍色系
    return blend_colors_with_ratio(income_color, density_color, income_weight_norm, density_weight_norm)

def blend_colors_with_ratio(color1, color2, weight1, weight2):
    """
    按照特定比例混合兩個 hex 顏色
    """
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(rgb):
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    # 加權平均
    total_weight = weight1 + weight2
    if total_weight == 0:
        return color1
    
    weight1 = weight1 / total_weight
    weight2 = weight2 / total_weight
    
    mixed_rgb = (
        rgb1[0] * weight1 + rgb2[0] * weight2,
        rgb1[1] * weight1 + rgb2[1] * weight2,
        rgb1[2] * weight1 + rgb2[2] * weight2
    )
    
    return rgb_to_hex(mixed_rgb)

def blend_colors(color1, color2, weight1, weight2):
    """
    混合兩個 hex 顏色
    """
    # 轉換 hex 到 RGB
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # RGB 到 hex
    def rgb_to_hex(rgb):
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    # 加權平均
    total_weight = weight1 + weight2
    if total_weight == 0:
        return color1
    
    weight1 = weight1 / total_weight
    weight2 = weight2 / total_weight
    
    mixed_rgb = (
        rgb1[0] * weight1 + rgb2[0] * weight2,
        rgb1[1] * weight1 + rgb2[1] * weight2,
        rgb1[2] * weight1 + rgb2[2] * weight2
    )
    
    return rgb_to_hex(mixed_rgb)

print("正在初始化 FastAPI 應用程式...")

app = FastAPI(title="台灣地圖 API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境中應該限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料路徑配置
BASE_DIR = Path(__file__).parent.parent
COUNTY_GEOJSON_PATH = BASE_DIR / "taiwan_country_border" / "taiwan_country_border.geojson"
VILLAGE_GEOJSON_PATH = BASE_DIR / "taiwan_village_border" / "counties_villages_standardized.geojson"
SALARY_DATA_DIR = BASE_DIR / "salary-gh-pages" / "data" / "csv"
POPULATION_DATA_DIR = BASE_DIR / "taiwan_population_data"
CLINIC_DATA_PATH = BASE_DIR / "taiwan_clinic_site" / "TAIWAN CLINIC SITE_FINAL_20231231.csv"

print(f"BASE_DIR: {BASE_DIR}")
print(f"COUNTY_GEOJSON_PATH: {COUNTY_GEOJSON_PATH}")
print(f"VILLAGE_GEOJSON_PATH: {VILLAGE_GEOJSON_PATH}")
print(f"SALARY_DATA_DIR: {SALARY_DATA_DIR}")

# 全域變數儲存處理後的資料
county_data = None
village_data = None
salary_data = None
population_data = None
village_salary_mapping = None
village_population_mapping = None
clinic_data = None



def calculate_area_km2(gdf):
    """
    計算 GeoDataFrame 中每個幾何的面積（平方公里）
    使用適合台灣的投影座標系統 TWD97 TM2 (EPSG:3826)
    """
    print("開始計算面積...")
    
    # 確保原始資料是 EPSG:4326 (WGS84)
    if gdf.crs != 'EPSG:4326':
        print(f"警告：資料CRS不是EPSG:4326，當前為: {gdf.crs}")
        gdf = gdf.to_crs('EPSG:4326')
    
    # 轉換到台灣適用的投影座標系統 (TWD97 TM2)
    try:
        gdf_projected = gdf.to_crs('EPSG:3826')
        print("成功轉換到 TWD97 TM2 (EPSG:3826)")
    except Exception as e:
        print(f"無法轉換到EPSG:3826，嘗試使用等面積投影: {e}")
        # 如果TWD97不可用，使用適合台灣地區的等面積投影
        # 使用 Albers Equal Area Conic 投影，參數適合台灣
        taiwan_albers = "+proj=aea +lat_1=22 +lat_2=26 +lat_0=24 +lon_0=121 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
        gdf_projected = gdf.to_crs(taiwan_albers)
        print("使用台灣Albers等面積投影")
    
    # 計算面積（平方公里）
    areas_km2 = gdf_projected.area / 1000000  # 從平方公尺轉換為平方公里
    
    print(f"面積計算完成，範圍：{areas_km2.min():.6f} - {areas_km2.max():.6f} km²")
    return areas_km2

def standardize_specialties(specialty_str):
    """
    標準化科別名稱，合併相似科別
    
    Args:
        specialty_str: 原始科別字串，可能包含多個科別用逗號分隔
        
    Returns:
        set: 標準化後的科別集合
    """
    if pd.isna(specialty_str) or specialty_str is None:
        return set()
    
    # 分割多個科別
    specialties = [s.strip() for s in str(specialty_str).split(',')]
    
    standardized = set()
    
    for specialty in specialties:
        # 家庭醫學科 + 西醫一般科 合併為 "家庭醫學科"
        if specialty in ['家庭醫學科', '西醫一般科']:
            standardized.add('家庭醫學科')
        # 整形外科 + 醫美整形 + 皮膚科 合併為 "醫美整形科"
        elif specialty in ['整形外科', '醫美整形', '皮膚科']:
            standardized.add('醫美整形科')
        # 其他主要科別直接加入
        elif specialty in ['牙科', '中醫', '眼科', '耳鼻喉科', '骨科', '內科', '外科', '婦產科', 
                         '兒科', '精神科', '神經科', '復健科', '泌尿科']:
            standardized.add(specialty)
        # 其他複雜科別歸類到"其他"
        elif not any(main in specialty for main in ['一般科', '診斷科', '腫瘤科', '病理科', 
                                                   '醫學科', '麻醉科', '放射']):
            standardized.add('其他')
    
    return standardized

def load_and_process_data():
    """載入並處理所有地理、薪資、人口和診所資料"""
    global county_data, village_data, salary_data, population_data, village_salary_mapping, village_population_mapping, clinic_data
    print("=== 開始載入資料 ===")
    
    print("正在載入地理資料...")
    
    # 載入縣市界資料
    if COUNTY_GEOJSON_PATH.exists():
        print("使用 json 模組直接讀取 GeoJSON...")
        # 直接使用 json 模組讀取 GeoJSON，避免 fiona 版本問題
        import json
        with open(COUNTY_GEOJSON_PATH, 'r', encoding='utf-8') as f:
            county_geojson = json.load(f)
        county_gdf = gpd.GeoDataFrame.from_features(county_geojson['features'])
        
        # 所有檔案已統一為 WGS84 (EPSG:4326)，直接設定 CRS
        print("設定縣市界為 WGS84 (EPSG:4326)")
        county_gdf.set_crs(epsg=4326, inplace=True, allow_override=True)
        print(f"縣市界 CRS: {county_gdf.crs}")
        
        # 計算代表性點 - 簡化版本，直接使用 WGS84 座標
        def get_representative_point(geometry):
            try:
                # 首先嘗試使用 representative_point
                rep_point = geometry.representative_point()
                
                # 檢查點是否在幾何內部
                if geometry.contains(rep_point):
                    print(f"使用 representative_point: ({rep_point.x:.6f}, {rep_point.y:.6f})")
                    return rep_point
                
                # 如果不在內部，嘗試使用 centroid
                centroid = geometry.centroid
                if geometry.contains(centroid):
                    print(f"使用 centroid: ({centroid.x:.6f}, {centroid.y:.6f})")
                    return centroid
                
                # 對於 MultiPolygon，使用最大多邊形的 centroid
                if geometry.geom_type == 'MultiPolygon':
                    largest_polygon = max(geometry.geoms, key=lambda p: p.area)
                    largest_centroid = largest_polygon.centroid
                    print(f"使用最大多邊形的 centroid: ({largest_centroid.x:.6f}, {largest_centroid.y:.6f})")
                    return largest_centroid
                
                # 所有方法都失敗
                print(f"無法找到合適的內部點")
                return None
                
            except Exception as e:
                print(f"座標計算錯誤: {e}")
                return None
        
        # 移除座標順序檢查函數，因為所有檔案已統一為 WGS84
        
        # 使用更安全的方式處理幾何資料
        representative_points = []
        center_lats = []
        center_lons = []
        
        for geometry in county_gdf['geometry']:
            rep_point = get_representative_point(geometry)
            if rep_point is not None:
                representative_points.append(rep_point)
                lat = rep_point.y
                lon = rep_point.x
                center_lats.append(lat)
                center_lons.append(lon)
            else:
                print("跳過無法計算合適座標的縣市")
                representative_points.append(None)
                center_lats.append(None)
                center_lons.append(None)
        
        county_gdf['representative_point'] = representative_points
        county_gdf['center_lat'] = center_lats
        county_gdf['center_lon'] = center_lons
        
        county_data = county_gdf
        print(f"已載入 {len(county_data)} 個縣市")
    else:
        raise FileNotFoundError(f"找不到縣市界檔案: {COUNTY_GEOJSON_PATH}")
    
    # 載入村里界資料
    if VILLAGE_GEOJSON_PATH.exists():
        print("使用 json 模組直接讀取 GeoJSON...")
        # 直接使用 json 模組讀取 GeoJSON，避免 fiona 版本問題
        import json
        with open(VILLAGE_GEOJSON_PATH, 'r', encoding='utf-8') as f:
            village_geojson = json.load(f)
        village_gdf = gpd.GeoDataFrame.from_features(village_geojson['features'])
        
        # 所有檔案已統一為 WGS84 (EPSG:4326)，直接設定 CRS
        print("設定村里界為 WGS84 (EPSG:4326)")
        village_gdf.set_crs(epsg=4326, inplace=True, allow_override=True)
        print(f"村里界 CRS: {village_gdf.crs}")
        
        # 計算村里的中心點
        representative_points = []
        center_lats = []
        center_lons = []
        
        for geometry in village_gdf['geometry']:
            rep_point = get_representative_point(geometry)
            if rep_point is not None:
                representative_points.append(rep_point)
                lat = rep_point.y
                lon = rep_point.x
                center_lats.append(lat)
                center_lons.append(lon)
            else:
                print("跳過無法計算合適座標的村里")
                representative_points.append(None)
                center_lats.append(None)
                center_lons.append(None)
        
        village_gdf['representative_point'] = representative_points
        village_gdf['center_lat'] = center_lats
        village_gdf['center_lon'] = center_lons
        
        # 計算村里面積
        print("正在計算村里面積...")
        village_gdf['area_km2'] = calculate_area_km2(village_gdf)
        
        village_data = village_gdf
        print(f"已載入 {len(village_data)} 個村里，面積範圍：{village_gdf['area_km2'].min():.6f} - {village_gdf['area_km2'].max():.6f} km²")
    else:
        raise FileNotFoundError(f"找不到村里界檔案: {VILLAGE_GEOJSON_PATH}")
    
    # 載入薪資資料（使用標準化檔案）
    print("正在載入標準化薪資資料...")
    salary_files = []
    for year in range(2011, 2024):  # 2011-2023
        file_path = SALARY_DATA_DIR / f"{year}_standardized.csv"
        if file_path.exists():
            salary_files.append(file_path)
    
    if not salary_files:
        raise FileNotFoundError(f"找不到薪資資料檔案在: {SALARY_DATA_DIR}")
    
    # 載入所有年份的薪資資料
    all_salary_data = []
    for file_path in salary_files:
        # 從檔案名稱中提取年份 (例如: 2011_standardized.csv -> 2011)
        year_str = file_path.stem.split('_')[0]
        year = int(year_str)
        df = pd.read_csv(file_path)
        df['年份'] = year
        all_salary_data.append(df)
    
    salary_data = pd.concat(all_salary_data, ignore_index=True)
    print(f"已載入 {len(salary_data)} 筆薪資資料記錄")
    
    # 載入人口資料（使用最新的標準化檔案）
    print("正在載入人口資料...")
    population_files = list(POPULATION_DATA_DIR.glob("*_standardized.csv"))
    if population_files:
        # 選擇最新的人口資料檔案
        latest_population_file = max(population_files, key=lambda x: x.stem)
        print(f"使用人口資料檔案: {latest_population_file.name}")
        population_data = pd.read_csv(latest_population_file)
        print(f"已載入 {len(population_data)} 筆人口資料記錄")
    else:
        raise FileNotFoundError(f"找不到人口資料檔案在: {POPULATION_DATA_DIR}")
    
    # 建立村里薪資對應關係
    print("正在建立村里薪資對應關係...")
    village_salary_mapping = {}
    

    
    # 取得最新年份（2023）的村里中位數資料
    latest_salary = salary_data[salary_data['年份'] == 2023].copy()
    
    # 建立村里名稱對應表（直接使用標準化資料）
    for _, row in latest_salary.iterrows():
        county_name = row['縣市']
        district_name = row['鄉鎮市區']
        village_name = row['村里']
        
        key = f"{county_name}_{district_name}_{village_name}"
        
        mapping_data = {
            'county': county_name,
            'district': district_name,
            'village': village_name,
            'median_income': row['中位數'],
            'total_income': row['綜合所得總額'],
            'average_income': row['平均數']
        }
        
        village_salary_mapping[key] = mapping_data
    
    print(f"已建立 {len(village_salary_mapping)} 個村里的薪資對應關係")
    
    # 建立村里人口密度對應關係
    print("正在建立村里人口密度對應關係...")
    village_population_mapping = {}
    
    # 使用人口資料計算人口密度
    for _, pop_row in population_data.iterrows():
        county_name = pop_row['縣市']
        district_name = pop_row['鄉鎮市區'] 
        village_name = pop_row['村里']
        population = pop_row['人口數']
        
        # 對應到村里地理資料，找到面積
        village_match = village_data[
            (village_data['COUNTYNAME'] == county_name) & 
            (village_data['TOWNNAME'] == district_name) & 
            (village_data['VILLNAME'] == village_name)
        ]
        
        if not village_match.empty:
            area_km2 = village_match.iloc[0]['area_km2']
            if area_km2 > 0:  # 避免除以零
                population_density = population / area_km2
                
                key = f"{county_name}_{district_name}_{village_name}"
                village_population_mapping[key] = {
                    'county': county_name,
                    'district': district_name, 
                    'village': village_name,
                    'population': population,
                    'area_km2': area_km2,
                    'population_density': population_density
                }
    
    print(f"已建立 {len(village_population_mapping)} 個村里的人口密度對應關係")
    print(f"人口密度範圍：{min([v['population_density'] for v in village_population_mapping.values()]):.2f} - {max([v['population_density'] for v in village_population_mapping.values()]):.2f} 人/km²")

    # 載入診所資料
    print("正在載入診所資料...")
    if CLINIC_DATA_PATH.exists():
        clinic_data = pd.read_csv(CLINIC_DATA_PATH)
        
        # 從縣市區名中提取縣市名稱 (例如：臺北市松山區 -> 臺北市)
        clinic_data['縣市'] = clinic_data['縣市區名'].str[:3]
        
        # 標準化科別
        clinic_data['標準科別'] = clinic_data['科別'].apply(standardize_specialties)
        
        # 移除無效的座標資料
        clinic_data = clinic_data.dropna(subset=['經度', '緯度'])
        clinic_data = clinic_data[(clinic_data['經度'] != 0) & (clinic_data['緯度'] != 0)]
        
        print(f"已載入 {len(clinic_data)} 筆診所資料")
        
        # 統計科別分布
        all_specialties = set()
        for specialty_set in clinic_data['標準科別']:
            all_specialties.update(specialty_set)
        print(f"標準化後共有 {len(all_specialties)} 種科別: {sorted(all_specialties)}")
    else:
        raise FileNotFoundError(f"找不到診所資料檔案: {CLINIC_DATA_PATH}")

@app.on_event("startup")
async def startup_event():
    """應用程式啟動時載入資料"""
    try:
        print("開始載入資料...")
        load_and_process_data()
        print("資料載入完成！")
    except Exception as e:
        print(f"資料載入失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

@app.get("/")
async def root():
    """根路徑"""
    return {"message": "台灣地圖 API 服務運行中"}

@app.get("/api/counties")
async def get_counties():
    """返回全台灣縣市的 GeoJSON 資料"""
    if county_data is None:
        raise HTTPException(status_code=500, detail="縣市資料尚未載入")
    
    # 轉換為 GeoJSON 格式
    counties_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    for _, row in county_data.iterrows():
        # 確保幾何資料的座標順序正確 [longitude, latitude]
        geometry = row['geometry']
        
        # Debug: 輸出座標值確認
        county_name = row.get('COUNTYNAME', row.get('name', '未知縣市'))
        center_lat_val = row['center_lat']
        center_lon_val = row['center_lon']
        print(f"API 返回 {county_name}: center_lat={center_lat_val}, center_lon={center_lon_val}")
        
        feature = {
            "type": "Feature",
            "properties": {
                "name": county_name,
                "center_lat": center_lat_val,
                "center_lon": center_lon_val
            },
            "geometry": mapping(geometry)
        }
        counties_geojson["features"].append(feature)
    
    return counties_geojson

@app.get("/api/villages/{county_name}")
async def get_villages(county_name: str, income_weight: float = 0.5, density_weight: float = 0.5):
    """返回指定縣市的所有村里 GeoJSON 資料（包含薪資和人口密度）"""
    if village_data is None or village_salary_mapping is None or village_population_mapping is None:
        raise HTTPException(status_code=500, detail="村里資料尚未載入")
    

    
    # 篩選該縣市的村里
    county_villages = village_data[village_data['COUNTYNAME'] == county_name].copy()
    
    if county_villages.empty:
        raise HTTPException(status_code=404, detail=f"找不到縣市: {county_name}")
    
    # 計算該縣市村里的中位數分級和人口密度分級
    county_village_incomes = []
    county_village_densities = []
    village_income_mapping = {}  # 儲存每個村里的收入
    village_density_mapping = {}  # 儲存每個村里的人口密度
    
    for _, row in county_villages.iterrows():
        village_name = row.get('VILLNAME', row.get('name', '未知村里'))
        district_name = row.get('TOWNNAME', '未知區')
        
        # 直接使用標準化資料進行對應
        key = f"{county_name}_{district_name}_{village_name}"
        
        # 處理薪資資料
        median_income = None
        if key in village_salary_mapping:
            median_income = village_salary_mapping[key]['median_income']
        
        # 處理人口密度資料
        population_density = None
        if key in village_population_mapping:
            population_density = village_population_mapping[key]['population_density']
        
        # 儲存每個村里的資料（沒有數據的設為None）
        village_key = f"{village_name}_{district_name}"
        village_income_mapping[village_key] = median_income
        village_density_mapping[village_key] = population_density
        
        if median_income is not None:
            county_village_incomes.append(median_income)
        if population_density is not None:
            county_village_densities.append(population_density)
    
    # 計算薪資九等分分級
    income_ranges = []
    if county_village_incomes:
        try:
            income_levels = pd.qcut(county_village_incomes, q=9, labels=False, duplicates='drop')
            income_levels = [int(level) for level in income_levels]
            
            # 確保長度匹配
            if len(income_levels) != len(county_village_incomes):
                print(f"警告：薪資等級數量 {len(income_levels)} 與收入數量 {len(county_village_incomes)} 不匹配")
                income_levels = [0] * len(county_village_incomes)  # 使用預設值
            
            # 計算每個等級的薪資範圍
            unique_levels = sorted(set(income_levels))
            
            for level in unique_levels:
                level_incomes = [county_village_incomes[j] for j, l in enumerate(income_levels) if l == level]
                if level_incomes:
                    min_income = min(level_incomes)
                    max_income = max(level_incomes)
                    income_ranges.append({
                        'level': level,
                        'min': min_income,
                        'max': max_income
                    })
            
            # 確保有9個等級（補齊缺失的等級）
            while len(income_ranges) < 9:
                income_ranges.append({
                    'level': len(income_ranges),
                    'min': 0,
                    'max': 0
                })
                
        except Exception as e:
            print(f"薪資分級計算錯誤: {e}")
            income_levels = [0] * len(county_village_incomes)
            income_ranges = [{'level': i, 'min': 0, 'max': 0} for i in range(9)]
    else:
        income_levels = [0] * len(county_villages)
        income_ranges = []
    
    # 計算人口密度九等分分級
    density_ranges = []
    if county_village_densities:
        try:
            density_levels = pd.qcut(county_village_densities, q=9, labels=False, duplicates='drop') 
            density_levels = [int(level) for level in density_levels]
            
            # 確保長度匹配
            if len(density_levels) != len(county_village_densities):
                print(f"警告：人口密度等級數量 {len(density_levels)} 與密度數量 {len(county_village_densities)} 不匹配")
                density_levels = [0] * len(county_village_densities)
            
            # 計算每個等級的人口密度範圍
            unique_levels = sorted(set(density_levels))
            
            for level in unique_levels:
                level_densities = [county_village_densities[j] for j, l in enumerate(density_levels) if l == level]
                if level_densities:
                    min_density = min(level_densities)
                    max_density = max(level_densities)
                    density_ranges.append({
                        'level': level,
                        'min': min_density,
                        'max': max_density
                    })
            
            # 確保有9個等級
            while len(density_ranges) < 9:
                density_ranges.append({
                    'level': len(density_ranges),
                    'min': 0,
                    'max': 0
                })
                
        except Exception as e:
            print(f"人口密度分級計算錯誤: {e}")
            density_levels = [0] * len(county_village_densities)
            density_ranges = [{'level': i, 'min': 0, 'max': 0} for i in range(9)]
    else:
        density_levels = [0] * len(county_villages)
        density_ranges = []
    
    # 轉換為 GeoJSON 格式
    villages_geojson = {
        "type": "FeatureCollection",
        "features": [],
        "income_ranges": income_ranges,
        "density_ranges": density_ranges
    }
    
    for _, row in county_villages.iterrows():
        village_name = row.get('VILLNAME', row.get('name', '未知村里'))
        district_name = row.get('TOWNNAME', '未知區')
        
        # 取得該村里的收入和人口密度
        village_key = f"{village_name}_{district_name}"
        median_income = village_income_mapping.get(village_key)
        population_density = village_density_mapping.get(village_key)
        
        # 計算收入等級
        income_level = 0
        if median_income is not None and county_village_incomes:
            try:
                # 使用簡單的百分位數計算，避免重複pd.qcut
                sorted_incomes = sorted(county_village_incomes)
                n = len(sorted_incomes)
                for level in range(9):
                    threshold_idx = int((level + 1) * n / 9) - 1
                    if threshold_idx < n and median_income <= sorted_incomes[threshold_idx]:
                        income_level = level
                        break
                else:
                    income_level = 8  # 最高等級
            except:
                income_level = 0
                
        # 計算人口密度等級
        density_level = 0
        if population_density is not None and county_village_densities:
            try:
                sorted_densities = sorted(county_village_densities)
                n = len(sorted_densities)
                for level in range(9):
                    threshold_idx = int((level + 1) * n / 9) - 1
                    if threshold_idx < n and population_density <= sorted_densities[threshold_idx]:
                        density_level = level
                        break
                else:
                    density_level = 8  # 最高等級
            except:
                density_level = 0
        
        # 使用預先計算的中心點
        center_lat = row.get('center_lat', row['geometry'].centroid.y)
        center_lon = row.get('center_lon', row['geometry'].centroid.x)
        
        # 計算雙變數顏色
        bivariate_color = get_bivariate_color(income_level, density_level, income_weight, density_weight)
        
        feature = {
            "type": "Feature",
            "properties": {
                "name": village_name,
                "county": county_name,
                "district": district_name,
                "center_lat": float(center_lat),
                "center_lon": float(center_lon),
                "income_level": income_level,
                "density_level": density_level,
                "median_income": median_income,
                "population_density": population_density,
                "area_km2": float(row.get('area_km2', 0)),
                "bivariate_color": bivariate_color
            },
            "geometry": mapping(row['geometry'])
        }
        villages_geojson["features"].append(feature)
    
    return villages_geojson

@app.get("/api/village_salary/{village_name}")
async def get_village_salary(village_name: str, county_name: Optional[str] = None, district_name: Optional[str] = None):
    """返回指定村里所有年份的薪資資料（使用標準化資料）"""
    print(f"API 請求: village_name={village_name}, county_name={county_name}, district_name={district_name}")
    
    if salary_data is None:
        raise HTTPException(status_code=500, detail="薪資資料尚未載入")
    
    # 篩選該村里的所有年份資料（直接使用標準化資料）
    if county_name and district_name:
        # 精確匹配縣市、區、村里
        print(f"精確匹配: {county_name} {district_name} {village_name}")
        village_salary = salary_data[
            (salary_data['村里'] == village_name) & 
            (salary_data['縣市'] == county_name) &
            (salary_data['鄉鎮市區'] == district_name)
        ]
        print(f"精確匹配結果筆數: {len(village_salary)}")
        
        # 如果精確匹配失敗，顯示該村里在該縣市的所有可能區域
        if village_salary.empty:
            possible_districts = salary_data[
                (salary_data['村里'] == village_name) & 
                (salary_data['縣市'] == county_name)
            ]['鄉鎮市區'].unique()
            print(f"該村里在 {county_name} 的可能區域: {list(possible_districts)}")
            print(f"前端傳送的區域: {district_name}")
            
            # 嘗試模糊匹配
            if len(possible_districts) == 1:
                actual_district = possible_districts[0]
                print(f"嘗試使用實際區域: {actual_district}")
                village_salary = salary_data[
                    (salary_data['村里'] == village_name) & 
                    (salary_data['縣市'] == county_name) &
                    (salary_data['鄉鎮市區'] == actual_district)
                ]
                print(f"模糊匹配結果筆數: {len(village_salary)}")
    elif county_name:
        # 只匹配縣市和村里
        village_salary = salary_data[
            (salary_data['村里'] == village_name) & 
            (salary_data['縣市'] == county_name)
        ]
    else:
        # 只用村里名稱搜尋
        village_salary = salary_data[salary_data['村里'] == village_name]
    
    if village_salary.empty:
        if district_name:
            raise HTTPException(status_code=404, detail=f"找不到村里: {county_name}{district_name}{village_name}")
        elif county_name:
            raise HTTPException(status_code=404, detail=f"找不到村里: {county_name}{village_name}")
        else:
            raise HTTPException(status_code=404, detail=f"找不到村里: {village_name}")
    
    # 整理資料格式
    result = []
    for _, row in village_salary.iterrows():
        result.append({
            "年份": int(row['年份']),
            "縣市": row['縣市'],
            "區": row['鄉鎮市區'],
            "村里": row['村里'],
            "綜合所得總額": float(row['綜合所得總額']),
            "平均數": float(row['平均數']),
            "中位數": float(row['中位數'])
        })
    
    # 按年份排序
    result.sort(key=lambda x: x['年份'])
    
    return result

@app.get("/api/village_population/{village_name}")
async def get_village_population(village_name: str, county_name: Optional[str] = None, district_name: Optional[str] = None):
    """返回指定村里所有年份的人口資料"""
    print(f"人口API 請求: village_name={village_name}, county_name={county_name}, district_name={district_name}")
    
    if population_data is None:
        raise HTTPException(status_code=500, detail="人口資料尚未載入")
    
    # 載入所有可用的人口資料檔案
    all_population_data = []
    population_files = list(POPULATION_DATA_DIR.glob("*_standardized.csv"))
    
    for file_path in population_files:
        # 從檔案名稱中提取年份和月份
        filename = file_path.stem  # 例如: opendata11407M030_standardized
        if 'opendata' in filename:
            year_month = filename.split('opendata')[1].split('_')[0]  # 11407M030
            if len(year_month) >= 5:
                year_str = year_month[:3]  # 114
                month_str = year_month[3:5]  # 07
                
                # 轉換民國年為西元年
                try:
                    year = int(year_str) + 1911  # 114 + 1911 = 2025
                    month = int(month_str)
                    
                    df = pd.read_csv(file_path)
                    df['年份'] = year
                    df['月份'] = month
                    all_population_data.append(df)
                except ValueError:
                    continue
    
    if not all_population_data:
        raise HTTPException(status_code=500, detail="無法載入人口資料檔案")
    
    # 合併所有年份資料
    combined_population = pd.concat(all_population_data, ignore_index=True)
    
    # 篩選該村里的資料
    if county_name and district_name:
        village_population = combined_population[
            (combined_population['村里'] == village_name) & 
            (combined_population['縣市'] == county_name) &
            (combined_population['鄉鎮市區'] == district_name)
        ]
    elif county_name:
        village_population = combined_population[
            (combined_population['村里'] == village_name) & 
            (combined_population['縣市'] == county_name)
        ]
    else:
        village_population = combined_population[combined_population['村里'] == village_name]
    
    if village_population.empty:
        if district_name:
            raise HTTPException(status_code=404, detail=f"找不到人口資料: {county_name}{district_name}{village_name}")
        elif county_name:
            raise HTTPException(status_code=404, detail=f"找不到人口資料: {county_name}{village_name}")
        else:
            raise HTTPException(status_code=404, detail=f"找不到人口資料: {village_name}")
    
    # 整理資料格式
    result = []
    for _, row in village_population.iterrows():
        result.append({
            "年份": int(row['年份']),
            "月份": int(row['月份']),
            "統計年月": f"{row['年份']}/{row['月份']:02d}",
            "縣市": row['縣市'],
            "區": row['鄉鎮市區'],
            "村里": row['村里'],
            "戶數": int(row['戶數']),
            "人口數": int(row['人口數'])
        })
    
    # 按年份和月份排序
    result.sort(key=lambda x: (x['年份'], x['月份']))
    
    return result

@app.get("/api/bivariate_colors")
async def get_bivariate_colors(income_weight: float = 0.5, density_weight: float = 0.5):
    """返回雙變數色彩矩陣"""
    color_matrix = []
    for income_level in range(9):
        row = []
        for density_level in range(9):
            color = get_bivariate_color(income_level, density_level, income_weight, density_weight)
            row.append(color)
        color_matrix.append(row)
    
    return {
        "color_matrix": color_matrix,
        "income_weight": income_weight,
        "density_weight": density_weight,
        "dimensions": {
            "income_levels": 9,
            "density_levels": 9
        }
    }

@app.get("/api/clinics/{county_name}")
async def get_clinics(county_name: str, specialties: Optional[str] = None):
    """返回指定縣市的診所地標資料"""
    if clinic_data is None:
        raise HTTPException(status_code=500, detail="診所資料尚未載入")
    
    # 篩選該縣市的診所
    county_clinics = clinic_data[clinic_data['縣市'] == county_name].copy()
    
    if county_clinics.empty:
        return {"type": "FeatureCollection", "features": []}
    
    # 處理科別篩選
    if specialties:
        requested_specialties = set([s.strip() for s in specialties.split(',')])
        
        # 篩選包含指定科別的診所
        filtered_clinics = []
        for _, clinic in county_clinics.iterrows():
            clinic_specialties = clinic['標準科別']
            if clinic_specialties and clinic_specialties.intersection(requested_specialties):
                filtered_clinics.append(clinic)
        
        county_clinics = pd.DataFrame(filtered_clinics)
        
        if county_clinics.empty:
            return {"type": "FeatureCollection", "features": []}
    
    # 依據機構名稱和地址去重，避免同一診所重複標記
    county_clinics = county_clinics.drop_duplicates(subset=['機構名稱', '地址'])
    
    # 轉換為 GeoJSON 格式
    clinics_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    for _, clinic in county_clinics.iterrows():
        # 將科別集合轉為列表以便JSON序列化
        specialties_list = list(clinic['標準科別']) if clinic['標準科別'] else []
        
        feature = {
            "type": "Feature",
            "properties": {
                "name": clinic['機構名稱'],
                "address": clinic['地址'],
                "specialties": specialties_list,
                "original_specialty": clinic['科別']  # 保留原始科別資訊
            },
            "geometry": {
                "type": "Point",
                "coordinates": [float(clinic['經度']), float(clinic['緯度'])]
            }
        }
        clinics_geojson["features"].append(feature)
    
    return clinics_geojson

@app.get("/api/clinic_specialties")
async def get_clinic_specialties():
    """返回所有可用的診所科別"""
    if clinic_data is None:
        raise HTTPException(status_code=500, detail="診所資料尚未載入")
    
    # 收集所有標準化科別
    all_specialties = set()
    for specialty_set in clinic_data['標準科別']:
        if specialty_set:
            all_specialties.update(specialty_set)
    
    # 定義科別顯示順序和圖標 (根據用戶指定的優先級)
    specialty_config = {
        '耳鼻喉科': {'order': 1, 'icon': '🔴'},
        '家庭醫學科': {'order': 2, 'icon': '🏠'},
        '兒科': {'order': 3, 'icon': '🍼'},
        '內科': {'order': 4, 'icon': '💊'},
        '醫美整形科': {'order': 5, 'icon': '⭐'},
        '眼科': {'order': 6, 'icon': '👁️'},
        '婦產科': {'order': 7, 'icon': '♀️'},
        '泌尿科': {'order': 8, 'icon': '♂️'},
        '復健科': {'order': 9, 'icon': '💪'},
        '骨科': {'order': 10, 'icon': '🦴'},
        '外科': {'order': 11, 'icon': '✂️'},
        '神經科': {'order': 12, 'icon': '🧠'},
        '精神科': {'order': 13, 'icon': '🤗'},
        '牙科': {'order': 14, 'icon': '🦷'},
        '中醫': {'order': 15, 'icon': '🌿'},
        '其他': {'order': 99, 'icon': '🏥'}
    }
    
    # 構建返回資料
    specialties_data = []
    for specialty in sorted(all_specialties):
        config = specialty_config.get(specialty, {'order': 99, 'icon': '🏥'})
        specialties_data.append({
            'name': specialty,
            'order': config['order'],
            'icon': config['icon']
        })
    
    # 按順序排序
    specialties_data.sort(key=lambda x: (x['order'], x['name']))
    
    return {
        "specialties": specialties_data,
        "total_count": len(specialties_data)
    }

@app.get("/api/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "county_data_loaded": county_data is not None,
        "village_data_loaded": village_data is not None,
        "salary_data_loaded": salary_data is not None,
        "population_data_loaded": population_data is not None,
        "clinic_data_loaded": clinic_data is not None,
        "salary_mappings": len(village_salary_mapping) if village_salary_mapping else 0,
        "population_mappings": len(village_population_mapping) if village_population_mapping else 0,
        "clinic_count": len(clinic_data) if clinic_data is not None else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
