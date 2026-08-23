const API_ORIGINS = {
  develop: "http://127.0.0.1:5000",
  trial: "",
  release: ""
}

function getEnvVersion() {
  try {
    const accountInfo = wx.getAccountInfoSync()
    return accountInfo.miniProgram.envVersion || "develop"
  } catch (_error) {
    return "develop"
  }
}

const ENV_VERSION = getEnvVersion()

function getApiBaseUrl() {
  const origin = String(API_ORIGINS[ENV_VERSION] || "").replace(/\/$/, "")
  if (!origin) {
    throw new Error(`尚未配置 ${ENV_VERSION} 环境的后端 API 地址`)
  }
  return `${origin}/api/v1`
}

module.exports = {
  ENV_VERSION,
  API_ORIGINS,
  getApiBaseUrl,
  REQUEST_TIMEOUT: 12000,
  UPLOAD_TIMEOUT: 60000
}
