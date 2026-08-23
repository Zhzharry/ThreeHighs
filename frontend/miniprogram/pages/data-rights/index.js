const api = require("../../services/api")

const CATEGORY_LABELS = {
  account: "账号资料",
  health_profile: "健康档案",
  settings: "提醒设置",
  consent: "授权记录",
  daily_records: "每日记录",
  vital_records: "健康指标",
  meal_records: "饮食记录",
  task_templates: "待办模板",
  task_template_items: "模板项目",
  daily_tasks: "每日待办",
  health_alerts: "健康提醒",
  medical_reports: "体检报告",
  report_indicators: "报告指标",
  ai_conversations: "AI会话",
  ai_messages: "AI消息"
}

Page({
  data: {
    isExporting: false,
    isWithdrawing: false,
    consentComplete: false,
    consentUpdatedAt: "",
    lastExportAt: "",
    categories: Object.keys(CATEGORY_LABELS).map((key) => ({ key, label: CATEGORY_LABELS[key], count: "-" }))
  },
  onShow() {
    api.getConsents().then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({
        consentComplete: Boolean(response.data.required_complete),
        consentUpdatedAt: response.data.withdrawn_at || response.data.accepted_at || ""
      })
    }).catch((error) => wx.showToast({ title: error.message || "授权状态加载失败", icon: "none" }))
  },
  withdrawConsent() {
    if (this.data.isWithdrawing) return
    wx.showModal({
      title: "撤回健康数据授权",
      content: "撤回后，每日记录、健康趋势、体检报告和AI健康上下文将立即停用；账号资料、协议查看与个人数据导出仍可使用。你可以稍后重新授权。",
      confirmText: "确认撤回",
      confirmColor: "#b91c1c",
      success: ({ confirm }) => { if (confirm) this.withdrawConsentConfirmed() }
    })
  },
  withdrawConsentConfirmed() {
    if (this.data.isWithdrawing) return Promise.resolve()
    this.setData({ isWithdrawing: true })
    return api.withdrawHealthConsent().then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({ consentComplete: false, consentUpdatedAt: response.data.withdrawn_at || "" })
      wx.showToast({ title: "授权已撤回", icon: "success" })
      setTimeout(() => wx.reLaunch({ url: "/pages/consent/index" }), 350)
    }).catch((error) => wx.showToast({ title: error.message || "撤回失败", icon: "none" }))
      .finally(() => this.setData({ isWithdrawing: false }))
  },
  exportData() {
    if (this.data.isExporting) return
    this.setData({ isExporting: true })
    api.exportMyData().then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      const payload = response.data
      const categories = Object.keys(CATEGORY_LABELS).map((key) => ({
        key,
        label: CATEGORY_LABELS[key],
        count: payload.counts[key] || 0
      }))
      const filePath = `${wx.env.USER_DATA_PATH}/three-high-data-${Date.now()}.json`
      wx.getFileSystemManager().writeFile({
        filePath,
        data: JSON.stringify(payload, null, 2),
        encoding: "utf8",
        success: () => {
          this.setData({ categories, lastExportAt: payload.generated_at })
          if (wx.canIUse("shareFileMessage")) {
            wx.shareFileMessage({
              filePath,
              fileName: "三高健康管理-个人数据副本.json",
              fail: () => wx.showModal({ title: "数据副本已生成", content: `文件已保存在小程序临时目录：${filePath}`, showCancel: false })
            })
          } else {
            wx.showModal({ title: "数据副本已生成", content: `文件已保存在小程序临时目录：${filePath}`, showCancel: false })
          }
        },
        fail: (error) => wx.showToast({ title: error.errMsg || "文件保存失败", icon: "none" })
      })
    }).catch((error) => wx.showToast({ title: error.message || "导出失败", icon: "none" }))
      .finally(() => this.setData({ isExporting: false }))
  }
})
