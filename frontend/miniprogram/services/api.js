const runtimeConfig = require("../config/index")

function apiBaseUrl() {
  return runtimeConfig.getApiBaseUrl()
}

function requestId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function normalizeError(error, fallbackMessage = "网络连接失败，请稍后重试") {
  if (error instanceof Error) return error
  const message = error && (error.errMsg || error.message)
  const normalized = new Error(message || fallbackMessage)
  normalized.cause = error
  return normalized
}

function authHeader() {
  const token = wx.getStorageSync("access_token")
  return token ? { Authorization: `Bearer ${token}` } : {}
}

let loginTask = null

function ensureLogin() {
  const token = wx.getStorageSync("access_token")
  if (token) return Promise.resolve(token)
  if (loginTask) return loginTask
  loginTask = new Promise((resolve, reject) => {
    wx.login({
      success: ({ code }) => {
        let url
        try {
          url = `${apiBaseUrl()}/auth/wechat-login`
        } catch (error) {
          reject(error)
          return
        }
        wx.request({
          url,
          method: "POST",
          data: { code },
          timeout: runtimeConfig.REQUEST_TIMEOUT,
          header: { "X-Request-ID": requestId() },
          success: ({ statusCode, data }) => {
            if (statusCode >= 200 && statusCode < 300 && data.code === 0 && data.data && data.data.token) {
              wx.setStorageSync("access_token", data.data.token)
              resolve(data.data.token)
            } else {
              const error = new Error((data && data.message) || "登录失败")
              error.statusCode = statusCode
              reject(error)
            }
          },
          fail: (error) => reject(normalizeError(error, "登录服务暂时不可用"))
        })
      },
      fail: (error) => reject(normalizeError(error, "无法获取微信登录凭证"))
    })
  }).finally(() => { loginTask = null })
  return loginTask
}

function request(path, options = {}, canRetryAuth = true) {
  if (path !== "/auth/wechat-login" && !wx.getStorageSync("access_token")) {
    return ensureLogin().then(() => request(path, options, false))
  }
  let url
  try {
    url = `${apiBaseUrl()}${path}`
  } catch (error) {
    return Promise.reject(error)
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method: options.method || "GET",
      data: options.data || {},
      timeout: options.timeout || runtimeConfig.REQUEST_TIMEOUT,
      header: {
        "content-type": "application/json",
        "X-Request-ID": requestId(),
        ...authHeader(),
        ...(options.header || {})
      },
      success(response) {
        if (response.statusCode === 401) {
          wx.removeStorageSync("access_token")
          if (path !== "/auth/wechat-login" && canRetryAuth) {
            ensureLogin().then(
              () => request(path, options, false).then(resolve, reject),
              reject
            )
            return
          }
        }
        resolve(response.data)
      },
      fail(error) {
        reject(normalizeError(error))
      }
    })
  })
}

function upload(path, filePath, formData = {}, canRetryAuth = true) {
  if (!wx.getStorageSync("access_token")) {
    return ensureLogin().then(() => upload(path, filePath, formData, false))
  }
  let url
  try {
    url = `${apiBaseUrl()}${path}`
  } catch (error) {
    return Promise.reject(error)
  }
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url,
      filePath,
      name: "file",
      formData,
      timeout: runtimeConfig.UPLOAD_TIMEOUT,
      header: { ...authHeader(), "X-Request-ID": requestId() },
      success(response) {
        if (response.statusCode === 401) {
          wx.removeStorageSync("access_token")
          if (canRetryAuth) {
            ensureLogin().then(
              () => upload(path, filePath, formData, false).then(resolve, reject),
              reject
            )
            return
          }
        }
        try {
          resolve(JSON.parse(response.data))
        } catch (error) {
          reject(normalizeError(error, "服务器返回了无法识别的上传结果"))
        }
      },
      fail(error) {
        reject(normalizeError(error, "文件上传失败，请检查网络后重试"))
      }
    })
  })
}

