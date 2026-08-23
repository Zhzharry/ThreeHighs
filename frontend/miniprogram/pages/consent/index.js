const api = require("../../services/api")

Page({
  data: {
    acceptedValues: [],
    isSaving: false,
    versions: {},
    loadError: ""
  },
  onLoad(options) {
    api.getConsents().then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({ versions: response.data.versions || {} })
      if (response.data.required_complete && options.review !== "1") wx.switchTab({ url: "/pages/daily/index" })
    }).catch((error) => this.setData({ loadError: error.message || "授权状态加载失败" }))
  },
  changeConsent(event) {
    this.setData({ acceptedValues: event.detail.value })
  },
  openDocument(event) {
    wx.navigateTo({ url: `/pages/legal/index?type=${event.currentTarget.dataset.type}` })
  },
  submitConsent() {
    if (this.data.acceptedValues.length !== 3 || this.data.isSaving) return
    this.setData({ isSaving: true })
    api.acceptConsents({
      privacy_policy_accepted: true,
      user_agreement_accepted: true,
      health_data_consent: true
    }).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      wx.showToast({ title: "授权已保存", icon: "success" })
      setTimeout(() => wx.switchTab({ url: "/pages/daily/index" }), 350)
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
      .finally(() => this.setData({ isSaving: false }))
  }
})
