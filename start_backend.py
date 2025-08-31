#!/usr/bin/env python3
"""
台灣地圖應用程式後端啟動腳本
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """檢查 Python 版本"""
    if sys.version_info < (3, 8):
        print("錯誤: 需要 Python 3.8 或更高版本")
        print(f"當前版本: {sys.version}")
        return False
    return True

def install_requirements():
    """安裝依賴套件"""
    print("正在檢查並安裝依賴套件...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✓ 依賴套件安裝完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依賴套件安裝失敗: {e}")
        return False

def start_backend():
    """啟動後端服務"""
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("錯誤: 找不到 backend 目錄")
        return False
    
    print("正在啟動後端服務...")
    print("服務將在 http://localhost:8000 啟動")
    print("按 Ctrl+C 停止服務")
    print("-" * 50)
    
    try:
        # 從項目根目錄啟動後端服務
        main_py_path = backend_dir / "main.py"
        subprocess.run([sys.executable, str(main_py_path)])
    except KeyboardInterrupt:
        print("\n服務已停止")
    except Exception as e:
        print(f"啟動服務時發生錯誤: {e}")
        return False
    
    return True

def main():
    """主函數"""
    print("台灣地圖應用程式 - 後端啟動器")
    print("=" * 50)
    
    # 檢查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 安裝依賴套件
    if not install_requirements():
        sys.exit(1)
    
    # 啟動後端服務
    start_backend()

if __name__ == "__main__":
    main() 