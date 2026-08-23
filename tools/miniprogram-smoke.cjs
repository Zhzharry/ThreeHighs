const Connection = require("miniprogram-automator/out/Connection").default
const MiniProgram = require("miniprogram-automator/out/MiniProgram").default

const endpoint = process.env.MINIPROGRAM_AUTOMATION_ENDPOINT || "ws://127.0.0.1:9420"

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function inspectTab(miniProgram, route, selector, expectedText) {
  await miniProgram.switchTab(`/${route}`)
  const page = await miniProgram.currentPage()
  await page.waitFor(800)
  const element = await page.$(selector)
  assert(page.path === route, `页面路径错误：期望 ${route}，实际 ${page.path}`)
  assert(element, `${route} 缺少关键元素 ${selector}`)
  const text = await element.text()
  if (expectedText) assert(text.includes(expectedText), `${route} 关键文案不正确：${text}`)
  return { route, selector, text }
}

async function run() {
  // 新版微信开发者工具未在旧自动化协议中返回 SDKVersion，官方 SDK 的
  // connect() 会在兼容性检查阶段报错；直接复用其连接与页面协议即可继续验收。
  const connection = await Connection.create(endpoint)
  const miniProgram = new MiniProgram(connection)
  let requestMocked = false
  try {
    const results = []
    let page = await miniProgram.reLaunch("/pages/consent/index?review=1")
    await page.waitFor(800)
    const consentTitle = await page.$(".consent-title")
    assert(consentTitle, "授权页缺少 .consent-title")
    results.push({ route: page.path, selector: ".consent-title", text: await consentTitle.text() })

    page = await miniProgram.navigateTo("/pages/legal/index?type=privacy")
    await page.waitFor(300)
    const legalTitle = await page.$(".legal-title")
    assert(legalTitle && (await legalTitle.text()) === "隐私政策", "隐私政策页未正确渲染")
    results.push({ route: page.path, selector: ".legal-title", text: await legalTitle.text() })
    await miniProgram.navigateBack()

    page = await miniProgram.currentPage()
    const initialConsentData = await page.data()
    const domainCheckBlocked = String(initialConsentData.loadError || "").includes("url not in domain list")
    if (domainCheckBlocked) {
      await miniProgram.mockWxMethod("request", {
        statusCode: 200,
        data: {
          code: 0,
          message: "授权记录已保存",
          data: { required_complete: true, versions: initialConsentData.versions || {} }
        }
      })
      requestMocked = true
    }
    await page.setData({ acceptedValues: ["agreement", "privacy", "health"] })
    await page.callMethod("submitConsent")
    await new Promise((resolve) => setTimeout(resolve, 3200))
    const pageAfterConsent = await miniProgram.currentPage()
    if (domainCheckBlocked) {
      await miniProgram.restoreWxMethod("request")
      requestMocked = false
    }
    assert(
      pageAfterConsent.path === "pages/daily/index",
      `授权提交后未进入每日记录，仍停留在 ${pageAfterConsent.path}，初始页面状态 ${JSON.stringify(initialConsentData)}`
    )
    results.push({
      route: "pages/consent/index",
      selector: "wx.request",
      text: domainCheckBlocked ? "开发者工具域名校验开启，已使用小程序API mock验证交互" : "真实后端授权写入成功"
    })
    results.push(await inspectTab(miniProgram, "pages/daily/index", ".daily-title"))
    results.push(await inspectTab(miniProgram, "pages/ai/index", ".assistant-title", "健康对话助手"))
    results.push(await inspectTab(miniProgram, "pages/mine/index", ".mine-name"))

    page = await miniProgram.navigateTo("/pages/data-rights/index")
    await page.waitFor(300)
    const rightsTitle = await page.$(".rights-title")
    assert(rightsTitle && (await rightsTitle.text()) === "获取我的数据副本", "我的数据页面未正确渲染")
    if (domainCheckBlocked) {
      await miniProgram.mockWxMethod("request", {
        statusCode: 200,
        data: {
          code: 0,
          message: "个人数据副本已生成",
          data: {
            generated_at: "2026-08-23T08:00:00+00:00",
            counts: { account: 1, health_profile: 1, daily_records: 3 },
            data: {},
            excluded_security_fields: []
          }
        }
      })
      requestMocked = true
    }
    await page.callMethod("exportData")
    await new Promise((resolve) => setTimeout(resolve, 1200))
    const rightsData = await page.data()
    if (requestMocked) {
      await miniProgram.restoreWxMethod("request")
      requestMocked = false
    }
    assert(Boolean(rightsData.lastExportAt), "小程序未成功生成数据副本")
    results.push({
      route: page.path,
      selector: ".rights-title",
      text: `${await rightsTitle.text()}（${domainCheckBlocked ? "API mock" : "真实后端"}）`
    })

    if (domainCheckBlocked) {
      await miniProgram.mockWxMethod("request", {
        statusCode: 200,
        data: {
          code: 0,
          message: "健康数据授权已撤回",
          data: { required_complete: false, withdrawn_at: "2026-08-23T09:00:00+00:00" }
        }
      })
      requestMocked = true
    }
    await page.callMethod("withdrawConsentConfirmed")
    await new Promise((resolve) => setTimeout(resolve, 5000))
    if (requestMocked) {
      await miniProgram.restoreWxMethod("request")
      requestMocked = false
    }
    page = await miniProgram.currentPage()
    assert(page.path === "pages/consent/index", `撤回授权后未进入重新授权页，当前为 ${page.path}`)
    results.push({ route: "pages/data-rights/index", selector: ".withdraw-button", text: "撤回后已停止健康功能并进入重新授权页" })

    if (domainCheckBlocked) {
      await miniProgram.mockWxMethod("request", {
        statusCode: 200,
        data: {
          code: 0,
          message: "授权记录已保存",
          data: { required_complete: true, versions: {} }
        }
      })
      requestMocked = true
    }
    await page.setData({ acceptedValues: ["agreement", "privacy", "health"] })
    await page.callMethod("submitConsent")
    await new Promise((resolve) => setTimeout(resolve, 5000))
    if (requestMocked) {
      await miniProgram.restoreWxMethod("request")
      requestMocked = false
    }
    page = await miniProgram.currentPage()
    assert(page.path === "pages/daily/index", `重新授权后未恢复每日记录页，当前为 ${page.path}`)
    results.push({ route: "pages/consent/index", selector: ".consent-title", text: "重新授权后健康功能已恢复" })
    console.log(JSON.stringify({ passed: true, endpoint, results }, null, 2))
  } finally {
    if (requestMocked) await miniProgram.restoreWxMethod("request").catch(() => {})
    await miniProgram.disconnect()
  }
}

run().catch((error) => {
  console.error(`小程序冒烟测试失败：${error.stack || error.message}`)
  process.exit(1)
})
