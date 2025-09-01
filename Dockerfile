# 使用 Python 3.11 官方映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements 檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 設定 Git LFS（如果需要）
RUN git lfs install

# 暴露端口
EXPOSE 8080

# 設定環境變數
ENV PORT=8080
ENV PYTHONPATH=/app

# 啟動命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
