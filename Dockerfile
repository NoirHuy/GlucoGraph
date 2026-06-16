# Stage 1: Build React Frontend
FROM node:18 AS builder
WORKDIR /app/frontend
COPY frontend-CDSS/package*.json ./
RUN npm install
COPY frontend-CDSS/ ./
RUN npm run build

# Stage 2: Python FastAPI Backend
FROM python:3.11-slim
WORKDIR /app

# Cài đặt thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt dependencies Python
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn backend
COPY backend/ ./

# Sao chép bản build của frontend vào thư mục dist để FastAPI phục vụ tĩnh
COPY --from=builder /app/frontend/dist ./dist

# Hugging Face Spaces mặc định expose cổng 7860
ENV PORT=7860
EXPOSE 7860

# Chạy FastAPI backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
