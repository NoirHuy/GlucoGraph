# Script tự động đóng gói và deploy GlucoGraph CDSS lên Hugging Face Spaces
# Chạy script bằng PowerShell tại thư mục gốc của dự án

$token = Read-Host -Prompt "Nhập Hugging Face Access Token của bạn (loại Write)"
if (-not $token) {
    Write-Error "Access Token không được để trống!"
    exit
}

Write-Host "1. Đang tạo thư mục tạm 'hf_deploy'..." -ForegroundColor Green
if (Test-Path hf_deploy) {
    Remove-Item -Recurse -Force hf_deploy
}
New-Item -ItemType Directory -Force -Path hf_deploy | Out-Null

Write-Host "2. Đang sao chép các file cần thiết (chỉ copy backend, frontend và Dockerfile)..." -ForegroundColor Green
Copy-Item -Recurse -Force backend hf_deploy/
Copy-Item -Recurse -Force frontend-CDSS hf_deploy/
Copy-Item -Force Dockerfile hf_deploy/

# Tạo file .gitignore cho thư mục deploy để loại bỏ các file rác
@'
node_modules/
.venv/
__pycache__/
*.pyc
.env
'@ | Out-File -FilePath hf_deploy/.gitignore -Encoding utf8

# Tạo file README.md chứa YAML Metadata cấu hình Docker Space cho Hugging Face
@'
---
title: GlucoGraph CDSS
emoji: 🩺
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# GlucoGraph - Clinical Decision Support System (CDSS)
Triển khai trực tuyến trên Hugging Face Spaces sử dụng Docker.
'@ | Out-File -FilePath hf_deploy/README.md -Encoding utf8


Write-Host "3. Đang khởi tạo Git trong thư mục deploy..." -ForegroundColor Green
cd hf_deploy
git init -b main
git add .
git commit -m "Deploy GlucoGraph CDSS to Hugging Face Spaces"

Write-Host "4. Đang push code lên Hugging Face..." -ForegroundColor Green
git remote add hf "https://NoirHuy:$token@huggingface.co/spaces/NoirHuy/glucologic-cdss"
git push hf main --force

Write-Host "5. Đang dọn dẹp thư mục tạm..." -ForegroundColor Green
cd ..
Remove-Item -Recurse -Force hf_deploy

Write-Host "Triển khai hoàn tất! Hãy truy cập https://huggingface.co/spaces/NoirHuy/glucologic-cdss để xem trạng thái build." -ForegroundColor Cyan
