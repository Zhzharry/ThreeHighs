Page({
  data: {
    steps: [
      { title: "上传报告", desc: "支持图片或 PDF 格式体检报告", active: true },
      { title: "OCR 识别", desc: "OpenCV 预处理 + PaddleOCR 提取文本", active: true },
      { title: "指标抽取", desc: "自动识别血糖、血脂、肝肾功能等字段", active: true },
      { title: "异常判断", desc: "按医学参考范围给出风险等级", active: false }
    ],
    indicators: [
      { name: "空腹血糖", value: "6.8 mmol/L", range: "3.9-6.1", result: "偏高" },
      { name: "总胆固醇", value: "5.9 mmol/L", range: "< 5.2", result: "偏高" },
      { name: "甘油三酯", value: "1.6 mmol/L", range: "< 1.7", result: "正常" },
      { name: "尿酸", value: "416 umol/L", range: "208-428", result: "正常" }
    ],
    review: {
      status: "待管理员复核",
      confidence: "92%",
      note: "空腹血糖和总胆固醇已标记为异常，建议复查并同步到健康档案。"
    }
  },
  showMockToast() {
    wx.showToast({
      title: "静态演示，暂未接入上传接口",
      icon: "none"
    })
  }
})
