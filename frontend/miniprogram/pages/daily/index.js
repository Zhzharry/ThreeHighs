const weekText = ["日", "一", "二", "三", "四", "五", "六"]
const fullWeekText = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
const monthWeekdays = ["一", "二", "三", "四", "五", "六", "日"]
const api = require("../../services/api")
const echarts = require("../../ec-canvas/echarts")

let trendChart = null

const monthCalendar = [
  { date: "2026-07-27", day: "27", lunar: "十四", outside: true, hasRecord: true, completion: 64 },
  { date: "2026-07-28", day: "28", lunar: "十五", outside: true, hasRecord: true, completion: 68 },
  { date: "2026-07-29", day: "29", lunar: "十六", outside: true, hasRecord: true, completion: 70 },
  { date: "2026-07-30", day: "30", lunar: "十七", outside: true, hasRecord: true, completion: 72 },
  { date: "2026-07-31", day: "31", lunar: "十八", outside: true, hasRecord: true, completion: 74 },
  { date: "2026-08-01", day: "1", lunar: "十九", hasRecord: true, completion: 76 },
  { date: "2026-08-02", day: "2", lunar: "二十", hasRecord: true, completion: 78 },
  { date: "2026-08-03", day: "3", lunar: "廿一", hasRecord: true, completion: 80 },
  { date: "2026-08-04", day: "4", lunar: "廿二", hasRecord: true, completion: 82 },
  { date: "2026-08-05", day: "5", lunar: "廿三", hasRecord: true, completion: 84 },
  { date: "2026-08-06", day: "6", lunar: "廿四", hasRecord: true, completion: 86 },
  { date: "2026-08-07", day: "7", lunar: "立秋", hasRecord: true, completion: 88 },
  { date: "2026-08-08", day: "8", lunar: "廿六", hasRecord: true, completion: 90 },
  { date: "2026-08-09", day: "9", lunar: "廿七", hasRecord: true, completion: 82 },
  { date: "2026-08-10", day: "10", lunar: "廿八", hasRecord: true, completion: 84 },
  { date: "2026-08-11", day: "11", lunar: "廿九", hasRecord: true, completion: 86 },
  { date: "2026-08-12", day: "12", lunar: "三十", hasRecord: true, completion: 88 },
  { date: "2026-08-13", day: "13", lunar: "七月", hasRecord: true, completion: 78 },
  { date: "2026-08-14", day: "14", lunar: "初二", hasRecord: true, completion: 80 },
  { date: "2026-08-15", day: "15", lunar: "初三", hasRecord: true, completion: 82 },
  { date: "2026-08-16", day: "16", lunar: "初四", hasRecord: true, completion: 84 },
  { date: "2026-08-17", day: "17", lunar: "初五", isToday: true, hasRecord: true, completion: 86 },
  { date: "2026-08-18", day: "18", lunar: "初六", hasRecord: true, completion: 76 },
  { date: "2026-08-19", day: "19", lunar: "初七", hasRecord: false, completion: 22 },
  { date: "2026-08-20", day: "20", lunar: "初八", hasRecord: true, completion: 68, muted: true },
  { date: "2026-08-21", day: "21", lunar: "初九", hasRecord: true, completion: 70 },
  { date: "2026-08-22", day: "22", lunar: "初十", hasRecord: true, completion: 72 },
  { date: "2026-08-23", day: "23", lunar: "处暑", hasRecord: true, completion: 74 },
  { date: "2026-08-24", day: "24", lunar: "十二", hasRecord: true, completion: 78 },
  { date: "2026-08-25", day: "25", lunar: "十三", hasRecord: true, completion: 80 },
  { date: "2026-08-26", day: "26", lunar: "十四", hasRecord: true, completion: 82 },
  { date: "2026-08-27", day: "27", lunar: "十五", hasRecord: true, completion: 84 },
  { date: "2026-08-28", day: "28", lunar: "十六", hasRecord: true, completion: 86 },
  { date: "2026-08-29", day: "29", lunar: "十七", hasRecord: true, completion: 88 },
  { date: "2026-08-30", day: "30", lunar: "十八", hasRecord: true, completion: 90 },
  { date: "2026-08-31", day: "31", lunar: "十九", hasRecord: true, completion: 84 },
  { date: "2026-09-01", day: "1", lunar: "二十", outside: true, hasRecord: true, completion: 78 },
  { date: "2026-09-02", day: "2", lunar: "廿一", outside: true, hasRecord: true, completion: 76 },
  { date: "2026-09-03", day: "3", lunar: "廿二", outside: true, hasRecord: true, completion: 74 },
  { date: "2026-09-04", day: "4", lunar: "廿三", outside: true, hasRecord: false, completion: 22 },
  { date: "2026-09-05", day: "5", lunar: "廿四", outside: true, hasRecord: true, completion: 72 },
  { date: "2026-09-06", day: "6", lunar: "廿五", outside: true, hasRecord: true, completion: 70 }
]

function pad(value) {
  return String(value).padStart(2, "0")
}

function formatDate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function parseDateText(dateText) {
  const [year, month, day] = dateText.split("-").map(Number)
  return new Date(year, month - 1, day)
}

function getCalendarMeta(dateText) {
  const date = parseDateText(dateText)
  const item = monthCalendar.find((day) => day.date === dateText)
  let lunar = item ? item.lunar : ""

  if (item && item.date.startsWith("2026-08") && Number(item.day) >= 13 && item.lunar !== "七月" && item.lunar !== "立秋" && item.lunar !== "处暑") {
    lunar = `七月${item.lunar}`
  } else if (item && item.lunar === "七月") {
    lunar = "七月初一"
  }

  return {
    title: `${date.getMonth() + 1}月${date.getDate()}日, ${fullWeekText[date.getDay()]}`,
    lunar
  }
}

