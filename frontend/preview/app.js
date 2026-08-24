const API_BASE_URL = "http://localhost:5000/api/v1"

const tabs = Array.from(document.querySelectorAll(".tabbar button"))
const pages = Array.from(document.querySelectorAll(".page"))
const topbarStatus = document.querySelector(".topbar span")
const calendarTriggers = Array.from(document.querySelectorAll(".calendar-trigger"))
const bigCalendarPreview = document.querySelector(".big-calendar-preview")
const monthPreviewButtons = Array.from(document.querySelectorAll(".month-preview-grid button"))
const profileSaveButton = document.querySelector(".profile-save-preview")
const dropzonePreview = document.querySelector(".dropzone-preview")
const choicePanel = document.querySelector(".choice-panel")
const choiceButtons = Array.from(document.querySelectorAll(".choice-panel button"))
const startOcrButton = document.querySelector(".start-ocr-preview")
const progressFill = document.querySelector(".progress-fill")
const progressLabel = document.querySelector(".progress-label")
const progressText = document.querySelector(".progress-text")

let currentRecordId = null
let currentReportId = null
let currentReportDetail = null
let reportEditMode = false
let webTrendChart = null
let webTrendRange = "7d"
let currentConversationId = null
let selectedDate = ""
let progressTimer = null
let taskSyncTimer = null
let accessToken = sessionStorage.getItem("access_token") || ""
let loginPromise = null
const WECHAT_PROFILE_PROMPT_KEY = "preview_wechat_profile_prompted"
let accountProfileState = {
  saved: { nickname: "李明", phone: "13800000926", avatarUrl: "" },
  current: { nickname: "李明", phone: "13800000926", avatarUrl: "" },
  avatarFile: null,
  avatarRemoved: false
}
let healthProfileState = {
  saved: [],
  current: []
}

function maskPhone(phone) {
  const value = String(phone || "")
  return value.length === 11 ? `${value.slice(0, 3)}****${value.slice(-4)}` : value || "未填写"
}

function setApiStatus(text, connected = true) {
  if (!topbarStatus) return
  topbarStatus.textContent = text
  topbarStatus.style.color = connected ? "rgba(255,255,255,0.82)" : "#fee2e2"
}

async function ensureLogin() {
  if (accessToken) return accessToken
  if (loginPromise) return loginPromise
  loginPromise = fetch(`${API_BASE_URL}/auth/wechat-login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ code: "browser-preview", nickname: "浏览器演示用户" })
  }).then((response) => response.json()).then((payload) => {
    if (!apiOk(payload)) throw new Error(payload.message || "登录失败")
    accessToken = payload.data.token
    sessionStorage.setItem("access_token", accessToken)
    return accessToken
  }).finally(() => { loginPromise = null })
  return loginPromise
}

function clearAccessToken() {
  accessToken = ""
  sessionStorage.removeItem("access_token")
}

function isAuthExpired(status, payload) {
  return status === 401 || (payload && Number(payload.code) >= 40100 && Number(payload.code) < 40200)
}

async function apiGet(path, canRetryAuth = true) {
  await ensureLogin()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  const payload = await response.json()
  if (isAuthExpired(response.status, payload) && canRetryAuth) {
    clearAccessToken()
    await ensureLogin()
    return apiGet(path, false)
  }
  return payload
}

async function apiSend(path, method, data, canRetryAuth = true) {
  await ensureLogin()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      Authorization: `Bearer ${accessToken}`
    },
    body: data ? JSON.stringify(data) : undefined
  })
  const payload = await response.json()
  if (isAuthExpired(response.status, payload) && canRetryAuth) {
    clearAccessToken()
    await ensureLogin()
    return apiSend(path, method, data, false)
  }
  return payload
}

function apiOk(response) {
  return response && response.code === 0
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function timeText(value) {
  if (!value) return "刚刚"
  return value.slice(11, 16) || "刚刚"
}

function formatToday() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${date.getFullYear()}-${month}-${day}`
}

function findDailyBlock(title) {
  return Array.from(document.querySelectorAll("#daily .block")).find((block) => {
    const heading = block.querySelector("h2")
    return heading && heading.textContent.includes(title)
  })
}

function riskText(level) {
  if (level === "high") return "高风险"
  if (level === "medium") return "中风险"
  return "可控"
}

function vitalStatus(label, value) {
  const numberValue = Number(value)
  if (label === "血压") return numberValue >= 140 ? "偏高" : numberValue >= 130 ? "关注" : "可控"
  if (label.includes("血糖")) return numberValue >= 6.1 ? "预警" : "可控"
  return "稳定"
}

function bindTabs() {
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.target
      tabs.forEach((item) => item.classList.toggle("active", item === tab))
      pages.forEach((page) => page.classList.toggle("active", page.id === target))
    })
  })
}

