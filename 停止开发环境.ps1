$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot
docker compose down

if ($LASTEXITCODE -ne 0) {
    throw "Docker 服务停止失败，请检查 Docker Desktop 状态。"
}

Write-Host "服务已停止，MySQL、Redis 和上传文件卷均已保留。" -ForegroundColor Green
Write-Host "如需连同数据一起删除，必须人工确认后执行 docker compose down -v。" -ForegroundColor Yellow
