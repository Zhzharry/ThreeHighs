const api = require("../../services/api")

function avatarText(name) {
  return (name || "用").slice(0, 1)
}

function maskPhone(phone) {
  const value = String(phone || "")
  return value.length === 11 ? `${value.slice(0, 3)}****${value.slice(-4)}` : value || "未填写"
}

function formatProfileItems(profile = {}) {
  return [
    { label: "性别", value: profile.gender || "" },
    { label: "年龄", value: `${profile.age || ""} 岁`.trim() },
    { label: "身高", value: `${profile.height_cm || ""} cm`.trim() },
    { label: "体重", value: `${profile.weight_kg || ""} kg`.trim() },
    { label: "BMI", value: String(profile.bmi || ""), readonly: true },
    { label: "三高类型", value: profile.disease_type || "" },
    { label: "既往病史", value: profile.medical_history || "" },
    { label: "用药", value: profile.medications || profile.medication || "" }
  ]
}

function numberValue(text) {
  const matched = String(text || "").match(/\d+(\.\d+)?/)
  return matched ? Number(matched[0]) : null
}

Page({
  data: {
    isBackendConnected: false,
    user: {
      avatar: "李",
      avatarUrl: "",
      name: "李明",
      age: 56,
      phone: "138****0926"
    },
    profileForm: { nickname: "李明", phone: "13800000926" },
    isSavingProfile: false,
    isUploadingAvatar: false,
    profileItems: [
      { label: "性别", value: "男" },
      { label: "年龄", value: "56 岁" },
      { label: "身高", value: "172 cm" },
      { label: "体重", value: "74 kg" },
      { label: "BMI", value: "25.1", readonly: true },
      { label: "三高类型", value: "高血压 + 高血糖" },
      { label: "既往病史", value: "轻度脂肪肝" },
      { label: "用药", value: "二甲双胍、氨氯地平" }
    ],
    settings: [
      { label: "异常预警推送", value: "已开启" },
      { label: "每日记录提醒", value: "20:30" }
    ],
    settingValues: {
      alert_push_enabled: true,
      daily_record_reminder_enabled: true,
      daily_record_reminder_time: "20:30"
    },
    isSavingSettings: false,
    consentStatus: { required_complete: false, accepted_at: "", versions: {} }
  },
  onLoad() {
    this.loadMineData()
  },
  loadMineData() {
    api.getMineProfile().then((response) => {
      if (response.code !== 0) return
      const user = response.data.user
      const profile = response.data.health_profile

      this.setData({
        isBackendConnected: true,
        user: {
          avatar: avatarText(user.nickname),
          avatarUrl: user.avatar_url || "",
          name: user.nickname,
          age: user.age,
          phone: user.phone_masked || maskPhone(user.phone)
        },
        profileForm: { nickname: user.nickname, phone: user.phone || "" },
        profileItems: formatProfileItems(profile)
      })
    }).catch(() => {
      wx.showToast({
        title: "后端未连接，显示本地资料",
        icon: "none"
      })
    })

    api.getSettings().then((response) => {
      if (response.code !== 0) return
      this.setData({
        settingValues: response.data,
        settings: [
          { label: "异常预警推送", value: response.data.alert_push_enabled ? "已开启" : "已关闭" },
          { label: "每日记录提醒", value: response.data.daily_record_reminder_time }
        ]
      })
    })

    api.getConsents().then((response) => {
      if (response.code === 0) this.setData({ consentStatus: response.data })
    })
  },
  saveSettings(nextValues) {
    if (this.data.isSavingSettings) return
    this.setData({ isSavingSettings: true, settingValues: nextValues })
    api.updateSettings(nextValues).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({
        settingValues: response.data,
        settings: [
          { label: "异常预警推送", value: response.data.alert_push_enabled ? "已开启" : "已关闭" },
          { label: "每日记录提醒", value: response.data.daily_record_reminder_enabled ? response.data.daily_record_reminder_time : "已关闭" }
        ]
      })
      wx.showToast({ title: "提醒设置已保存", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
      .finally(() => this.setData({ isSavingSettings: false }))
  },
  toggleAlertPush(event) {
    this.saveSettings({ ...this.data.settingValues, alert_push_enabled: event.detail.value })
  },
  toggleDailyReminder(event) {
    this.saveSettings({ ...this.data.settingValues, daily_record_reminder_enabled: event.detail.value })
  },
  changeReminderTime(event) {
    this.saveSettings({ ...this.data.settingValues, daily_record_reminder_time: event.detail.value })
  },
  editUserField(event) {
    const field = event.currentTarget.dataset.field
    this.setData({ [`profileForm.${field}`]: event.detail.value })
  },
  saveUserProfile() {
    if (this.data.isSavingProfile) return
    const nickname = this.data.profileForm.nickname.trim()
    const phone = this.data.profileForm.phone.trim()
    if (!nickname || nickname.length > 30) {
      wx.showToast({ title: "昵称长度应为1到30个字符", icon: "none" })
      return
    }
    if (phone && !/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: "请输入正确的手机号", icon: "none" })
      return
    }
    this.setData({ isSavingProfile: true })
    api.updateMineProfile({ nickname, phone }).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({
        "user.avatar": avatarText(response.data.nickname),
        "user.name": response.data.nickname,
        "user.phone": response.data.phone,
        profileForm: { nickname: response.data.nickname, phone }
      })
      wx.showToast({ title: "个人资料已保存", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
      .finally(() => this.setData({ isSavingProfile: false }))
  },
  chooseAvatar(event) {
    const filePath = event.detail.avatarUrl
    if (!filePath || this.data.isUploadingAvatar) return
    this.setData({ isUploadingAvatar: true, "user.avatarUrl": filePath })
    api.uploadMineAvatar(filePath).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      this.setData({ "user.avatarUrl": response.data.avatar_url })
      wx.showToast({ title: "头像已更新", icon: "success" })
    }).catch((error) => {
      this.setData({ "user.avatarUrl": "" })
      wx.showToast({ title: error.message || "头像上传失败", icon: "none" })
    }).finally(() => this.setData({ isUploadingAvatar: false }))
  },
  removeAvatar() {
    if (!this.data.user.avatarUrl || this.data.isUploadingAvatar) return
    wx.showModal({ title: "移除头像", content: "移除后将显示昵称首字，是否继续？", success: ({ confirm }) => {
      if (!confirm) return
      this.setData({ isUploadingAvatar: true })
      api.deleteMineAvatar().then((response) => {
        if (response.code !== 0) throw new Error(response.message)
        this.setData({ "user.avatarUrl": "" })
        wx.showToast({ title: "头像已移除", icon: "success" })
      }).catch((error) => wx.showToast({ title: error.message || "移除失败", icon: "none" }))
        .finally(() => this.setData({ isUploadingAvatar: false }))
    } })
  },
  editProfileItem(event) {
    const index = Number(event.currentTarget.dataset.index)
    this.setData({
      [`profileItems[${index}].value`]: event.detail.value
    })
  },
  saveHealthProfile() {
    const items = this.data.profileItems
    const payload = {
      gender: items[0].value,
      age: numberValue(items[1].value),
      height_cm: numberValue(items[2].value),
      weight_kg: numberValue(items[3].value),
      disease_type: items[5].value,
      medical_history: items[6].value,
      medications: items[7].value,
      chronic_types: ["hypertension", "diabetes"]
    }

    api.updateHealthProfile(payload).then((response) => {
      if (response.code !== 0) {
        wx.showToast({
          title: "保存失败",
          icon: "none"
        })
        return
      }

      this.setData({
        profileItems: formatProfileItems(response.data),
        isBackendConnected: true
      })
      wx.showToast({
        title: "已保存到后端",
        icon: "success"
      })
    }).catch(() => {
      wx.showToast({
        title: "后端未连接",
        icon: "none"
      })
    })
  },
  openLegalDocument(event) {
    wx.navigateTo({ url: `/pages/legal/index?type=${event.currentTarget.dataset.type}` })
  },
  openConsentCenter() {
    wx.navigateTo({ url: "/pages/consent/index?review=1" })
  },
  openDataRights() {
    wx.navigateTo({ url: "/pages/data-rights/index" })
  },
  showDemoToast() {
    wx.showToast({
      title: "已接入个人中心接口",
      icon: "none"
    })
  }
})