function bindCalendar() {
  calendarTriggers.forEach((button) => {
    button.addEventListener("click", () => {
      if (bigCalendarPreview) {
        bigCalendarPreview.classList.toggle("open")
      }
    })
  })

  if (bigCalendarPreview) {
    bigCalendarPreview.addEventListener("click", (event) => {
      if (event.target === bigCalendarPreview) {
        bigCalendarPreview.classList.remove("open")
      }
    })
  }

  const calendarStart = new Date(2026, 6, 27)
  monthPreviewButtons.forEach((button, index) => {
    const day = new Date(calendarStart)
    day.setDate(calendarStart.getDate() + index)
    button.dataset.date = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`
    button.addEventListener("click", async () => {
      monthPreviewButtons.forEach((item) => item.classList.toggle("active", item === button))
      if (bigCalendarPreview) {
        bigCalendarPreview.classList.remove("open")
      }
      await loadDailyDate(button.dataset.date)
    })
  })

  document.querySelector(".empty-record-preview button")?.addEventListener("click", async () => {
    const response = await apiSend("/daily-records", "POST", { date: selectedDate })
    if (apiOk(response)) {
      renderDaily(response)
      await loadMeals(currentRecordId)
    }
  })
}

function renderDaily(payload) {
  const data = payload.data
  const record = data.record
  const vitals = data.vitals || {}
  const nutrition = data.nutrition || {}
  const alerts = data.alerts || []
  document.querySelector(".empty-record-preview")?.setAttribute("hidden", "")
  selectedDate = record.record_date
  currentRecordId = record.id

  const title = document.querySelector("#daily .daily-hero h1")
  const score = document.querySelector("#daily .score strong")
  const heroNote = document.querySelector("#daily .daily-hero span")
  if (title) title.textContent = record.record_date
  if (score) score.textContent = record.health_score || 82
  if (heroNote) heroNote.textContent = `完成度 ${record.completion_rate}% · 已连接后端 API`

  renderMetrics(vitals)
  renderQuickForms(vitals)
  renderTasks(data.tasks || [])
  renderAlerts(alerts)
  renderNutrition(nutrition)
  const noteSection = document.querySelector(".daily-note-preview")
  if (noteSection) {
    const select = noteSection.querySelector("select")
    const textarea = noteSection.querySelector("textarea")
    if (select) select.value = record.mood || "平稳"
    if (textarea) textarea.value = record.note || ""
  }
}

async function loadDailyDate(date) {
  selectedDate = date
  const response = await apiGet(`/daily-records?date=${date}`)
  if (apiOk(response)) {
    renderDaily(response)
    await loadMeals(currentRecordId)
    return
  }
  currentRecordId = null
  const empty = document.querySelector(".empty-record-preview")
  if (empty) {
    empty.removeAttribute("hidden")
    empty.querySelector("strong").textContent = `${date} 还没有健康记录`
    const button = empty.querySelector("button")
    button.disabled = date > formatToday()
    button.textContent = date > formatToday() ? "未来日期暂不可补录" : "开始补录"
  }
}

function renderMetrics(vitals) {
  const grid = document.querySelector("#daily .metric-grid")
  if (!grid) return

  const pressure = vitals.systolic_pressure && vitals.diastolic_pressure
    ? `${vitals.systolic_pressure}/${vitals.diastolic_pressure}`
    : "-"
  const cards = [
    { label: "血压", value: pressure, status: vitalStatus("血压", vitals.systolic_pressure) },
    { label: "空腹血糖", value: vitals.fasting_glucose || "-", status: vitalStatus("空腹血糖", vitals.fasting_glucose) },
    { label: "餐后血糖", value: vitals.postprandial_glucose || "-", status: vitalStatus("餐后血糖", vitals.postprandial_glucose) },
    { label: "体重", value: `${vitals.weight_kg || 74}kg`, status: "稳定" }
  ]

  grid.innerHTML = cards.map((item) => `
    <div class="card">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <em class="${item.status === "偏高" || item.status === "预警" || item.status === "关注" ? "" : "ok"}">${escapeHtml(item.status)}</em>
    </div>
  `).join("")
}

function renderQuickForms(vitals) {
  const form = document.querySelector("#daily .form-demo")
  if (!form) return

  const fields = [
    ["收缩压", "systolic_pressure", vitals.systolic_pressure || "", "mmHg"],
    ["舒张压", "diastolic_pressure", vitals.diastolic_pressure || "", "mmHg"],
    ["空腹血糖", "fasting_glucose", vitals.fasting_glucose || "", "mmol/L"],
    ["餐后血糖", "postprandial_glucose", vitals.postprandial_glucose || "", "mmol/L"],
    ["今日体重", "weight_kg", vitals.weight_kg || "", "kg"]
  ]
  form.innerHTML = fields.map(([label, field, value, unit]) => `
    <label><span>${label}</span><span class="preview-input"><input type="number" step="0.1" data-field="${field}" value="${escapeHtml(value)}"><small>${unit}</small></span></label>
  `).join("") + '<button class="save-vitals-preview" type="button">保存今日记录</button>'

  form.querySelector(".save-vitals-preview")?.addEventListener("click", async (event) => {
    const button = event.currentTarget
    const payload = {}
    form.querySelectorAll("input[data-field]").forEach((input) => { payload[input.dataset.field] = Number(input.value) })
    button.disabled = true
    button.textContent = "保存中..."
    const response = await apiSend(`/daily-records/${currentRecordId}/vitals`, "PATCH", payload)
    if (apiOk(response)) {
      button.textContent = "保存成功"
      await loadDaily()
    } else {
      button.textContent = response.message || "保存失败"
      button.disabled = false
    }
  })
}

function bindTodoRow(row) {
  const statusButton = row.querySelector("[data-action='toggle']")
  const deleteButton = row.querySelector("[data-action='delete']")
  const input = row.querySelector("input")

  if (statusButton) {
    statusButton.addEventListener("click", async () => {
      const taskId = Number(row.dataset.taskId)
      const done = !statusButton.classList.contains("done")
      statusButton.classList.toggle("done", done)
      statusButton.classList.toggle("pending", !done)
      statusButton.textContent = done ? "已完成" : "待记录"

      if (taskId) {
        await apiSend(`/daily-tasks/${taskId}`, "PATCH", { is_done: done })
      }
    })
  }

  if (deleteButton) {
    deleteButton.addEventListener("click", () => {
      row.remove()
      syncTaskTemplateSoon()
    })
  }

  if (input) {
    input.addEventListener("input", syncTaskTemplateSoon)
  }
}

function bindDailyNote() {
  const section = document.querySelector(".daily-note-preview")
  const button = section?.querySelector("button")
  if (!button) return
  button.addEventListener("click", async () => {
    const mood = section.querySelector("select")?.value || "平稳"
    const note = section.querySelector("textarea")?.value || ""
    button.disabled = true
    button.textContent = "保存中..."
    const response = await apiSend(`/daily-records/${currentRecordId}`, "PATCH", { mood, note })
    button.textContent = apiOk(response) ? "保存成功" : response.message || "保存失败"
    setTimeout(() => {
      button.disabled = false
      button.textContent = "保存状态"
    }, 1200)
  })
}

function renderTasks(tasks) {
  const todoPreview = document.querySelector(".todo-preview")
  if (!todoPreview) return

  todoPreview.innerHTML = tasks.map((task) => `
    <div data-task-id="${task.id}">
      <input value="${escapeHtml(task.task_name)}" />
      <button data-action="toggle" class="${task.is_done ? "done" : "pending"}">${task.is_done ? "已完成" : "待记录"}</button>
      <button data-action="delete">删</button>
    </div>
  `).join("") + '<button class="add-todo-preview" type="button">添加待办</button>'

  Array.from(todoPreview.querySelectorAll("div")).forEach(bindTodoRow)
  const addButton = todoPreview.querySelector(".add-todo-preview")
  if (addButton) {
    addButton.addEventListener("click", () => {
      const row = document.createElement("div")
      row.innerHTML = '<input value="新增待办" /><button data-action="toggle" class="pending">待记录</button><button data-action="delete">删</button>'
      todoPreview.insertBefore(row, addButton)
      bindTodoRow(row)
      syncTaskTemplateSoon()
    })
  }
}

function syncTaskTemplateSoon() {
  if (taskSyncTimer) clearTimeout(taskSyncTimer)
  taskSyncTimer = setTimeout(async () => {
    const rows = Array.from(document.querySelectorAll(".todo-preview div"))
    const items = rows.map((row, index) => ({
      task_name: row.querySelector("input")?.value || "新增待办",
      sort_order: index + 1
    }))

    await apiSend("/daily-task-templates/current", "PUT", {
      effective_date: selectedDate || formatToday(),
      items
    })
  }, 700)
}

function renderAlerts(alerts) {
  const warn = document.querySelector("#daily .block.warn p")
  if (!warn) return
  if (!alerts.length) {
    warn.innerHTML = '<span class="preview-alert read">今日暂无异常提醒。</span>'
    return
  }
  warn.innerHTML = alerts.map((item) => `
    <button class="preview-alert ${item.is_read ? "read" : ""}" type="button" data-alert-id="${item.id}" ${item.is_read ? "disabled" : ""}>
      <strong>${escapeHtml(item.title || "健康提醒")}</strong>
      <span>${escapeHtml(item.description || item.content || item.title)}</span>
      <small>${item.is_read ? "已读" : "点击标记已读"}</small>
    </button>
  `).join("")
  warn.querySelectorAll("button[data-alert-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const response = await apiSend(`/alerts/${button.dataset.alertId}/read`, "PATCH")
      if (apiOk(response)) {
        button.classList.add("read")
        button.disabled = true
        button.querySelector("small").textContent = "已读"
      }
    })
  })
}

function renderNutrition(summary) {
  const block = findDailyBlock("三餐记录")
  const note = block?.querySelector("header span")
  if (note) {
    note.textContent = `热量 ${summary.calories || 0} kcal · 盐 ${summary.salt || 0}g`
  }
}

async function loadMeals(recordId) {
  const response = await apiGet(`/daily-records/${recordId}/meals`)
  if (!apiOk(response)) return

  const block = findDailyBlock("三餐记录")
  const list = block?.querySelector(".list")
  if (!list) return

  list.innerHTML = response.data.meals.map((meal) => {
    const foods = meal.foods || []
    return `
      <div class="preview-meal-row" data-meal-id="${meal.id}">
        <strong>${escapeHtml(meal.meal_name)}</strong>
        <span class="meal-food-text">${escapeHtml(foods.map((food) => food.name).join("、") || "暂无食物明细")}</span>
        <em>已记录</em>
        <span class="meal-row-actions"><button type="button" data-action="edit">编辑</button><button type="button" data-action="delete">删除</button></span>
      </div>
    `
  }).join("")

  list.querySelectorAll(".preview-meal-row").forEach((row) => {
    const mealId = Number(row.dataset.mealId)
    const meal = response.data.meals.find((item) => item.id === mealId)
    const editButton = row.querySelector('[data-action="edit"]')
    const deleteButton = row.querySelector('[data-action="delete"]')
    editButton?.addEventListener("click", async () => {
      const text = row.querySelector(".meal-food-text")
      const input = text.querySelector("input")
      if (!input) {
        const firstName = meal.foods?.[0]?.name || ""
        text.innerHTML = `<input value="${escapeHtml(firstName)}" aria-label="编辑食物名称">`
        editButton.textContent = "保存"
        text.querySelector("input").focus()
        return
      }
      const foods = (meal.foods || []).map((food, index) => index === 0 ? { ...food, name: input.value.trim() } : food)
      const updated = await apiSend(`/meals/${mealId}`, "PUT", { meal_type: meal.meal_type, meal_name: meal.meal_name, foods })
      if (apiOk(updated)) await loadMeals(recordId)
    })
    deleteButton?.addEventListener("click", async () => {
      const deleted = await apiSend(`/meals/${mealId}`, "DELETE")
      if (apiOk(deleted)) await loadMeals(recordId)
    })
  })
}

async function loadPredictions() {
  const response = await apiGet("/predictions/vitals?days=3")
  if (!apiOk(response)) return

  const block = findDailyBlock("未来 3 天预测")
  const list = block?.querySelector(".list")
  if (!list) return

  list.innerHTML = response.data.predictions.slice(0, 3).map((item, index) => `
    <div>
      <strong>${index === 0 ? "明日" : index === 1 ? "后天" : `第 ${index + 1} 天`}</strong>
      <span>血压 ${item.systolic_pressure}/${item.diastolic_pressure} · 血糖 ${item.fasting_glucose}</span>
      <em class="${item.risk_level === "low" ? "ok" : ""}">${riskText(item.risk_level)}</em>
    </div>
  `).join("")
}

async function loadReportHistory() {
  const response = await apiGet("/reports/history")
  if (!apiOk(response) || !response.data.items[0]) {
    currentReportId = null
    renderReportDetail(null, [])
    return
  }

  currentReportId = response.data.items[0].id
  const report = response.data.items[0]
  const fileTitle = document.querySelector(".file-card strong")
  const fileMeta = document.querySelector(".file-card span")
  const fileDesc = document.querySelector(".file-card p")
  if (fileTitle) fileTitle.textContent = report.file_name
  if (fileMeta) fileMeta.textContent = `${report.file_name.endsWith(".pdf") ? "PDF" : "图片"} · 后端历史记录 · ${report.status}`
  if (fileDesc) fileDesc.textContent = report.summary || "点击开始识别后读取后端 OCR 进度。"
  await loadReportDetailPreview(currentReportId)
}

function reportStatusText(status) {
  return ({ uploaded: "待识别", recognizing: "识别中", review_pending: "待复核", completed: "已确认" })[status] || status || "未知"
}

function indicatorStatusText(status) {
  return ({ normal: "正常", high: "偏高", low: "偏低", abnormal: "异常" })[status] || status
}

function renderReportDetail(detail, indicators) {
  currentReportDetail = detail
  reportEditMode = false
  const title = document.querySelector(".report-detail-title")
  const status = document.querySelector(".report-detail-status")
  const summary = document.querySelector(".report-detail-summary")
  const list = document.querySelector(".report-indicator-preview")
  const editButton = document.querySelector(".report-edit-preview")
  const saveButton = document.querySelector(".report-save-preview")
  if (title) title.textContent = detail ? detail.file_name : "报告详情"
  if (status) status.textContent = detail ? `${reportStatusText(detail.status)} · 置信度 ${detail.confidence == null ? "待计算" : `${Math.round(detail.confidence * 100)}%`}` : "等待选择报告"
  if (summary) summary.textContent = detail?.summary || "识别完成后可在这里复核指标。"
  if (editButton) {
    editButton.disabled = !detail || !indicators.length
    editButton.textContent = "人工纠错"
  }
  if (saveButton) saveButton.disabled = true
  if (!list) return
  list.innerHTML = indicators.length ? indicators.map((item) => `
    <div class="report-indicator-row" data-id="${item.id || ""}">
      <input data-field="indicator_name" value="${escapeHtml(item.indicator_name)}" aria-label="指标名称" disabled />
      <input data-field="value" value="${escapeHtml(item.value)}" aria-label="指标值" disabled />
      <input data-field="unit" value="${escapeHtml(item.unit || "")}" aria-label="单位" disabled />
      <input data-field="reference_range" value="${escapeHtml(item.reference_range || "")}" aria-label="参考范围" disabled />
      <select data-field="status" aria-label="指标状态" disabled>
        ${["normal", "high", "low", "abnormal"].map((value) => `<option value="${value}" ${value === (item.status || item.result_status) ? "selected" : ""}>${indicatorStatusText(value)}</option>`).join("")}
      </select>
    </div>
  `).join("") : "<p class=\"trend-empty-preview\">尚无识别指标，请先开始识别。</p>"
}

async function loadReportDetailPreview(reportId) {
  const [detailResponse, indicatorResponse] = await Promise.all([
    apiGet(`/reports/${reportId}`),
    apiGet(`/reports/${reportId}/indicators`)
  ])
  if (!apiOk(detailResponse) || !apiOk(indicatorResponse)) return
  renderReportDetail(detailResponse.data, indicatorResponse.data)
}

function renderWebTrend(points) {
  const container = document.querySelector("#web-trend-chart")
  const empty = document.querySelector(".trend-empty-preview")
  if (!container || typeof echarts === "undefined") return
  if (!points.length) {
    if (webTrendChart) webTrendChart.clear()
    if (empty) empty.hidden = false
    return
  }
  if (empty) empty.hidden = true
  if (!webTrendChart) webTrendChart = echarts.init(container)
  webTrendChart.setOption({
    color: ["#0f766e", "#38bdf8", "#f59e0b"],
    tooltip: { trigger: "axis" },
    legend: { top: 4, data: ["收缩压", "舒张压", "空腹血糖"], textStyle: { color: "#475569", fontSize: 11 } },
    grid: { left: 44, right: 44, top: 48, bottom: 34 },
    xAxis: { type: "category", boundaryGap: false, data: points.map((item) => item.date.slice(5)), axisLabel: { interval: points.length > 7 ? 4 : 0, color: "#64748b" } },
    yAxis: [
      { type: "value", name: "mmHg", min: 60, max: 180, splitLine: { lineStyle: { color: "#eef2f7" } } },
      { type: "value", name: "mmol/L", min: 3, max: 12, splitLine: { show: false } }
    ],
    series: [
      { name: "收缩压", type: "line", smooth: true, data: points.map((item) => item.systolic_pressure) },
      { name: "舒张压", type: "line", smooth: true, data: points.map((item) => item.diastolic_pressure) },
      { name: "空腹血糖", type: "line", yAxisIndex: 1, smooth: true, data: points.map((item) => item.fasting_glucose) }
    ]
  }, true)
}

async function loadWebTrend(range = webTrendRange) {
  const response = await apiGet(`/trends/vitals?range=${range}`)
  if (!apiOk(response)) return
  webTrendRange = range
  document.querySelectorAll(".trend-range-preview button").forEach((button) => button.classList.toggle("active", button.dataset.range === range))
  renderWebTrend(response.data.points || [])
}

async function loadDaily() {
  try {
    const response = await apiGet("/daily-records/today")
    if (!apiOk(response)) throw new Error(response.message)
    renderDaily(response)
    await Promise.all([
      loadMeals(currentRecordId),
      loadPredictions(),
      loadReportHistory(),
      loadWebTrend()
    ])
    setApiStatus("已连接 Flask 后端 API")
  } catch (error) {
    setApiStatus("后端连接失败，显示本地预览", false)
  }
}

async function uploadDemoReport(sourceText, canRetryAuth = true) {
  await ensureLogin()
  const fileName = sourceText.includes("拍照") ? "拍照体检报告.jpg" : "体检报告图片.jpg"
  const form = new FormData()
  form.append("file", new Blob(["demo report image"], { type: "image/jpeg" }), fileName)
  form.append("source", sourceText.includes("拍照") ? "camera" : "album")
  form.append("report_date", selectedDate || formatToday())

  const response = await fetch(`${API_BASE_URL}/reports/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: form
  }).then(async (item) => ({ status: item.status, payload: await item.json() }))

  if (isAuthExpired(response.status, response.payload) && canRetryAuth) {
    clearAccessToken()
    await ensureLogin()
    return uploadDemoReport(sourceText, false)
  }

  if (!apiOk(response.payload)) {
    if (progressText) progressText.textContent = response.payload?.message || "上传失败，请检查后端服务"
    return
  }
  currentReportId = response.payload.data.report_id

  const fileTitle = document.querySelector(".file-card strong")
  const fileMeta = document.querySelector(".file-card span")
  const fileDesc = document.querySelector(".file-card p")
  if (fileTitle) fileTitle.textContent = fileName
  if (fileMeta) fileMeta.textContent = `图片 · ${sourceText} · 待识别`
  if (fileDesc) fileDesc.textContent = "已上传到 Flask 后端，点击开始识别后读取 OCR 进度。"
  if (progressText) progressText.textContent = `${sourceText}已上传，等待开始识别`
  await loadReportDetailPreview(currentReportId)
}

