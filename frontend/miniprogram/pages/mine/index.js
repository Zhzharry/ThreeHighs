const api = require("../../services/api")
const WECHAT_PROFILE_PROMPT_KEY = "mine_wechat_profile_prompted"

function avatarText(name) {
  return (name || "用").slice(0, 1)
}

function maskPhone(phone) {
  const value = String(phone || "")
  return value.length === 11 ? `${value.slice(0, 3)}****${value.slice(-4)}` : value || "未填写"
}

function profileFormFromUser(user = {}) {
  return {
    nickname: user.nickname || "",
    phone: user.phone || "",
    avatarUrl: user.avatar_url || "",
    avatarLocalPath: "",
    avatarRemoved: false
  }
}

function comparableProfileForm(form = {}) {
  return {
    nickname: String(form.nickname || "").trim(),
    phone: String(form.phone || "").trim(),
    avatarUrl: String(form.avatarUrl || "").trim()
  }
}

function comparableHealthProfileItems(items = []) {
  return items.map((item) => String(item.value || "").trim())
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
    profileForm: {
      nickname: "李明",
      phone: "13800000926",
      avatarUrl: "",
      avatarLocalPath: "",
      avatarRemoved: false
    },
    savedProfileForm: {
      nickname: "李明",
      phone: "13800000926",
      avatarUrl: ""
    },
    isProfileDirty: false,
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
    savedHealthProfileItems: ["男", "56 岁", "172 cm", "74 kg", "25.1", "高血压 + 高血糖", "轻度脂肪肝", "二甲双胍、氨氯地平"],
    isHealthProfileDirty: false,
    isSavingHealthProfile: false,
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
    setTimeout(() => this.promptWechatProfileIfNeeded(), 600)
  },
  loadMineData() {
    api.getMineProfile().then((response) => {
      if (response.code !== 0) return
      const user = response.data.user
      const profile = response.data.health_profile
      const profileForm = profileFormFromUser(user)
      const savedProfileForm = comparableProfileForm(profileForm)
      const profileItems = formatProfileItems(profile)

      this.setData({
        isBackendConnected: true,
        user: {
          avatar: avatarText(user.nickname),
          avatarUrl: profileForm.avatarUrl,
          name: user.nickname,
          age: profile.age || user.age || "",
          phone: user.phone_masked || maskPhone(profileForm.phone)
        },
        profileForm,
        savedProfileForm,
        isProfileDirty: false,
        profileItems,
        savedHealthProfileItems: comparableHealthProfileItems(profileItems),
        isHealthProfileDirty: false
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
  hasProfileChanged(profileForm = this.data.profileForm) {
    const current = comparableProfileForm(profileForm)
    const saved = comparableProfileForm(this.data.savedProfileForm)
    return current.nickname !== saved.nickname
      || current.phone !== saved.phone
      || current.avatarUrl !== saved.avatarUrl
  },
  hasHealthProfileChanged(profileItems = this.data.profileItems) {
    const current = comparableHealthProfileItems(profileItems)
    const saved = this.data.savedHealthProfileItems || []
    return current.length !== saved.length || current.some((value, index) => value !== saved[index])
  },
  applyProfileForm(profileForm) {
    const nickname = profileForm.nickname || "未填写"
    this.setData({
      profileForm,
      "user.avatar": avatarText(nickname),
      "user.avatarUrl": profileForm.avatarUrl || "",
      "user.name": nickname,
      "user.phone": maskPhone(profileForm.phone),
      isProfileDirty: this.hasProfileChanged(profileForm)
    })
  },
  promptWechatProfileIfNeeded() {
    if (wx.getStorageSync(WECHAT_PROFILE_PROMPT_KEY)) return
    wx.setStorageSync(WECHAT_PROFILE_PROMPT_KEY, true)
    wx.showModal({
      title: "完善个人资料",
      content: "是否使用微信头像和微信昵称作为个人资料？也可以稍后手动编辑。",
      confirmText: "使用",
      cancelText: "暂不",
      success: ({ confirm }) => {
        if (confirm) this.useWechatProfile()
      }
    })
  },
  useWechatProfile() {
    if (!wx.getUserProfile) {
      wx.showToast({ title: "当前基础库不支持自动获取，可手动选择头像和昵称", icon: "none" })
      return
    }
    wx.getUserProfile({
      desc: "用于完善三高健康管理个人资料",
      success: ({ userInfo }) => {
        const nickname = String(userInfo.nickName || "").trim()
        const avatarUrl = userInfo.avatarUrl || ""
        const profileForm = {
          ...this.data.profileForm,
          nickname: nickname || this.data.profileForm.nickname,
          avatarUrl: avatarUrl || this.data.profileForm.avatarUrl,
          avatarLocalPath: "",
          avatarRemoved: false
        }
        this.applyProfileForm(profileForm)
        wx.showToast({ title: "已填入微信资料，请保存", icon: "none" })
      },
      fail: () => {
        wx.showToast({ title: "未使用微信资料，可直接手动编辑", icon: "none" })
      }
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
    this.applyProfileForm({
      ...this.data.profileForm,
      [field]: event.detail.value
    })
  },
  saveUserProfile() {
    if (this.data.isSavingProfile || this.data.isUploadingAvatar || !this.data.isProfileDirty) return
    wx.showModal({
      title: "保存个人资料",
      content: "确认保存当前头像、昵称和联系方式的修改吗？",
      confirmText: "保存",
      success: ({ confirm }) => {
        if (confirm) this.commitUserProfile()
      }
    })
  },
  commitUserProfile() {
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
    const form = this.data.profileForm
    let avatarUrl = form.avatarUrl || ""
    let avatarTask = Promise.resolve()
    this.setData({ isSavingProfile: true, isUploadingAvatar: !!form.avatarLocalPath || !!form.avatarRemoved })

    if (form.avatarRemoved) {
      avatarTask = api.deleteMineAvatar().then((response) => {
        if (response.code !== 0) throw new Error(response.message)
        avatarUrl = ""
      })
    } else if (form.avatarLocalPath) {
      avatarTask = api.uploadMineAvatar(form.avatarLocalPath).then((response) => {
        if (response.code !== 0) throw new Error(response.message)
        avatarUrl = response.data.avatar_url || avatarUrl
      })
    }

    avatarTask.then(() => api.updateMineProfile({ nickname, phone, avatar_url: avatarUrl })).then((response) => {
      if (response.code !== 0) throw new Error(response.message)
      const savedProfileForm = {
        nickname: response.data.nickname,
        phone,
        avatarUrl: response.data.avatar_url || avatarUrl || ""
      }
      this.setData({
        user: {
          ...this.data.user,
          avatar: avatarText(savedProfileForm.nickname),
          avatarUrl: savedProfileForm.avatarUrl,
          name: savedProfileForm.nickname,
          phone: response.data.phone || maskPhone(savedProfileForm.phone)
        },
        profileForm: {
          ...savedProfileForm,
          avatarLocalPath: "",
          avatarRemoved: false
        },
        savedProfileForm,
        isProfileDirty: false
      })
      wx.showToast({ title: "个人资料已保存", icon: "success" })
    }).catch((error) => wx.showToast({ title: error.message || "保存失败", icon: "none" }))
      .finally(() => this.setData({ isSavingProfile: false, isUploadingAvatar: false }))
  },
  chooseAvatar(event) {
    const filePath = event.detail.avatarUrl
    if (!filePath || this.data.isSavingProfile || this.data.isUploadingAvatar) return
    this.applyProfileForm({
      ...this.data.profileForm,
      avatarUrl: filePath,
      avatarLocalPath: filePath,
      avatarRemoved: false
    })
    wx.showToast({ title: "已选择头像，请保存", icon: "none" })
  },
  editProfileItem(event) {
    const index = Number(event.currentTarget.dataset.index)
    const value = event.detail.value
    const profileItems = this.data.profileItems.map((item, itemIndex) => (
      itemIndex === index ? { ...item, value } : item
    ))
    const nextData = {
      profileItems,
      isHealthProfileDirty: this.hasHealthProfileChanged(profileItems)
    }
    if (index === 1) {
      nextData["user.age"] = numberValue(value) || ""
    }
    this.setData(nextData)
  },
  saveHealthProfile() {
    if (this.data.isSavingHealthProfile || !this.data.isHealthProfileDirty) return
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

    this.setData({ isSavingHealthProfile: true })
    api.updateHealthProfile(payload).then((response) => {
      if (response.code !== 0) {
        wx.showToast({
          title: "保存失败",
          icon: "none"
        })
        return
      }
      const profileItems = formatProfileItems(response.data)

      this.setData({
        profileItems,
        savedHealthProfileItems: comparableHealthProfileItems(profileItems),
        isHealthProfileDirty: false,
        "user.age": response.data.age || "",
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
    }).finally(() => this.setData({ isSavingHealthProfile: false }))
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
