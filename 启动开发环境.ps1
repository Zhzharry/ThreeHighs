$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未找到 Docker。请先安装并启动 Docker Desktop，然后重新运行本脚本。"
}

try {
    docker info *> $null
} catch {
    throw "Docker Desktop 尚未启动，或当前用户无法访问 Docker Engine。"
}

if (-not $env:DOCKER_BASE_REGISTRY) {
    $env:DOCKER_BASE_REGISTRY = "public.ecr.aws/docker/library"
}

Write-Host "正在检查 Docker Compose 配置..." -ForegroundColor Cyan
docker compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose 配置检查失败。"
}

Write-Host "正在构建并启动 MySQL、Redis、后端 API 和前端预览..." -ForegroundColor Cyan
docker compose up -d --build mysql redis backend-api frontend-preview
if ($LASTEXITCODE -ne 0) {
    throw "Docker 服务启动失败，请查看上方输出。"
}

$healthUrl = "http://127.0.0.1:5000/api/v1/health"
$ready = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
        if ($response.code -eq 0 -and $response.data.status -eq "ready") {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

docker compose ps

if (-not $ready) {
    throw "容器已启动，但后端在 60 秒内没有进入 ready。请运行 docker compose logs backend-api 查看原因。"
}

Write-Host ""
Write-Host "启动成功" -ForegroundColor Green
Write-Host "前端预览页面：http://127.0.0.1:8088/"
Write-Host "后端健康检查：$healthUrl"
Write-Host ""
Write-Host "网页预览用于快速看界面和联调；微信小程序真机/模拟器请在微信开发者工具中导入当前目录并点击编译。" -ForegroundColor Yellow
Write-Host "没有原 AppID 成员权限时，请改用测试号或自己的 AppID。" -ForegroundColor Yellow