function bindReportUpload() {
  if (dropzonePreview && choicePanel) {
    dropzonePreview.addEventListener("click", () => {
      choicePanel.classList.toggle("open")
    })
  }

  choiceButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      if (choicePanel) choicePanel.classList.remove("open")
      if (progressText) progressText.textContent = "正在上传到后端"
      await uploadDemoReport(button.textContent)
    })
  })

  if (!startOcrButton || !progressFill || !progressLabel || !progressText) return

  startOcrButton.addEventListener("click", async () => {
    if (!currentReportId) {
      await uploadDemoReport("选择图片")
    }

    if (progressTimer) clearInterval(progressTimer)
    const recognizeResponse = await apiSend(`/reports/${currentReportId}/recognize`, "POST")
    if (!apiOk(recognizeResponse)) return
    await loadReportDetailPreview(currentReportId)

    progressFill.style.width = "8%"
    progressLabel.textContent = "8%"
    progressText.textContent = "正在请求后端 OCR 识别接口"
    startOcrButton.disabled = true
    startOcrButton.textContent = "识别中"

    progressTimer = setInterval(async () => {
      const response = await apiGet(`/reports/${currentReportId}/progress`)
      if (!apiOk(response)) return

      const progress = response.data.progress
      progressFill.style.width = `${progress}%`
      progressLabel.textContent = `${progress}%`
      progressText.textContent = response.data.message

      if (progress >= 100 || response.data.status === "review_pending") {
        clearInterval(progressTimer)
        progressTimer = null
        startOcrButton.disabled = false
        startOcrButton.textContent = "重新识别"
        await loadReportHistory()
      }
    }, 800)
  })
}

