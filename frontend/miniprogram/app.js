const api = require("./services/api")

App({
  onLaunch() {
    this.globalData.loginState = "loading"
    api.ensureLogin().then(() => {
      this.globalData.loginState = "ready"
      return api.getConsents()
    }).then((response) => {
      if (!response || response.code !== 0 || response.data.required_complete) return
      const pages = getCurrentPages()
      const currentRoute = pages.length ? pages[pages.length - 1].route : ""
      if (currentRoute !== "pages/consent/index") wx.reLaunch({ url: "/pages/consent/index" })
    }).catch((error) => {
      this.globalData.loginState = "error"
      this.globalData.loginError = error.message
      wx.showToast({ title: error.message || "登录失败", icon: "none" })
    })
    wx.onNetworkStatusChange(({ isConnected }) => {
      this.globalData.isNetworkConnected = isConnected
      if (!isConnected) wx.showToast({ title: "网络连接已断开", icon: "none" })
    })
  },
  globalData: {
    loginState: "idle",
    loginError: "",
    isNetworkConnected: true,
    userName: "李明",
    healthScore: 82,
    riskLevel: "中风险",
    lastSyncText: "今日 08:30"
  }
})