module.exports = {
  ensureLogin,
  getRuntimeConfig: () => ({ envVersion: runtimeConfig.ENV_VERSION, apiBaseUrl: apiBaseUrl() }),
  login: (data) => request("/auth/wechat-login", { method: "POST", data }),
  getTodayRecord: () => request("/daily-records/today"),
  getDailyRecord: (date) => request(`/daily-records?date=${date}`),
  createDailyRecord: (date) => request("/daily-records", { method: "POST", data: { date } }),
  getCalendarMarks: (month) => request(`/daily-records/calendar?month=${month}`),
  updateDailyRecord: (recordId, data) => request(`/daily-records/${recordId}`, { method: "PATCH", data }),
  updateVitals: (recordId, data) => request(`/daily-records/${recordId}/vitals`, { method: "PATCH", data }),
  getDailyTasks: (recordId) => request(`/daily-records/${recordId}/tasks`),
  updateDailyTask: (taskId, data) => request(`/daily-tasks/${taskId}`, { method: "PATCH", data }),
  getTaskTemplate: (date) => request(`/daily-task-templates/current?date=${date}`),
  updateTaskTemplate: (data) => request("/daily-task-templates/current", { method: "PUT", data }),
  getMeals: (recordId) => request(`/daily-records/${recordId}/meals`),
  addMeal: (recordId, data) => request(`/daily-records/${recordId}/meals`, { method: "POST", data }),
  updateMeal: (mealId, data) => request(`/meals/${mealId}`, { method: "PUT", data }),
  deleteMeal: (mealId) => request(`/meals/${mealId}`, { method: "DELETE" }),
  getVitalsTrend: (range = "7d") => request(`/trends/vitals?range=${range}`),
  getVitalsPrediction: (days = 7) => request(`/predictions/vitals?days=${days}`),
  getAlerts: (date) => request(`/alerts?date=${date}`),
  markAlertRead: (alertId) => request(`/alerts/${alertId}/read`, { method: "PATCH" }),
  uploadReport: (filePath, source, reportDate) => upload("/reports/upload", filePath, {
    source,
    report_date: reportDate
  }),
  getReportHistory: () => request("/reports/history"),
  getReportDetail: (reportId) => request(`/reports/${reportId}`),
  startReportRecognize: (reportId) => request(`/reports/${reportId}/recognize`, { method: "POST" }),
  getReportProgress: (reportId) => request(`/reports/${reportId}/progress`),
  getReportIndicators: (reportId) => request(`/reports/${reportId}/indicators`),
  updateReportIndicators: (reportId, items) => request(`/reports/${reportId}/indicators`, { method: "PUT", data: { items } }),
  confirmReport: (reportId, reviewNote = "") => request(`/reports/${reportId}`, { method: "PATCH", data: { action: "confirm", review_note: reviewNote } }),
  deleteReport: (reportId) => request(`/reports/${reportId}`, { method: "DELETE" }),
  getQuickQuestions: () => request("/ai/quick-questions"),
  getAiContextToday: (date) => request(`/ai/context/today?date=${date}`),
  getAiConversations: () => request("/ai/conversations"),
  createAiConversation: (data) => request("/ai/conversations", { method: "POST", data }),
  getAiMessages: (conversationId) => request(`/ai/conversations/${conversationId}/messages`),
  sendAiMessage: (conversationId, data) => request(`/ai/conversations/${conversationId}/messages`, { method: "POST", data }),
  getMineProfile: () => request("/me/profile"),
  updateMineProfile: (data) => request("/me/profile", { method: "PUT", data }),
  uploadMineAvatar: (filePath) => upload("/me/avatar", filePath),
  deleteMineAvatar: () => request("/me/avatar", { method: "DELETE" }),
  updateHealthProfile: (data) => request("/me/health-profile", { method: "PUT", data }),
  getSettings: () => request("/me/settings"),
  updateSettings: (data) => request("/me/settings", { method: "PUT", data }),
  getConsents: () => request("/me/consents"),
  acceptConsents: (data) => request("/me/consents", { method: "PUT", data }),
  withdrawHealthConsent: () => request("/me/consents/withdraw", { method: "POST", data: { confirmation: "撤回授权" } }),
  exportMyData: () => request("/me/data-export", { timeout: runtimeConfig.UPLOAD_TIMEOUT }),
  getAdminDashboard: () => request("/admin/dashboard")
}