function bindReportReview() {
  const editButton = document.querySelector(".report-edit-preview")
  const saveButton = document.querySelector(".report-save-preview")
  const confirmButton = document.querySelector(".report-confirm-preview")
  const rerecognizeButton = document.querySelector(".report-rerecognize-preview")
  const deleteButton = document.querySelector(".report-delete-preview")

  editButton?.addEventListener("click", () => {
    if (!currentReportId) return
    reportEditMode = !reportEditMode
    document.querySelectorAll(".report-indicator-row input, .report-indicator-row select").forEach((input) => { input.disabled = !reportEditMode })
    editButton.textContent = reportEditMode ? "取消纠错" : "人工纠错"
    if (saveButton) saveButton.disabled = !reportEditMode
  })

  saveButton?.addEventListener("click", async () => {
    if (!currentReportId || !reportEditMode) return
    const items = Array.from(document.querySelectorAll(".report-indicator-row")).map((row) => ({
      indicator_name: row.querySelector('[data-field="indicator_name"]').value.trim(),
      value: row.querySelector('[data-field="value"]').value.trim(),
      unit: row.querySelector('[data-field="unit"]').value.trim(),
      reference_range: row.querySelector('[data-field="reference_range"]').value.trim(),
      status: row.querySelector('[data-field="status"]').value
    }))
    if (!items.length || items.some((item) => !item.indicator_name || !item.value)) {
      window.alert("指标名称和值不能为空")
      return
    }
    const response = await apiSend(`/reports/${currentReportId}/indicators`, "PUT", { items })
    if (!apiOk(response)) {
      window.alert(response.message || "保存失败")
      return
    }
    await loadReportDetailPreview(currentReportId)
  })

  confirmButton?.addEventListener("click", async () => {
    if (!currentReportId) return
    const response = await apiSend(`/reports/${currentReportId}`, "PATCH", { action: "confirm", review_note: "网页版人工复核确认" })
    if (!apiOk(response)) {
      window.alert(response.message || "确认失败")
      return
    }
    await loadReportDetailPreview(currentReportId)
  })

  rerecognizeButton?.addEventListener("click", () => {
    if (currentReportId) startOcrButton?.click()
  })

  deleteButton?.addEventListener("click", async () => {
    if (!currentReportId || !window.confirm("确定删除当前报告及其识别指标吗？")) return
    const response = await apiSend(`/reports/${currentReportId}`, "DELETE")
    if (!apiOk(response)) {
      window.alert(response.message || "删除失败")
      return
    }
    currentReportId = null
    renderReportDetail(null, [])
    await loadReportHistory()
  })
}

