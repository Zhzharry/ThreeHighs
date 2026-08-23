Page({
  data: {
    current: {
      systolic: 138,
      diastolic: 86,
      fasting: 6.8,
      afterMeal: 8.6
    },
    records: [
      { day: "8/11", systolic: 132, fasting: 6.2, bpHeight: 110, sugarHeight: 86 },
      { day: "8/12", systolic: 136, fasting: 6.4, bpHeight: 126, sugarHeight: 92 },
      { day: "8/13", systolic: 140, fasting: 6.7, bpHeight: 148, sugarHeight: 104 },
      { day: "8/14", systolic: 139, fasting: 6.5, bpHeight: 138, sugarHeight: 96 },
      { day: "8/15", systolic: 134, fasting: 6.3, bpHeight: 118, sugarHeight: 88 },
      { day: "8/16", systolic: 137, fasting: 6.6, bpHeight: 132, sugarHeight: 100 },
      { day: "今日", systolic: 138, fasting: 6.8, bpHeight: 140, sugarHeight: 110 }
    ],
    predictions: [
      { date: "明日", bp: "136/84 mmHg", sugar: "6.5 mmol/L", level: "中风险" },
      { date: "后天", bp: "134/83 mmHg", sugar: "6.3 mmol/L", level: "关注" },
      { date: "第 3 天", bp: "132/82 mmHg", sugar: "6.1 mmol/L", level: "可控" }
    ],
    alerts: [
      { title: "空腹血糖偏高", desc: "近期空腹血糖均高于 6.1 mmol/L，建议控制晚餐主食量并保持睡眠规律。", level: "中风险" },
      { title: "收缩压波动", desc: "收缩压多次接近 140 mmHg，建议晚间复测并减少高盐食物。", level: "关注" }
    ]
  }
})
