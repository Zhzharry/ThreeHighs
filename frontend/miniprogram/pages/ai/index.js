const api = require("../../services/api")

const presetAnswers = {
  "晚饭怎么吃": "晚餐主食建议控制在半碗左右，优先选择杂粮、豆制品和深色蔬菜，饭后散步 20-30 分钟。",
  "血压偏高怎么办": "建议今晚低盐饮食，避免浓茶、酒精和熬夜，睡前保持安静状态复测一次。如果连续多日高于 140/90 mmHg，应咨询医生。",
  "报告异常怎么看": "空腹血糖和总胆固醇偏高，建议结合近 7 日记录观察趋势，并在下次复查前持续记录饮食、血压和血糖。"
}

function pad(value) {
  return String(value).padStart(2, "0")
}

function todayText() {
  const date = new Date()
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function messageTime(value) {
  if (!value) return "刚刚"
  return value.slice(11, 16) || "刚刚"
}

function mapMessage(item) {
  return {
    role: item.role === "user" ? "user" : "assistant",
    time: messageTime(item.created_at),
    text: item.content
  }
}

function mapRiskLevel(level) {
  if (level === "high") return "高风险"
  if (level === "medium") return "中风险"
  return "可控"
}

Page({
  data: {
    currentConversationId: null,
    isBackendConnected: false,
    isSending: false,
    currentQuestion: "晚饭怎么吃",
    messages: [
      { role: "assistant", time: "09:18", text: "我已读取你今天的血压、血糖和饮食记录，可以帮你分析风险或生成饮食计划。" },
      { role: "user", time: "09:20", text: "最近空腹血糖偏高，晚饭应该怎么吃？" },
      { role: "assistant", time: "09:20", text: presetAnswers["晚饭怎么吃"] }
    ],
    draftText: "",
    quickQuestions: ["晚饭怎么吃", "血压偏高怎么办", "报告异常怎么看"],
    chatRecords: [
      { title: "晚饭怎么吃", desc: "根据空腹血糖 6.8 生成晚餐建议", time: "今日 09:20" },
      { title: "血压偏高怎么办", desc: "解释收缩压 138 的居家处理方式", time: "昨日 21:10" },
      { title: "报告异常怎么看", desc: "解读空腹血糖和总胆固醇异常", time: "8/12 18:45" }
    ],
    contextCards: [
      { label: "已读取", value: "今日记录" },
      { label: "风险等级", value: "中风险" },
      { label: "知识库", value: "3 条命中" }
    ],
    riskSummary: [
      { label: "空腹血糖", value: "6.8", status: "中风险" },
      { label: "收缩压", value: "138", status: "关注" },
      { label: "盐分摄入", value: "4.6g", status: "接近上限" }
    ],
    suggestions: [
      { title: "今日控糖方案", desc: "晚餐主食减量 1/3，优先选择杂粮、豆腐、鱼肉和深色蔬菜。", tags: ["晚餐", "控糖"] },
      { title: "今日控压方案", desc: "避免腌制品和重口味汤汁，晚间复测血压并记录状态。", tags: ["低盐", "复测"] },
      { title: "今日运动方案", desc: "饭后 20-30 分钟散步，强度以微微出汗、不气喘为宜。", tags: ["步行", "血糖"] }
    ],
    mealPlan: [
      { name: "早餐", text: "燕麦粥 + 鸡蛋 + 无糖豆浆" },
      { name: "午餐", text: "糙米饭半碗 + 清蒸鱼 + 两份青菜" },
      { name: "晚餐", text: "杂粮馒头半个 + 鸡胸肉 + 凉拌黄瓜" }
    ],
    reminders: [
      "20:30 进行晚间血压复测。",
      "晚餐后散步 20 分钟。",
      "明早空腹血糖继续记录。"
    ],
    hits: [
      { name: "三高人群饮食原则", score: "0.89", source: "知识库: diet_guideline.md" },
      { name: "高血压居家监测建议", score: "0.84", source: "知识库: bp_monitor.md" },
      { name: "糖尿病前期生活方式干预", score: "0.81", source: "知识库: glucose_lifestyle.md" }
    ]
  },
  onLoad() {
    this.loadQuickQuestions()
    this.loadAiContext()
    this.loadConversations()
  },
  loadQuickQuestions() {
    api.getQuickQuestions().then((response) => {
      if (response.code === 0) {
        this.setData({
          quickQuestions: response.data,
          currentQuestion: response.data[0] || this.data.currentQuestion,
          isBackendConnected: true
        })
      }
    })
  },
  loadAiContext() {
    api.getAiContextToday(todayText()).then((response) => {
      if (response.code !== 0) return

      this.setData({
        contextCards: [
          { label: "已读取", value: "今日记录" },
          { label: "风险等级", value: "中风险" },
          { label: "知识库", value: "3 条命中" }
        ],
        riskSummary: response.data.risk_cards.map((item) => ({
          label: item.label,
          value: item.value,
          status: mapRiskLevel(item.level)
        }))
      })
    })
  },
  loadConversations() {
    api.getAiConversations().then((response) => {
      if (response.code !== 0) return

      const items = response.data.items || []
      this.setData({
        chatRecords: items.map((item) => ({
          id: item.id,
          title: item.title,
          desc: item.last_message || "暂无消息",
          time: messageTime(item.updated_at)
        }))
      })

      if (items[0]) {
        this.openConversation(items[0].id)
      }
    })
  },
  openConversation(conversationId) {
    api.getAiMessages(conversationId).then((response) => {
      if (response.code !== 0) return
      this.setData({
        currentConversationId: conversationId,
        messages: response.data.map(mapMessage),
        isBackendConnected: true
      })
    })
  },
  createNewConversation() {
    api.createAiConversation({
      title: "新的健康问答",
      source: "manual",
      related_date: todayText()
    }).then((response) => {
      if (response.code !== 0) return
      this.setData({
        currentConversationId: response.data.conversation_id,
        messages: [
          { role: "assistant", time: "刚刚", text: "新对话已创建，你可以从快捷问题开始咨询。" }
        ]
      })
      this.loadConversations()
    })
  },
  chooseQuestion(event) {
    const question = event.currentTarget.dataset.question
    this.setData({
      currentQuestion: question,
      draftText: question
    })
    this.sendQuestion(question)
  },
  sendQuestion(question) {
    const normalizedQuestion = String(question || "").trim()
    if (!normalizedQuestion) {
      wx.showToast({ title: "请输入问题", icon: "none" })
      return
    }
    const ensureConversation = this.data.currentConversationId
      ? Promise.resolve(this.data.currentConversationId)
      : api.createAiConversation({
        title: normalizedQuestion,
        source: "quick_question",
        related_date: todayText()
      }).then((response) => response.data.conversation_id)

    this.setData({
      isSending: true,
      draftText: "",
      currentQuestion: normalizedQuestion,
      messages: this.data.messages.concat([
        { role: "user", time: "刚刚", text: normalizedQuestion },
        { role: "assistant", time: "刚刚", text: "正在结合你的每日记录生成建议..." }
      ])
    })

    ensureConversation.then((conversationId) => {
      this.setData({
        currentConversationId: conversationId
      })
      return api.sendAiMessage(conversationId, {
        content: normalizedQuestion,
        use_daily_context: true,
        related_date: todayText()
      })
    }).then((response) => {
      if (!response || response.code !== 0) {
        throw new Error("AI 接口返回异常")
      }

      const nextMessages = this.data.messages.slice(0, -2).concat([
        mapMessage(response.data.user_message),
        mapMessage(response.data.assistant_message)
      ])

      this.setData({
        messages: nextMessages,
        contextCards: [
          { label: "已读取", value: "今日记录" },
          { label: "风险等级", value: "中风险" },
          { label: "知识库", value: `${response.data.retrieval.hit_count} 条命中` }
        ],
        hits: [
          { name: "三高人群饮食原则", score: "0.89", source: "Chroma: health_knowledge" },
          { name: "体检指标参考范围", score: "0.84", source: "Chroma: indicator_reference" },
          { name: "用户健康摘要", score: "0.81", source: "Chroma: user_health_memory" }
        ],
        isBackendConnected: true,
        isSending: false
      })
      this.loadConversations()
    }).catch(() => {
      const fallback = presetAnswers[normalizedQuestion] || "我会结合你的每日记录给出生活方式建议。当前演示接口异常，请稍后重试。"
      const nextMessages = this.data.messages.slice(0, -1).concat([
        { role: "assistant", time: "刚刚", text: fallback }
      ])
      this.setData({
        messages: nextMessages,
        isSending: false
      })
      wx.showToast({
        title: "后端未连接，显示本地回答",
        icon: "none"
      })
    })
  },
  editDraftText(event) {
    this.setData({ draftText: event.detail.value })
  },
  sendCurrentQuestion() {
    this.sendQuestion(this.data.draftText)
  },
  openConversationFromHistory(event) {
    const conversationId = Number(event.currentTarget.dataset.id)
    if (!conversationId) return
    this.openConversation(conversationId)
  },
  showDemoToast() {
    wx.showToast({
      title: "已接入后端 AI 接口",
      icon: "none"
    })
  }
})