function bindTrendRange() {
  document.querySelectorAll(".trend-range-preview button").forEach((button) => {
    button.addEventListener("click", () => loadWebTrend(button.dataset.range))
  })
  window.addEventListener("resize", () => webTrendChart?.resize())
}

function renderQuickQuestions(questions) {
  const quick = document.querySelector(".quick-preview")
  if (!quick) return

  quick.innerHTML = questions.map((question, index) => `
    <button class="${index === 0 ? "active" : ""}" type="button">${escapeHtml(question)}</button>
  `).join("")

  Array.from(quick.querySelectorAll("button")).forEach((button) => {
    button.addEventListener("click", () => {
      Array.from(quick.querySelectorAll("button")).forEach((item) => item.classList.toggle("active", item === button))
      sendAiQuestion(button.textContent)
    })
  })
}

function renderMessages(messages) {
  const panel = document.querySelector(".chat-panel-preview")
  const composer = panel?.querySelector(".chat-composer")
  if (!panel || !composer) return

  panel.querySelectorAll(".message").forEach((item) => item.remove())
  messages.forEach((message) => {
    const row = document.createElement("div")
    row.className = `message ${message.role === "user" ? "user" : "assistant"}`
    row.innerHTML = `
      <b>${message.role === "user" ? "我" : "AI"}</b>
      <div><small>${message.role === "user" ? "我" : "AI 助手"} · ${timeText(message.created_at)}</small><p>${escapeHtml(message.content)}</p></div>
    `
    panel.insertBefore(row, composer)
  })
}

