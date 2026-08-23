Page({
  data: {
    dateText: "2026-08-17",
    nutrients: [
      { label: "热量", value: "1420 kcal", percent: 78, status: "正常" },
      { label: "糖分", value: "52 g", percent: 68, status: "可控" },
      { label: "脂肪", value: "38 g", percent: 64, status: "正常" },
      { label: "盐分", value: "4.6 g", percent: 92, status: "接近上限" }
    ],
    meals: [
      { name: "早餐", foods: "燕麦粥、鸡蛋、无糖豆浆", calories: "390 kcal", advice: "搭配优质蛋白，控糖表现较好。" },
      { name: "午餐", foods: "糙米饭、清蒸鱼、青菜、番茄汤", calories: "620 kcal", advice: "主食份量适中，建议继续保持低盐烹饪。" },
      { name: "晚餐", foods: "杂粮馒头、鸡胸肉、凉拌黄瓜", calories: "410 kcal", advice: "晚餐清淡，饭后 20 分钟散步更利于血糖稳定。" }
    ],
    tips: [
      "减少精制米面和含糖饮料，优先选择杂粮、蔬菜和优质蛋白。",
      "每日盐分建议控制在 5 g 以内，少吃腌制品和重口味外卖。",
      "血脂偏高时减少动物油和油炸食品，增加深色蔬菜摄入。"
    ]
  }
})
