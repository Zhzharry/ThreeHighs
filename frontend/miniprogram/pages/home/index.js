const app = getApp()

Page({
  data: {
    userName: app.globalData.userName,
    score: app.globalData.healthScore,
    riskLevel: app.globalData.riskLevel,
    lastSyncText: app.globalData.lastSyncText,
    tasks: [
      { name: "早餐记录", status: "已完成" },
      { name: "空腹血糖", status: "已完成" },
      { name: "晚间血压", status: "待记录" }
    ],
    metrics: [
      { label: "收缩压", value: "138", unit: "mmHg", tag: "偏高" },
      { label: "空腹血糖", value: "6.8", unit: "mmol/L", tag: "预警" },
      { label: "BMI", value: "25.1", unit: "", tag: "超重" },
      { label: "今日盐分", value: "4.6", unit: "g", tag: "正常" }
    ],
    features: [
      { title: "健康档案", desc: "基础信息、病史、三高类型", url: "/pages/profile/index" },
      { title: "饮食记录", desc: "三餐摄入与营养统计", url: "/pages/diet/index" },
      { title: "血压血糖", desc: "记录趋势与预测展示", url: "/pages/vitals/index" },
      { title: "体检报告", desc: "图片/PDF OCR 识别流程", url: "/pages/report/index" },
      { title: "AI 建议", desc: "个性化问答与健康方案", url: "/pages/advice/index" },
      { title: "管理员端", desc: "用户、数据、报告和公告", url: "/pages/admin/index" }
    ],
    trendBars: [
      { day: "周一", height: 118, altHeight: 82 },
      { day: "周二", height: 134, altHeight: 88 },
      { day: "周三", height: 126, altHeight: 90 },
      { day: "周四", height: 142, altHeight: 96 },
      { day: "周五", height: 136, altHeight: 86 },
      { day: "周六", height: 128, altHeight: 80 },
      { day: "今日", height: 138, altHeight: 92 }
    ],
    alerts: [
      { name: "空腹血糖", value: "6.8 mmol/L", level: "中风险", desc: "连续 3 天高于建议范围，建议减少精制主食。" },
      { name: "收缩压", value: "138 mmHg", level: "关注", desc: "晚间复测一次，避免高盐晚餐和熬夜。" }
    ]
  }
})