async function loadAi() {
  try {
    const [questions, context, conversations] = await Promise.all([
      apiGet("/ai/quick-questions"),
      apiGet(`/ai/context/today?date=${formatToday()}`),
      apiGet("/ai/conversations")
    ])

    if (apiOk(questions)) renderQuickQuestions(questions.data)
    if (apiOk(context)) {
      const contextItems = document.querySelectorAll(".context-mini div")
      if (contextItems[0]) contextItems[0].innerHTML = "<strong>今日记录</strong><span>已读取</span>"
      if (contextItems[1]) contextItems[1].innerHTML = "<strong>中风险</strong><span>风险等级</span>"
      if (contextItems[2]) contextItems[2].innerHTML = "<strong>3 条</strong><span>知识命中</span>"
    }

    if (apiOk(conversations)) {
      const first = conversations.data.items[0]
      renderConversationHistory(conversations.data.items)
      if (first) {
        currentConversationId = first.id
        const messages = await apiGet(`/ai/conversations/${currentConversationId}/messages`)
        if (apiOk(messages)) renderMessages(messages.data)
      }
    }
  } catch (error) {
    setApiStatus("AI 接口暂未连接，显示本地预览", false)
  }
}

function renderConversationHistory(items) {
  const list = document.querySelector(".history-preview")
  if (!list) return
  list.innerHTML = items.map((item) => `
    <button type="button" data-conversation-id="${item.id}">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.last_message || "暂无消息")}</span>
      <em>${timeText(item.updated_at)}</em>
    </button>
  `).join("")
  list.querySelectorAll("button[data-conversation-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      currentConversationId = Number(button.dataset.conversationId)
      const messages = await apiGet(`/ai/conversations/${currentConversationId}/messages`)
      if (apiOk(messages)) renderMessages(messages.data)
    })
  })
}

async function ensureConversation(title) {
  if (currentConversationId) return currentConversationId
  const response = await apiSend("/ai/conversations", "POST", {
    title,
    source: "preview",
    related_date: formatToday()
  })
  if (!apiOk(response)) throw new Error(response.message || "创建会话失败")
  currentConversationId = response.data.conversation_id
  return currentConversationId
}

async function sendAiQuestion(question) {
  const normalizedQuestion = String(question || "").trim()
  if (!normalizedQuestion) return
  const sendButton = document.querySelector(".chat-composer button")
  if (sendButton) {
    sendButton.disabled = true
    sendButton.textContent = "发送中"
  }

  try {
    const conversationId = await ensureConversation(normalizedQuestion)
    renderMessages([
      { role: "user", content: normalizedQuestion, created_at: "刚刚" },
      { role: "assistant", content: "正在结合你的每日记录生成建议...", created_at: "刚刚" }
    ])

    const response = await apiSend(`/ai/conversations/${conversationId}/messages`, "POST", {
      content: normalizedQuestion,
      use_daily_context: true,
      related_date: formatToday()
    })

    if (!apiOk(response)) throw new Error(response.message || "AI 回复失败")
    const messages = await apiGet(`/ai/conversations/${conversationId}/messages`)
    if (apiOk(messages)) renderMessages(messages.data)
    const conversations = await apiGet("/ai/conversations")
    if (apiOk(conversations)) {
      renderConversationHistory(conversations.data.items)
    }
  } catch (error) {
    renderMessages([
      { role: "user", content: normalizedQuestion, created_at: "刚刚" },
      { role: "assistant", content: error.message || "AI 接口暂时不可用，请稍后重试。", created_at: "刚刚" }
    ])
  } finally {
    if (sendButton) {
      sendButton.disabled = false
      sendButton.textContent = "发送"
    }
  }
}

function bindAiButtons() {
  const newChatButton = document.querySelector(".chat-panel-preview header button")
  const sendButton = document.querySelector(".chat-composer button")
  const input = document.querySelector(".chat-composer input")

  if (newChatButton) {
    newChatButton.addEventListener("click", async () => {
      const response = await apiSend("/ai/conversations", "POST", {
        title: "新的健康问答",
        source: "preview",
        related_date: formatToday()
      })
      if (!apiOk(response)) return
      currentConversationId = response.data.conversation_id
      renderMessages([{ role: "assistant", content: "新对话已创建，可以继续提问。", created_at: "刚刚" }])
      const conversations = await apiGet("/ai/conversations")
      if (apiOk(conversations)) renderConversationHistory(conversations.data.items)
    })
  }

  if (sendButton) {
    sendButton.addEventListener("click", () => {
      const question = input?.value || ""
      if (input) input.value = ""
      sendAiQuestion(question)
    })
  }

  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return
      const question = input.value
      input.value = ""
      sendAiQuestion(question)
    })
  }
}

