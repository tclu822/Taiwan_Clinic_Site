#!/usr/bin/env python3
"""
台灣地圖應用程式前端啟動腳本
"""

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """支援 CORS 的 HTTP 請求處理器"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def start_frontend_server():
    """啟動前端 HTTP 伺服器"""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("錯誤: 找不到 frontend 目錄")
        return False
    
    # 檢查必要文件
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        print("錯誤: 找不到 index.html 檔案")
        return False
    
    print(f"前端目錄: {frontend_dir.absolute()}")
    print(f"工作目錄: {os.getcwd()}")
    
    # 切換到前端目錄
    os.chdir(frontend_dir)
    print(f"切換後工作目錄: {os.getcwd()}")
    
    # 設定伺服器
    port = 8080
    server_address = ('127.0.0.1', port)  # 明確指定IP
    
    try:
        httpd = HTTPServer(server_address, CORSRequestHandler)
        print(f"前端服務已啟動: http://127.0.0.1:{port}")
        print("按 Ctrl+C 停止服務")
        print("-" * 50)
        
        # 在瀏覽器中開啟應用程式（清除快取）
        def open_browser():
            time.sleep(2)  # 等待伺服器啟動
            
            # 添加時間戳參數來避免快取
            timestamp = int(time.time())
            url_with_timestamp = f'http://127.0.0.1:{port}?t={timestamp}'
            
            # 嘗試使用 Microsoft Edge 無痕模式開啟
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
            ]
            
            edge_found = False
            for edge_path in edge_paths:
                if os.path.exists(edge_path):
                    try:
                        # 使用 Edge 無痕模式和禁用快取參數
                        subprocess.run([
                            edge_path,
                            "--inprivate",  # Edge 的無痕模式參數
                            "--disable-web-security",
                            "--disable-features=VizDisplayCompositor",
                            "--force-refresh",
                            "--no-first-run",
                            "--disable-background-timer-throttling",
                            url_with_timestamp
                        ], check=False)
                        edge_found = True
                        print(f"已在 Microsoft Edge 無痕模式開啟: {url_with_timestamp}")
                        break
                    except Exception as e:
                        print(f"嘗試啟動 Edge 失敗: {e}")
                        continue
            
            # 如果找不到 Edge，使用預設瀏覽器
            if not edge_found:
                webbrowser.open(url_with_timestamp)
                print(f"已在預設瀏覽器開啟: {url_with_timestamp}")
                print("建議手動清除瀏覽器快取或使用無痕模式")
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        # 啟動伺服器
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n前端服務已停止")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"錯誤: 端口 {port} 已被佔用")
        else:
            print(f"網絡錯誤: {e}")
        return False
    except Exception as e:
        print(f"啟動前端服務時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """主函數"""
    print("台灣地圖應用程式 - 前端啟動器")
    print("=" * 50)
    print("注意: 請確保後端服務已在 http://localhost:8000 運行")
    print("-" * 50)
    
    # 啟動前端服務
    start_frontend_server()

if __name__ == "__main__":
    main() 