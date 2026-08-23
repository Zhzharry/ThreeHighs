Page({
  data: {
    profile: {
      name: "李明",
      sex: "男",
      age: 56,
      height: 172,
      weight: 74,
      bmi: 25.1,
      type: "高血压 + 高血糖",
      history: "2 型糖尿病家族史，轻度脂肪肝",
      medication: "二甲双胍、苯磺酸氨氯地平",
      target: "控制空腹血糖低于 6.1 mmol/L，血压稳定在 130/80 mmHg 左右"
    },
    tags: ["控糖", "控压", "低盐饮食", "餐后散步", "每周复查"],
    goals: [
      { label: "体重目标", value: "70 kg", progress: 62 },
      { label: "日均盐分", value: "< 5 g", progress: 78 },
      { label: "运动频次", value: "5 次/周", progress: 70 }
    ],
    navs: [
      { title: "饮食记录", url: "/pages/diet/index" },
      { title: "血压血糖", url: "/pages/vitals/index" },
      { title: "体检报告", url: "/pages/report/index" }
    ]
  }
})