async function loadMine() {
  try {
    const [profile, settings] = await Promise.all([
      apiGet("/me/profile"),
      apiGet("/me/settings")
    ])

    if (apiOk(profile)) {
      const user = profile.data.user
      const health = profile.data.health_profile
      accountProfileState.saved = {
        nickname: user.nickname || "",
        phone: user.phone || "",
        avatarUrl: user.avatar_url || ""
      }
      accountProfileState.current = { ...accountProfileState.saved }
      accountProfileState.avatarFile = null
      accountProfileState.avatarRemoved = false
      const hero = document.querySelector("#mine .mine-hero")
      if (hero) {
        const name = hero.querySelector("h1")
        const spans = hero.querySelectorAll("div:nth-child(2) > span")
        renderWebAvatar(user.avatar_url, user.nickname)
        if (name) name.textContent = user.nickname
        if (spans[0]) spans[0].textContent = `年龄：${health.age || user.age || ""} 岁`
        if (spans[1]) spans[1].textContent = `电话：${user.phone_masked || maskPhone(user.phone)}`
      }

      const nicknameInput = document.querySelector('[data-profile="nickname"]')
      const phoneInput = document.querySelector('[data-profile="phone"]')
      if (nicknameInput) nicknameInput.value = user.nickname || ""
      if (phoneInput) phoneInput.value = user.phone || ""
      updateAccountSaveState()

      const values = [
        health.gender,
        `${health.age || user.age} 岁`,
        `${health.height_cm} cm`,
        `${health.weight_kg} kg`,
        health.bmi,
        health.disease_type,
        health.medical_history,
        health.medications || health.medication
      ]
      document.querySelectorAll(".profile-edit-preview input").forEach((input, index) => {
        input.value = values[index] || ""
      })
      healthProfileState.saved = values.map((value) => String(value || "").trim())
      healthProfileState.current = [...healthProfileState.saved]
      updateHealthProfileSaveState()
    }

    if (apiOk(settings)) {
      const alertInput = document.querySelector('[data-setting="alert_push_enabled"]')
      const reminderInput = document.querySelector('[data-setting="daily_record_reminder_enabled"]')
      const timeInput = document.querySelector('[data-setting="daily_record_reminder_time"]')
      if (alertInput) alertInput.checked = settings.data.alert_push_enabled
      if (reminderInput) reminderInput.checked = settings.data.daily_record_reminder_enabled
      if (timeInput) {
        timeInput.value = settings.data.daily_record_reminder_time
        timeInput.disabled = !settings.data.daily_record_reminder_enabled
      }
    }
  } catch (error) {
    setApiStatus("个人中心接口暂未连接，显示本地预览", false)
  }
}

function updateHealthProfileSaveState() {
  const saveButton = profileSaveButton
  const dirty = healthProfileState.current.length !== healthProfileState.saved.length
    || healthProfileState.current.some((value, index) => value !== healthProfileState.saved[index])
  if (saveButton) {
    saveButton.disabled = !dirty
    saveButton.classList.toggle("active", dirty)
    saveButton.classList.toggle("inactive", !dirty)
  }
  return dirty
}

function bindMineSave() {
  if (!profileSaveButton) return
  const profileInputs = Array.from(document.querySelectorAll(".profile-edit-preview input"))
  healthProfileState.current = profileInputs.map((item) => String(item.value || "").trim())
  if (!healthProfileState.saved.length) {
    healthProfileState.saved = [...healthProfileState.current]
  }
  updateHealthProfileSaveState()
  profileInputs.forEach((input, index) => input.addEventListener("input", () => {
    healthProfileState.current = profileInputs.map((item) => String(item.value || "").trim())
    if (index === 1) {
      const matched = String(input.value || "").match(/\d+(\.\d+)?/)
      const spans = document.querySelectorAll("#mine .mine-hero div:nth-child(2) > span")
      if (spans[0]) spans[0].textContent = `年龄：${matched ? matched[0] : ""} 岁`
    }
    updateHealthProfileSaveState()
  }))

  profileSaveButton.addEventListener("click", async () => {
    if (!updateHealthProfileSaveState()) return
    const inputs = Array.from(document.querySelectorAll(".profile-edit-preview input"))
    const numberValue = (text) => Number(String(text).match(/\d+(\.\d+)?/)?.[0] || 0)
    profileSaveButton.disabled = true
    profileSaveButton.textContent = "保存中..."
    const response = await apiSend("/me/health-profile", "PUT", {
      gender: inputs[0]?.value || "",
      age: numberValue(inputs[1]?.value),
      height_cm: numberValue(inputs[2]?.value),
      weight_kg: numberValue(inputs[3]?.value),
      disease_type: inputs[5]?.value || "",
      medical_history: inputs[6]?.value || "",
      medications: inputs[7]?.value || "",
      chronic_types: ["hypertension", "diabetes"]
    })

    profileSaveButton.textContent = apiOk(response) ? "已保存到后端" : "保存失败"
    if (apiOk(response)) {
      const spans = document.querySelectorAll("#mine .mine-hero div:nth-child(2) > span")
      if (spans[0]) spans[0].textContent = `年龄：${response.data.age || ""} 岁`
      const values = [
        response.data.gender,
        `${response.data.age || ""} 岁`,
        `${response.data.height_cm || ""} cm`,
        `${response.data.weight_kg || ""} kg`,
        response.data.bmi,
        response.data.disease_type,
        response.data.medical_history,
        response.data.medications || response.data.medication
      ]
      inputs.forEach((input, index) => { input.value = values[index] || "" })
      healthProfileState.saved = values.map((value) => String(value || "").trim())
      healthProfileState.current = [...healthProfileState.saved]
    }
    setTimeout(() => {
      profileSaveButton.textContent = "保存健康档案"
      updateHealthProfileSaveState()
    }, 1200)
  })
}

function renderWebAvatar(avatarUrl, nickname) {
  const avatar = document.querySelector("#mine .mine-hero .avatar")
  const face = avatar?.querySelector(".avatar-face") || avatar
  if (!face) return
  face.innerHTML = avatarUrl
    ? `<img src="${escapeHtml(avatarUrl)}" alt="用户头像" />`
    : `<span>${escapeHtml((nickname || "用").slice(0, 1))}</span>`
}

function updateAccountSaveState() {
  const saveButton = document.querySelector(".account-save-preview")
  const pending = document.querySelector(".account-pending-preview")
  const saved = accountProfileState.saved
  const current = accountProfileState.current
  const dirty = current.nickname !== saved.nickname
    || current.phone !== saved.phone
    || current.avatarUrl !== saved.avatarUrl
  if (saveButton) {
    saveButton.disabled = !dirty
    saveButton.classList.toggle("active", dirty)
    saveButton.classList.toggle("inactive", !dirty)
  }
  if (pending) pending.hidden = !dirty
  return dirty
}

