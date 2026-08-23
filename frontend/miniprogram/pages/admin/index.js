Page({
  data: {
    stats: [
      { label: "用户总数", value: "128" },
      { label: "中高风险", value: "34" },
      { label: "待审核报告", value: "12" },
      { label: "公告", value: "5" }
    ],
    users: [
      { name: "李明", type: "高血压 + 高血糖", risk: "中风险", active: "今日活跃" },
      { name: "王女士", type: "高血脂", risk: "关注", active: "昨日活跃" },
      { name: "陈先生", type: "高血压", risk: "高风险", active: "3 天未记录" }
    ],
    modules: [
      { title: "健康数据维护", desc: "维护血压、血糖、血脂、BMI 等记录。" },
      { title: "饮食数据维护", desc: "维护食物热量、糖分、脂肪、盐分基础库。" },
      { title: "报告审核", desc: "复核 OCR 识别低置信度或异常指标。" },
      { title: "系统公告", desc: "发布复查提醒、饮食提醒、系统维护通知。" }
    ]
  }
})