function formatFileSize(size) {
  if (!size) {
    return "大小未知"
  }

  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function buildCalendar(today) {
  const days = []
  const start = new Date(today)
  start.setDate(today.getDate() - 3)

  for (let index = 0; index < 7; index += 1) {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    days.push({
      date: formatDate(date),
      day: pad(date.getDate()),
      week: weekText[date.getDay()],
      isToday: formatDate(date) === formatDate(today),
      hasRecord: index !== 1 && index !== 5,
      completion: index === 3 ? 86 : index === 1 || index === 5 ? 22 : 68 + index * 3
    })
  }

  return days
}

function getVitalStatus(label, value) {
  const numberValue = Number(value)

  if (label === "收缩压" && numberValue >= 140) return { text: "偏高", warn: true }
  if (label === "收缩压" && numberValue >= 130) return { text: "关注", warn: true }
  if (label === "舒张压" && numberValue >= 90) return { text: "偏高", warn: true }
  if (label === "舒张压" && numberValue >= 85) return { text: "关注", warn: true }
  if (label === "空腹血糖" && numberValue >= 6.1) return { text: "预警", warn: true }
  if (label === "餐后血糖" && numberValue >= 7.8) return { text: "关注", warn: true }

  return { text: "可控", warn: false }
}

function mapVitals(vitals = {}) {
  const rows = [
    { label: "收缩压", value: vitals.systolic_pressure || "-", unit: "mmHg" },
    { label: "舒张压", value: vitals.diastolic_pressure || "-", unit: "mmHg" },
    { label: "空腹血糖", value: vitals.fasting_glucose || "-", unit: "mmol/L" },
    { label: "餐后血糖", value: vitals.postprandial_glucose || "-", unit: "mmol/L" }
  ]

  return rows.map((item) => {
    const status = getVitalStatus(item.label, item.value)
    return {
      ...item,
      status: status.text,
      warn: status.warn
    }
  })
}

function mapForms(vitals = {}) {
  return [
    { label: "晨间血压", value: `${vitals.systolic_pressure || "-"}/${vitals.diastolic_pressure || "-"}`, unit: "mmHg", placeholder: "输入血压" },
    { label: "空腹血糖", value: vitals.fasting_glucose || "-", unit: "mmol/L", placeholder: "输入血糖" },
    { label: "餐后血糖", value: vitals.postprandial_glucose || "-", unit: "mmol/L", placeholder: "输入血糖" },
    { label: "今日体重", value: vitals.weight_kg || "-", unit: "kg", placeholder: "输入体重" }
  ]
}

function mapNutrition(summary = {}) {
  const calories = Number(summary.calories || 0)
  const sugar = Number(summary.sugar || 0)
  const fat = Number(summary.fat || 0)
  const salt = Number(summary.salt || 0)

  const withProgressStyle = (item) => ({
    ...item,
    progressStyle: `width: ${item.progress}%;`
  })

  return [
    { label: "热量", value: `${calories || 0} kcal`, progress: Math.min(Math.round(calories / 20), 100), warn: false },
    { label: "糖分", value: `${sugar || 0} g`, progress: Math.min(Math.round(sugar * 2), 100), warn: sugar > 50 },
    { label: "脂肪", value: `${fat || 0} g`, progress: Math.min(Math.round(fat * 1.6), 100), warn: fat > 60 },
    { label: "盐分", value: `${salt || 0} g`, progress: Math.min(Math.round(salt * 18), 100), warn: salt > 5 }
  ].map(withProgressStyle)
}

function mapMeals(meals = []) {
  return meals.map((meal) => {
    const foods = meal.foods || []
    const calories = foods.reduce((sum, food) => sum + Number(food.calories || 0), 0)
    const sugar = foods.reduce((sum, food) => sum + Number(food.sugar || 0), 0)
    const salt = foods.reduce((sum, food) => sum + Number(food.salt || 0), 0)

    return {
      id: meal.id,
      mealType: meal.meal_type,
      firstFood: foods[0] || {},
      name: meal.meal_name,
      text: foods.map((food) => `${food.name}${food.amount ? ` ${food.amount}` : ""}`).join("、") || "暂无食物明细",
      calories: `${Math.round(calories)} kcal`,
      sugar: `${sugar.toFixed(1)}g`,
      salt: `${salt.toFixed(1)}g`,
      tag: "已记录"
    }
  })
}

function mapPredictions(predictions = []) {
  return predictions.slice(0, 3).map((item, index) => ({
    date: index === 0 ? "明日" : index === 1 ? "后天" : `第 ${index + 1} 天`,
    bp: `${item.systolic_pressure}/${item.diastolic_pressure}`,
    glucose: item.fasting_glucose,
    level: item.risk_level === "medium" ? "中风险" : item.risk_level === "high" ? "高风险" : "可控"
  }))
}

function mapIndicators(indicators = []) {
  return indicators.map((item) => ({
    id: item.id,
    name: item.indicator_name,
    indicatorCode: item.indicator_code || "",
    value: String(item.value),
    unit: item.unit || "",
    range: item.reference_range || "-",
    status: item.status || item.result_status || "normal",
    riskLevel: item.risk_level || "low",
    result: item.status === "high" ? "偏高" : item.status === "low" ? "偏低" : item.status === "abnormal" ? "异常" : "正常"
  }))
}

function shortDate(dateText) {
  const [, month, day] = dateText.split("-")
  return `${Number(month)}/${Number(day)}`
}

function trendOption(points) {
  return {
    animation: true,
    color: ["#0f766e", "#38bdf8", "#f59e0b"],
    tooltip: { trigger: "axis" },
    legend: { top: 4, data: ["收缩压", "舒张压", "空腹血糖"], textStyle: { color: "#475569", fontSize: 10 } },
    grid: { left: 42, right: 42, top: 44, bottom: 34 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: points.map((item) => shortDate(item.date)),
      axisLabel: { color: "#64748b", fontSize: 9, interval: points.length > 7 ? 4 : 0 },
      axisLine: { lineStyle: { color: "#cbd5e1" } }
    },
    yAxis: [
      { type: "value", name: "mmHg", min: 60, max: 180, axisLabel: { color: "#64748b", fontSize: 9 }, splitLine: { lineStyle: { color: "#eef2f7" } } },
      { type: "value", name: "mmol/L", min: 3, max: 12, axisLabel: { color: "#64748b", fontSize: 9 }, splitLine: { show: false } }
    ],
    series: [
      { name: "收缩压", type: "line", smooth: true, symbolSize: 5, data: points.map((item) => item.systolic_pressure) },
      { name: "舒张压", type: "line", smooth: true, symbolSize: 5, data: points.map((item) => item.diastolic_pressure) },
      { name: "空腹血糖", type: "line", yAxisIndex: 1, smooth: true, symbolSize: 5, data: points.map((item) => item.fasting_glucose) }
    ]
  }
}

const today = new Date()
const todayText = formatDate(today)
const calendarMeta = getCalendarMeta(todayText)

const baseAlerts = [
  { id: "local-glucose", title: "空腹血糖偏高", content: "空腹血糖高于建议范围，晚餐主食建议减量。", riskLevel: "medium", isRead: false },
  { id: "local-pressure", title: "血压需要关注", content: "收缩压接近 140 mmHg，今晚建议低盐饮食并复测。", riskLevel: "medium", isRead: false }
]

Page({
  data: {
    currentRecordId: null,
    canCreateRecord: false,
    isCreatingRecord: false,
    ec: { lazyLoad: true },
    chartReady: false,
    trendLoading: true,
    trendError: "",
    trendRange: "7d",
    trendPoints: [],
    reportEditMode: false,
    isSavingReport: false,
    reportStatusOptions: ["正常", "偏高", "偏低", "异常"],
    reportStatusValues: ["normal", "high", "low", "abnormal"],
    currentReportDetail: null,
    isBackendConnected: false,
    selectedDate: todayText,
    calendarTitle: calendarMeta.title,
    calendarLunar: calendarMeta.lunar || "七月初五",
    monthLabel: "2026年8月",
    showCalendarModal: false,
    activePanel: "overview",
    completionRate: 86,
    healthScore: 82,
    isSavingVitals: false,
    isSavingNote: false,
    moodOptions: ["平稳", "愉快", "疲惫", "焦虑", "不适"],
    noteForm: {
      mood: "平稳",
      note: ""
    },
    showMealForm: false,
    mealTypeNames: ["早餐", "午餐", "晚餐", "加餐"],
    vitalForm: {
      systolic_pressure: "",
      diastolic_pressure: "",
      fasting_glucose: "",
      postprandial_glucose: "",
      weight_kg: ""
    },
    mealForm: {
      editingId: null,
      meal_type: "breakfast",
      meal_name: "早餐",
      food_name: "",
      amount: "",
      calories: "",
      sugar: "",
      fat: "",
      salt: ""
    },
    calendarDays: buildCalendar(today),
    monthWeekdays,
    monthCalendar,
    monthSummary: [
      { label: "本月记录", value: "18天" },
      { label: "连续打卡", value: "6天" },
      { label: "异常次数", value: "5次" }
    ],
    panels: [
      { key: "overview", name: "概览" },
      { key: "diet", name: "饮食" },
      { key: "trend", name: "趋势" },
      { key: "report", name: "报告" }
    ],
    records: {
      bloodPressure: "138/86",
      fastingGlucose: "6.8",
      postMealGlucose: "8.6",
      weight: "74",
      bmi: "25.1",
      sleep: "6.5h",
      water: "1500ml",
      steps: "6200",
      vitals: [
        { label: "收缩压", value: "138", unit: "mmHg", status: "偏高", warn: true },
        { label: "舒张压", value: "86", unit: "mmHg", status: "关注", warn: true },
        { label: "空腹血糖", value: "6.8", unit: "mmol/L", status: "预警", warn: true },
        { label: "餐后血糖", value: "8.6", unit: "mmol/L", status: "可控", warn: false }
      ],
      forms: [
        { label: "晨间血压", value: "138/86", unit: "mmHg", placeholder: "输入血压" },
        { label: "空腹血糖", value: "6.8", unit: "mmol/L", placeholder: "输入血糖" },
        { label: "餐后血糖", value: "8.6", unit: "mmol/L", placeholder: "输入血糖" },
        { label: "今日体重", value: "74", unit: "kg", placeholder: "输入体重" }
      ],
      meals: [
        { name: "早餐", text: "燕麦粥、鸡蛋、无糖豆浆", calories: "390 kcal", sugar: "8g", salt: "0.8g", tag: "已记录" },
        { name: "午餐", text: "糙米饭、清蒸鱼、青菜、番茄汤", calories: "620 kcal", sugar: "18g", salt: "1.9g", tag: "已记录" },
        { name: "晚餐", text: "杂粮馒头、鸡胸肉、凉拌黄瓜", calories: "410 kcal", sugar: "11g", salt: "1.4g", tag: "待确认" }
      ],
      nutrition: [
        { label: "热量", value: "1420 kcal", progress: 78, progressStyle: "width: 78%;", warn: false },
        { label: "糖分", value: "52 g", progress: 68, progressStyle: "width: 68%;", warn: false },
        { label: "脂肪", value: "38 g", progress: 64, progressStyle: "width: 64%;", warn: false },
        { label: "盐分", value: "4.6 g", progress: 92, progressStyle: "width: 92%;", warn: true }
      ],
      tasks: [
        { id: "bp", name: "晨间血压", done: true },
        { id: "glucose", name: "空腹血糖", done: true },
        { id: "meal", name: "三餐饮食", done: true },
        { id: "night", name: "晚间复测", done: false },
        { id: "medicine", name: "用药打卡", done: true }
      ],
      summaryCards: [
        { title: "今日小结", desc: "血糖偏高与晚餐主食相关性较强，建议晚餐主食减量并继续饭后步行。" },
        { title: "记录建议", desc: "今晚补录晚间血压，并在明早继续记录空腹血糖，方便预测模型判断趋势。" }
      ],
      trendBars: [
        { day: "8/11", bp: 112, sugar: 78 },
        { day: "8/12", bp: 128, sugar: 86 },
        { day: "8/13", bp: 144, sugar: 104 },
        { day: "8/14", bp: 136, sugar: 96 },
        { day: "8/15", bp: 124, sugar: 88 },
        { day: "8/16", bp: 132, sugar: 100 },
        { day: "今日", bp: 140, sugar: 110 }
      ],
      reports: [
        { name: "空腹血糖", value: "6.8 mmol/L", range: "3.9-6.1", result: "偏高" },
        { name: "总胆固醇", value: "5.9 mmol/L", range: "< 5.2", result: "偏高" },
        { name: "甘油三酯", value: "1.6 mmol/L", range: "< 1.7", result: "正常" }
      ],
      uploadOptionsVisible: false,
      hasReportFile: false,
      isRecognizing: false,
      ocrProgress: 0,
      ocrProgressStyle: "width: 0%;",
      selectedReport: {
        name: "暂未选择报告图片",
        type: "图片",
        size: "-",
        source: "待选择",
        status: "未上传",
        confidence: "待计算",
        preview: "点击上传框选择报告图片或直接拍照"
      },
      uploadHistory: [
        { name: "体检报告.pdf", type: "PDF", time: "今日 09:20", status: "待复核" },
        { name: "血脂检查单.jpg", type: "图片", time: "8/12 18:40", status: "已归档" }
      ],
      predictionList: [
        { date: "明日", bp: "136/84", glucose: "6.5", level: "中风险" },
        { date: "后天", bp: "134/83", glucose: "6.3", level: "关注" },
        { date: "第 3 天", bp: "132/82", glucose: "6.1", level: "可控" }
      ],
      alerts: baseAlerts
    }
  },
  onLoad() {
    this.loadDailyRecord(todayText)
    this.loadCalendarMarks(todayText)
    this.loadTrendData()
    this.loadPredictionData()
    this.loadReportHistory()
  },
  onReady() {
    this.initTrendChart()
  },
  initTrendChart() {
    if (this.data.activePanel !== "trend" || trendChart) return
    const component = this.selectComponent("#vitals-trend-chart")
    if (!component) return
    component.init((canvas, width, height, dpr) => {
      trendChart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr })
      canvas.setChart(trendChart)
      this.setData({ chartReady: true })
      this.renderTrendChart()
      return trendChart
    })
  },
  renderTrendChart() {
    if (!trendChart) return
    if (!this.data.trendPoints.length) {
      trendChart.clear()
      return
    }
    trendChart.setOption(trendOption(this.data.trendPoints), true)
  },
  loadDailyRecord(date) {
    const requestTask = date === todayText ? api.getTodayRecord() : api.getDailyRecord(date)

    requestTask.then((response) => {
      if (response.code !== 0) {
        this.applyNoRecord(date)
        return
      }

      this.applyDailyPayload(response.data)
    }).catch(() => {
      wx.showToast({
        title: "后端未连接，显示本地演示",
        icon: "none"
      })
    })
  },
  applyDailyPayload(payload) {
    const record = payload.record || {}
    const vitals = payload.vitals || {}
    const nutrition = payload.nutrition || {}
    const tasks = payload.tasks || []
    const alerts = payload.alerts || []
    const date = record.record_date || this.data.selectedDate
    const meta = getCalendarMeta(date)
    const pressure = vitals.systolic_pressure && vitals.diastolic_pressure ? `${vitals.systolic_pressure}/${vitals.diastolic_pressure}` : "-"

    this.setData({
      currentRecordId: record.id || null,
      canCreateRecord: false,
      isBackendConnected: true,
      selectedDate: date,
      calendarTitle: meta.title,
      calendarLunar: meta.lunar || "暂无农历信息",
      completionRate: record.completion_rate || 0,
      healthScore: record.health_score || 82,
      noteForm: {
        mood: record.mood || "平稳",
        note: record.note || ""
      },
      "records.bloodPressure": pressure,
      "records.fastingGlucose": vitals.fasting_glucose || "-",
      "records.postMealGlucose": vitals.postprandial_glucose || "-",
      "records.weight": vitals.weight_kg || "-",
      "records.vitals": mapVitals(vitals),
      "records.forms": mapForms(vitals),
      vitalForm: {
        systolic_pressure: String(vitals.systolic_pressure || ""),
        diastolic_pressure: String(vitals.diastolic_pressure || ""),
        fasting_glucose: String(vitals.fasting_glucose || ""),
        postprandial_glucose: String(vitals.postprandial_glucose || ""),
        weight_kg: String(vitals.weight_kg || "")
      },
      "records.nutrition": mapNutrition(nutrition),
      "records.tasks": tasks.map((task) => ({
        id: task.id,
        name: task.task_name,
        done: task.is_done
      })),
      "records.summaryCards": [
        { title: "今日小结", desc: record.summary || "今日记录已从后端读取，继续保持每日打卡。" },
        { title: "记录建议", desc: "数据已连接 Flask API，后续可替换为 MySQL 中的真实记录。" }
      ],
      "records.alerts": alerts.length ? alerts.map((alert) => ({
        id: alert.id,
        title: alert.title || "健康提醒",
        content: alert.description || alert.content || alert.title,
        riskLevel: alert.risk_level || alert.level || "low",
        isRead: Boolean(alert.is_read)
      })) : [{ id: "empty", title: "暂无异常", content: "今日暂无异常提醒。", riskLevel: "low", isRead: true }]
    })

    if (record.id) {
      this.loadMeals(record.id)
    }
  },
  applyNoRecord(date) {
    const meta = getCalendarMeta(date)
    this.setData({
      selectedDate: date,
      calendarTitle: meta.title,
      calendarLunar: meta.lunar || "暂无农历信息",
      completionRate: 0,
      currentRecordId: null,
      canCreateRecord: date <= todayText,
      noteForm: { mood: "平稳", note: "" },
      "records.vitals": mapVitals({}),
      "records.forms": mapForms({}),
      "records.meals": [],
      "records.nutrition": mapNutrition({}),
      "records.tasks": [],
      "records.alerts": [{ id: "no-record", title: "暂无记录", content: "这一天还没有记录，历史日期不会自动套用最新待办模板。", riskLevel: "low", isRead: true }]
    })
  },
  loadMeals(recordId) {
    api.getMeals(recordId).then((response) => {
      if (response.code !== 0) return

      this.setData({
        "records.meals": mapMeals(response.data.meals),
        "records.nutrition": mapNutrition(response.data.summary)
      })
    })
  },
  loadCalendarMarks(date) {
    const month = date.slice(0, 7)

    api.getCalendarMarks(month).then((response) => {
      if (response.code !== 0) return

      const marks = {}
      response.data.days.forEach((item) => {
        marks[item.date] = item
      })

      const nextCalendar = this.data.monthCalendar.map((item) => {
        const mark = marks[item.date]
        if (!mark) return item
        return {
          ...item,
          hasRecord: mark.has_record,
          completion: mark.completion_rate,
          muted: mark.has_alert
        }
      })

      const currentMonthDays = response.data.days
      this.setData({
        monthLabel: `${month.slice(0, 4)}年${Number(month.slice(5, 7))}月`,
        monthCalendar: nextCalendar,
        monthSummary: [
          { label: "本月记录", value: `${currentMonthDays.filter((item) => item.has_record).length}天` },
          { label: "连续打卡", value: "6天" },
          { label: "异常次数", value: `${currentMonthDays.filter((item) => item.has_alert).length}次` }
        ]
      })
    })
  },
  loadTrendData(range = this.data.trendRange) {
    const requestSequence = (this.trendRequestSequence || 0) + 1
    this.trendRequestSequence = requestSequence
    this.setData({ trendLoading: true, trendError: "" })
    api.getVitalsTrend(range).then((response) => {
      if (requestSequence !== this.trendRequestSequence) return
      if (response.code !== 0) throw new Error(response.message || "趋势数据加载失败")

      const points = Array.isArray(response.data && response.data.points) ? response.data.points : []

      this.setData({
        trendRange: range,
        trendPoints: points,
        "records.trendBars": points.map((item) => ({
          day: item.date === todayText ? "今日" : shortDate(item.date),
          bp: Math.max(40, Math.round(Number(item.systolic_pressure || 0) * 0.8)),
          sugar: Math.max(40, Math.round(Number(item.fasting_glucose || 0) * 16))
        }))
      }, () => this.renderTrendChart())
    }).catch((error) => {
      if (requestSequence !== this.trendRequestSequence) return
      this.setData({ trendPoints: [], trendError: error.message || "趋势数据加载失败" }, () => this.renderTrendChart())
    }).finally(() => {
      if (requestSequence === this.trendRequestSequence) this.setData({ trendLoading: false })
    })
  },
  retryTrendData() {
    this.loadTrendData(this.data.trendRange)
  },
  switchTrendRange(event) {
    const range = event.currentTarget.dataset.range
    if (range === this.data.trendRange) return
    this.loadTrendData(range)
  },
  loadPredictionData() {
    api.getVitalsPrediction(3).then((response) => {
      if (response.code !== 0) return

      this.setData({
        "records.predictionList": mapPredictions(response.data.predictions)
      })
    })
  },
  loadReportHistory() {
    api.getReportHistory().then((response) => {
      if (response.code !== 0) return

      this.setData({
        "records.uploadHistory": response.data.items.map((item) => ({
          id: item.id,
          name: item.file_name,
          type: item.file_name.endsWith(".pdf") ? "PDF" : "图片",
          time: item.report_date,
          status: item.status === "review_pending" ? "待复核" : "已归档"
        }))
      })

      if (response.data.items[0]) {
        this.loadReportDetail(response.data.items[0].id)
      }
    })
  },
  loadReportIndicators(reportId) {
    api.getReportIndicators(reportId).then((response) => {
      if (response.code !== 0) return
      this.setData({
        "records.reports": mapIndicators(response.data)
      })
    })
  },
  openReportDetail(event) {
    const reportId = Number(event.currentTarget.dataset.id)
    this.loadReportDetail(reportId)
  },
  loadReportDetail(reportId) {
    Promise.all([api.getReportDetail(reportId), api.getReportIndicators(reportId)]).then(([detailResponse, indicatorResponse]) => {
      if (detailResponse.code !== 0 || indicatorResponse.code !== 0) throw new Error("报告详情加载失败")
      const detail = detailResponse.data
      this.setData({
        currentReportDetail: detail,
        reportEditMode: false,
        "records.hasReportFile": true,
        "records.selectedReport.reportId": reportId,
        "records.selectedReport.name": detail.file_name,
        "records.selectedReport.type": detail.file_type === "pdf" ? "PDF" : "图片",
        "records.selectedReport.source": "历史报告",
        "records.selectedReport.status": detail.status,
        "records.selectedReport.confidence": detail.confidence == null ? "待计算" : `${Math.round(detail.confidence * 100)}%`,
        "records.selectedReport.preview": detail.summary || "暂无报告摘要",
        "records.reports": mapIndicators(indicatorResponse.data)
      })
    }).catch((error) => wx.showToast({ title: error.message, icon: "none" }))
  },
  toggleReportEdit() {
    this.setData({ reportEditMode: !this.data.reportEditMode })
  },
  editReportIndicator(event) {
    const index = Number(event.currentTarget.dataset.index)
    const field = event.currentTarget.dataset.field
    this.setData({ [`records.reports[${index}].${field}`]: event.detail.value })
  },
  changeReportStatus(event) {
    const index = Number(event.currentTarget.dataset.index)
    const optionIndex = Number(event.detail.value)
    const status = this.data.reportStatusValues[optionIndex]
    const labels = { normal: "正常", high: "偏高", low: "偏低", abnormal: "异常" }
    this.setData({ [`records.reports[${index}].status`]: status, [`records.reports[${index}].result`]: labels[status] })
  },
  saveReportCorrections() {
    const reportId = this.data.records.selectedReport.reportId
    if (!reportId || this.data.isSavingReport) return
    const items = this.data.records.reports.map((item) => ({
      indicator_name: item.name,
      indicator_code: item.indicatorCode,
      value: item.value,
      unit: item.unit,
      reference_range: item.range,
      status: item.status,
      risk_level: item.status === "normal" ? "low" : item.riskLevel === "high" ? "high" : "medium"
    }))
    this.setData({ isSavingReport: true })
    api.updateReportIndicators(reportId, items).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({ reportEditMode: false, "records.reports": mapIndicators(response.data) })
      wx.showToast({ title: "指标纠正已保存", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
      .finally(() => this.setData({ isSavingReport: false }))
  },
  confirmCurrentReport() {
    const reportId = this.data.records.selectedReport.reportId
    if (!reportId || !this.data.records.reports.length) {
      wx.showToast({ title: "暂无可确认指标", icon: "none" })
      return
    }
    api.confirmReport(reportId, "用户已核对报告指标").then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({ currentReportDetail: response.data, "records.selectedReport.status": "completed", "records.selectedReport.preview": response.data.summary })
      this.loadReportHistory()
      wx.showToast({ title: "报告已确认", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "确认失败", icon: "none" }))
  },
  rerecognizeCurrentReport() {
    if (!this.data.records.selectedReport.reportId) return
    this.startOcrDemo()
  },
  deleteCurrentReport() {
    const reportId = this.data.records.selectedReport.reportId
    if (!reportId) return
    wx.showModal({ title: "删除报告", content: "报告文件和识别指标将一并删除，是否继续？", success: ({ confirm }) => {
      if (!confirm) return
      api.deleteReport(reportId).then((response) => {
        if (response.code !== 0) throw new Error(response.message)
        this.setData({
          currentReportDetail: null,
          reportEditMode: false,
          "records.hasReportFile": false,
          "records.reports": [],
          "records.selectedReport": { name: "暂未选择报告图片", type: "图片", size: "-", source: "待选择", status: "未上传", confidence: "待计算", preview: "点击上传框选择报告图片或直接拍照" }
        })
        this.loadReportHistory()
        wx.showToast({ title: "报告已删除", icon: "success" })
      }).catch((error) => wx.showToast({ title: error.message || "删除失败", icon: "none" }))
    } })
  },
  selectDate(event) {
    const { date } = event.currentTarget.dataset
    this.applySelectedDate(date)
  },
  selectMonthDate(event) {
    const { date } = event.currentTarget.dataset
    this.applySelectedDate(date)
    this.setData({
      showCalendarModal: false
    })
  },
  applySelectedDate(date) {
    const selected = this.data.monthCalendar.find((item) => item.date === date) || this.data.calendarDays.find((item) => item.date === date)
    const hasRecord = selected ? selected.hasRecord : false
    const completionRate = selected ? selected.completion : 0
    const meta = getCalendarMeta(date)
    const nextData = {
      selectedDate: date,
      calendarTitle: meta.title,
      calendarLunar: meta.lunar || "暂无农历信息",
      completionRate,
      "records.meals[2].tag": hasRecord ? "待确认" : "无记录",
      "records.alerts": hasRecord ? baseAlerts : [{ id: "incomplete", title: "记录不完整", content: "这一天还没有完整记录，可补录饮食、血压、血糖和用药。", riskLevel: "low", isRead: true }]
    }

    if (this.data.records.tasks[3]) {
      nextData["records.tasks[3].done"] = false
    }

    this.setData(nextData)
    this.loadDailyRecord(date)
  },
  createSelectedRecord() {
    if (!this.data.canCreateRecord || this.data.isCreatingRecord) return
    wx.showModal({
      title: "开始补录",
      content: `创建 ${this.data.selectedDate} 的健康记录，并使用当天有效的待办模板。`,
      success: ({ confirm }) => {
        if (!confirm) return
        this.setData({ isCreatingRecord: true })
        api.createDailyRecord(this.data.selectedDate).then((response) => {
          if (response.code !== 0) throw new Error(response.message)
          this.applyDailyPayload(response.data)
          this.loadCalendarMarks(this.data.selectedDate)
          wx.showToast({ title: "记录已创建", icon: "success" })
        }).catch((error) => wx.showToast({ title: error.message || "创建失败", icon: "none" }))
          .finally(() => this.setData({ isCreatingRecord: false }))
      }
    })
  },
  openCalendarModal() {
    this.setData({
      showCalendarModal: true
    })
  },
  closeCalendarModal() {
    this.setData({
      showCalendarModal: false
    })
  },
  noop() {},
  switchPanel(event) {
    const nextPanel = event.currentTarget.dataset.panel
    if (nextPanel === this.data.activePanel) return

    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }

    this.setData({
      activePanel: nextPanel,
      chartReady: false
    }, () => {
      if (nextPanel !== "trend") return
      wx.nextTick(() => this.initTrendChart())
    })
  },
  editVital(event) {
    const field = event.currentTarget.dataset.field
    this.setData({ [`vitalForm.${field}`]: event.detail.value })
  },
  saveVitals() {
    if (!this.data.currentRecordId || this.data.isSavingVitals) return
    const form = this.data.vitalForm
    const systolic = Number(form.systolic_pressure)
    const diastolic = Number(form.diastolic_pressure)
    const fasting = Number(form.fasting_glucose)
    const postprandial = Number(form.postprandial_glucose)
    const weight = Number(form.weight_kg)
    if (systolic < 60 || systolic > 260 || diastolic < 30 || diastolic > 160 || fasting < 1 || fasting > 40 || postprandial < 1 || postprandial > 40 || weight < 20 || weight > 300) {
      wx.showToast({ title: "请检查录入数值范围", icon: "none" })
      return
    }
    this.setData({ isSavingVitals: true })
    api.updateVitals(this.data.currentRecordId, {
      systolic_pressure: systolic,
      diastolic_pressure: diastolic,
      fasting_glucose: fasting,
      postprandial_glucose: postprandial,
      weight_kg: weight
    }).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      wx.showToast({ title: "今日指标已保存", icon: "success" })
      this.loadDailyRecord(this.data.selectedDate)
      this.loadTrendData()
    }).catch((error) => {
      wx.showToast({ title: error.message || "保存失败", icon: "none" })
    }).finally(() => this.setData({ isSavingVitals: false }))
  },
  chooseMood(event) {
    this.setData({ "noteForm.mood": this.data.moodOptions[Number(event.detail.value)] })
  },
  editDailyNote(event) {
    this.setData({ "noteForm.note": event.detail.value })
  },
  saveDailyNote() {
    if (!this.data.currentRecordId || this.data.isSavingNote) return
    if (this.data.noteForm.note.length > 500) {
      wx.showToast({ title: "备注不能超过500字", icon: "none" })
      return
    }
    this.setData({ isSavingNote: true })
    api.updateDailyRecord(this.data.currentRecordId, this.data.noteForm).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      wx.showToast({ title: "状态与备注已保存", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
      .finally(() => this.setData({ isSavingNote: false }))
  },
  markAlertRead(event) {
    const index = Number(event.currentTarget.dataset.index)
    const alert = this.data.records.alerts[index]
    if (!alert || alert.isRead || typeof alert.id !== "number") return
    api.markAlertRead(alert.id).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({ [`records.alerts[${index}].isRead`]: true })
      wx.showToast({ title: "已标记为已读", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "操作失败", icon: "none" }))
  },
  toggleMealForm() {
    const nextVisible = !this.data.showMealForm
    this.setData({
      showMealForm: nextVisible,
      mealForm: nextVisible ? { editingId: null, meal_type: "breakfast", meal_name: "早餐", food_name: "", amount: "", calories: "", sugar: "", fat: "", salt: "" } : this.data.mealForm
    })
  },
  editMealField(event) {
    const field = event.currentTarget.dataset.field
    this.setData({ [`mealForm.${field}`]: event.detail.value })
  },
  chooseMealType(event) {
    const types = ["breakfast", "lunch", "dinner", "extra"]
    const names = ["早餐", "午餐", "晚餐", "加餐"]
    const index = Number(event.detail.value)
    this.setData({ "mealForm.meal_type": types[index], "mealForm.meal_name": names[index] })
  },
  saveMeal() {
    const form = this.data.mealForm
    if (!this.data.currentRecordId || !form.food_name.trim()) {
      wx.showToast({ title: "请输入食物名称", icon: "none" })
      return
    }
    const payload = {
      meal_type: form.meal_type,
      meal_name: form.meal_name,
      foods: [{
        name: form.food_name.trim(),
        amount: form.amount.trim(),
        calories: Number(form.calories || 0),
        sugar: Number(form.sugar || 0),
        fat: Number(form.fat || 0),
        salt: Number(form.salt || 0)
      }]
    }
    const requestTask = form.editingId
      ? api.updateMeal(form.editingId, payload)
      : api.addMeal(this.data.currentRecordId, payload)
    requestTask.then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({
        showMealForm: false,
        mealForm: { editingId: null, meal_type: "breakfast", meal_name: "早餐", food_name: "", amount: "", calories: "", sugar: "", fat: "", salt: "" }
      })
      this.loadMeals(this.data.currentRecordId)
      wx.showToast({ title: form.editingId ? "饮食已更新" : "饮食已保存", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
  },
  editMeal(event) {
    const mealId = Number(event.currentTarget.dataset.id)
    const meal = this.data.records.meals.find((item) => item.id === mealId)
    if (!meal) return
    const food = meal.firstFood || {}
    this.setData({
      showMealForm: true,
      mealForm: {
        editingId: meal.id,
        meal_type: meal.mealType || "extra",
        meal_name: meal.name,
        food_name: food.name || "",
        amount: food.amount || "",
        calories: String(food.calories || ""),
        sugar: String(food.sugar || ""),
        fat: String(food.fat || ""),
        salt: String(food.salt || "")
      }
    })
  },
  cancelMealEdit() {
    this.setData({ showMealForm: false, "mealForm.editingId": null })
  },
  deleteMeal(event) {
    const mealId = Number(event.currentTarget.dataset.id)
    wx.showModal({
      title: "删除饮食记录",
      content: "确定删除这一餐吗？",
      success: ({ confirm }) => {
        if (!confirm) return
        api.deleteMeal(mealId).then((response) => {
          if (response.code === 0) this.loadMeals(this.data.currentRecordId)
        })
      }
    })
  },
  editTaskName(event) {
    const index = Number(event.currentTarget.dataset.index)
    this.setData({
      [`records.tasks[${index}].name`]: event.detail.value
    })
    this.queueTaskTemplateSync()
  },
  toggleTaskDone(event) {
    const index = Number(event.currentTarget.dataset.index)
    const task = this.data.records.tasks[index]
    const nextDone = !task.done

    this.setData({
      [`records.tasks[${index}].done`]: nextDone
    })

    if (typeof task.id === "number") {
      api.updateDailyTask(task.id, { is_done: nextDone }).then((response) => {
        if (response.code !== 0) {
          this.setData({
            [`records.tasks[${index}].done`]: task.done
          })
        }
      })
    }
  },
  addTaskItem() {
    const nextTasks = this.data.records.tasks.concat({
      id: `custom-${Date.now()}`,
      name: "新增待办",
      done: false
    })

    this.setData({
      "records.tasks": nextTasks
    })
    this.queueTaskTemplateSync()
  },
  deleteTaskItem(event) {
    const index = Number(event.currentTarget.dataset.index)
    const nextTasks = this.data.records.tasks.filter((_, itemIndex) => itemIndex !== index)

    this.setData({
      "records.tasks": nextTasks
    })
    this.queueTaskTemplateSync()
  },
  queueTaskTemplateSync() {
    if (this.taskSyncTimer) {
      clearTimeout(this.taskSyncTimer)
    }

    this.taskSyncTimer = setTimeout(() => {
      const items = this.data.records.tasks
        .filter((task) => task.name)
        .map((task, index) => ({
          task_name: task.name,
          sort_order: index + 1
        }))

      api.updateTaskTemplate({
        effective_date: this.data.selectedDate,
        items
      }).then((response) => {
        if (response.code === 0) {
          this.loadDailyRecord(this.data.selectedDate)
        }
      })
    }, 700)
  },
  toggleUploadOptions() {
    this.setData({
      "records.uploadOptionsVisible": !this.data.records.uploadOptionsVisible
    })
  },
  handleReportImage(file, source, reportType = "图片") {
    if (this.ocrTimer) {
      clearInterval(this.ocrTimer)
      this.ocrTimer = null
    }

    const filePath = file.tempFilePath || ""
    const pathParts = filePath.split("/")
    const fallbackName = reportType === "PDF" ? "体检报告.pdf" : source === "拍照" ? "拍照体检报告.jpg" : "体检报告图片.jpg"

    this.setData({
      "records.uploadOptionsVisible": false,
      "records.hasReportFile": true,
      "records.isRecognizing": false,
      "records.ocrProgress": 0,
      "records.ocrProgressStyle": "width: 0%;",
      "records.selectedReport": {
        name: pathParts[pathParts.length - 1] || fallbackName,
        type: reportType,
        size: formatFileSize(file.size),
        source,
        status: "上传中",
        confidence: "待计算",
        preview: "正在上传到 Flask 后端"
      }
    })

    const uploadSource = reportType === "PDF" ? "pdf" : source === "拍照" ? "camera" : "album"
    api.uploadReport(filePath, uploadSource, this.data.selectedDate).then((response) => {
      if (response.code !== 0) {
        this.setData({
          "records.selectedReport.status": "上传失败",
          "records.selectedReport.preview": response.message || "请检查后端接口是否启动"
        })
        return
      }

      this.setData({
        "records.selectedReport.reportId": response.data.report_id,
        "records.selectedReport.status": "待识别",
        "records.selectedReport.preview": "已上传到后端，点击开始识别后读取 OCR 进度"
      })
      this.loadReportHistory()
    }).catch(() => {
      this.setData({
        "records.selectedReport.status": "上传失败",
        "records.selectedReport.preview": "后端未连接，请确认 localhost:5000 已启动"
      })
    })
  },
  chooseAlbumReport() {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album"],
      success: (res) => {
        const file = res.tempFiles[0]
        this.handleReportImage(file, "相册图片")
      },
      fail: () => {
        wx.showToast({
          title: "未选择图片",
          icon: "none"
        })
      }
    })
  },
  takePhotoReport() {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["camera"],
      success: (res) => {
        const file = res.tempFiles[0]
        this.handleReportImage(file, "拍照")
      },
      fail: () => {
        wx.showToast({
          title: "未拍照",
          icon: "none"
        })
      }
    })
  },
  choosePdfReport() {
    wx.chooseMessageFile({
      count: 1,
      type: "file",
      extension: ["pdf"],
      success: (res) => {
        const file = res.tempFiles[0]
        this.handleReportImage({ tempFilePath: file.path, size: file.size }, "聊天文件", "PDF")
      },
      fail: () => wx.showToast({ title: "未选择 PDF", icon: "none" })
    })
  },
  startOcrDemo() {
    if (!this.data.records.hasReportFile) {
      wx.showToast({
        title: "请先上传报告",
        icon: "none"
      })
      return
    }

    const reportId = this.data.records.selectedReport.reportId
    if (!reportId) {
      wx.showToast({
        title: "请等待文件上传完成",
        icon: "none"
      })
      return
    }

    if (this.ocrTimer) {
      clearInterval(this.ocrTimer)
      this.ocrTimer = null
    }

    this.setData({
      "records.isRecognizing": true,
      "records.ocrProgress": 8,
      "records.ocrProgressStyle": "width: 8%;",
      "records.reports": [],
      "records.selectedReport.status": "识别中",
      "records.selectedReport.confidence": "计算中",
      "records.selectedReport.preview": "正在请求后端 OCR 识别接口"
    })

    api.startReportRecognize(reportId).then((startResponse) => {
      if (startResponse.code !== 0) throw new Error(startResponse.message || "识别启动失败")
      this.ocrTimer = setInterval(() => {
        api.getReportProgress(reportId).then((response) => {
          if (response.code !== 0) throw new Error(response.message || "识别进度查询失败")
          const progress = Number(response.data.progress || 0)
          const done = progress >= 100 || ["review_pending", "completed"].includes(response.data.status)
          const nextData = {
            "records.ocrProgress": progress,
            "records.ocrProgressStyle": `width: ${Math.max(0, Math.min(progress, 100))}%;`,
            "records.selectedReport.status": done ? "识别完成" : "识别中",
            "records.selectedReport.preview": response.data.message || "正在提取报告指标"
          }

          if (done) {
            clearInterval(this.ocrTimer)
            this.ocrTimer = null
            nextData["records.isRecognizing"] = false
            nextData["records.selectedReport.confidence"] = "92%"
            this.loadReportIndicators(reportId)
            this.loadReportHistory()
            wx.showToast({
              title: "OCR 识别完成",
              icon: "success"
            })
          }

          this.setData(nextData)
        }).catch((error) => {
          clearInterval(this.ocrTimer)
          this.ocrTimer = null
          this.setData({
            "records.isRecognizing": false,
            "records.selectedReport.status": "识别失败",
            "records.selectedReport.preview": error.message || "识别进度查询失败"
          })
        })
      }, 800)
    }).catch((error) => {
      this.setData({
        "records.isRecognizing": false,
        "records.selectedReport.status": "识别失败",
        "records.selectedReport.preview": error.message || "识别启动失败"
      })
      wx.showToast({ title: error.message || "识别启动失败", icon: "none" })
    })
  },
  onUnload() {
    if (this.ocrTimer) {
      clearInterval(this.ocrTimer)
      this.ocrTimer = null
    }
    if (this.taskSyncTimer) {
      clearTimeout(this.taskSyncTimer)
      this.taskSyncTimer = null
    }
    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }
  },
  showDemoToast() {
    wx.showToast({
      title: "静态 demo，后续接入 API 保存",
      icon: "none"
    })
  }
})