function setAccountCurrent(nextValues) {
  accountProfileState.current = { ...accountProfileState.current, ...nextValues }
  const hero = document.querySelector("#mine .mine-hero")
  if (hero?.querySelector("h1")) hero.querySelector("h1").textContent = accountProfileState.current.nickname || "未填写"
  const spans = hero?.querySelectorAll("div:nth-child(2) > span") || []
  if (spans[1]) spans[1].textContent = `电话：${maskPhone(accountProfileState.current.phone)}`
  renderWebAvatar(accountProfileState.current.avatarUrl, accountProfileState.current.nickname)
  updateAccountSaveState()
}

function promptPreviewWechatProfileIfNeeded() {
  if (localStorage.getItem(WECHAT_PROFILE_PROMPT_KEY)) return
  localStorage.setItem(WECHAT_PROFILE_PROMPT_KEY, "1")
  if (!window.confirm("是否使用微信头像和微信昵称作为个人资料？")) return
  window.alert("浏览器预览不能直接读取微信资料。请在微信开发者工具里点击“使用”，或在这里手动编辑昵称并选择头像。")
}

function bindAccountProfile() {
  const nicknameInput = document.querySelector('[data-profile="nickname"]')
  const phoneInput = document.querySelector('[data-profile="phone"]')
  const saveButton = document.querySelector(".account-save-preview")
  const fileInput = document.querySelector(".avatar-picker-preview input")

  nicknameInput?.addEventListener("input", () => {
    setAccountCurrent({ nickname: nicknameInput.value.trim() })
  })

  phoneInput?.addEventListener("input", () => {
    setAccountCurrent({ phone: phoneInput.value.trim() })
  })

  saveButton?.addEventListener("click", async () => {
    const nickname = nicknameInput.value.trim()
    const phone = phoneInput.value.trim()
    if (!updateAccountSaveState()) return
    if (!nickname || nickname.length > 30) return window.alert("昵称长度应为1到30个字符")
    if (phone && !/^1[3-9]\d{9}$/.test(phone)) return window.alert("请输入正确的手机号")
    if (!window.confirm("确认保存当前头像、昵称和联系方式的修改吗？")) return
    saveButton.disabled = true
    saveButton.textContent = "保存中..."
    let avatarUrl = accountProfileState.current.avatarUrl
    try {
      if (accountProfileState.avatarRemoved) {
        const avatarResponse = await apiSend("/me/avatar", "DELETE")
        if (!apiOk(avatarResponse)) throw new Error(avatarResponse.message || "头像移除失败")
        avatarUrl = ""
      } else if (accountProfileState.avatarFile) {
        await ensureLogin()
        const form = new FormData()
        form.append("file", accountProfileState.avatarFile)
        const avatarResponse = await fetch(`${API_BASE_URL}/me/avatar`, {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: form
        }).then((item) => item.json())
        if (!apiOk(avatarResponse)) throw new Error(avatarResponse.message || "头像上传失败")
        avatarUrl = avatarResponse.data.avatar_url || avatarUrl
      }
      const response = await apiSend("/me/profile", "PUT", { nickname, phone, avatar_url: avatarUrl })
      if (!apiOk(response)) throw new Error(response.message || "保存失败")
      accountProfileState.saved = {
        nickname: response.data.nickname,
        phone,
        avatarUrl: response.data.avatar_url || avatarUrl || ""
      }
      accountProfileState.current = { ...accountProfileState.saved }
      accountProfileState.avatarFile = null
      accountProfileState.avatarRemoved = false
      setAccountCurrent(accountProfileState.current)
      saveButton.textContent = "个人资料已保存"
    } catch (error) {
      window.alert(error.message || "保存失败")
      saveButton.textContent = "保存个人资料"
    }
    setTimeout(() => {
      saveButton.textContent = "保存个人资料"
      updateAccountSaveState()
    }, 1200)
  })

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      window.alert("头像图片不能超过2MB")
      fileInput.value = ""
      return
    }
    accountProfileState.avatarFile = file
    accountProfileState.avatarRemoved = false
    setAccountCurrent({ avatarUrl: URL.createObjectURL(file) })
    window.alert("已选择头像，点击保存后才会上传。")
    fileInput.value = ""
  })

}

function bindMineSettings() {
  const controls = Array.from(document.querySelectorAll(".settings-preview input"))
  controls.forEach((control) => control.addEventListener("change", async () => {
    const alertInput = document.querySelector('[data-setting="alert_push_enabled"]')
    const reminderInput = document.querySelector('[data-setting="daily_record_reminder_enabled"]')
    const timeInput = document.querySelector('[data-setting="daily_record_reminder_time"]')
    if (timeInput) timeInput.disabled = !reminderInput.checked
    await apiSend("/me/settings", "PUT", {
      alert_push_enabled: alertInput.checked,
      daily_record_reminder_enabled: reminderInput.checked,
      daily_record_reminder_time: timeInput.value
    })
  }))
}

function applyHashTarget() {
  if (!window.location.hash) return

  const hashTarget = document.querySelector(window.location.hash)
  if (!hashTarget) return

  const parentPage = hashTarget.closest(".page")
  if (parentPage) {
    tabs.forEach((item) => item.classList.toggle("active", item.dataset.target === parentPage.id))
    pages.forEach((page) => page.classList.toggle("active", page === parentPage))
  }

  hashTarget.scrollIntoView({ block: "start" })
}

bindTabs()
bindCalendar()
bindDailyNote()
bindReportUpload()
bindReportReview()
bindTrendRange()
bindAiButtons()
bindMineSave()
bindAccountProfile()
bindMineSettings()
loadDaily()
loadAi()
loadMine()
setTimeout(promptPreviewWechatProfileIfNeeded, 600)
applyHashTarget()
