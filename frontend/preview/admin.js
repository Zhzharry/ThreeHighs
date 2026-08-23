const API_BASE_URL = "http://localhost:5000/api/v1"
let accessToken = sessionStorage.getItem("admin_access_token") || ""
let modalContext = null
const state = {
  users: [], reports: [], foods: [], announcements: [],
  pagination: {
    users: { page: 1, pageSize: 10, total: 0 },
    reports: { page: 1, pageSize: 10, total: 0 },
    foods: { page: 1, pageSize: 10, total: 0 },
    announcements: { page: 1, pageSize: 5, total: 0 }
  },
  selected: { reports: new Set(), foods: new Set(), announcements: new Set() }
}

const $ = (selector) => document.querySelector(selector)
const $$ = (selector) => Array.from(document.querySelectorAll(selector))
const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;")

async function ensureLogin() {
  if (accessToken) return accessToken
  throw new Error("请先登录管理后台")
}

async function api(path, options = {}) {
  await ensureLogin()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers: { "content-type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: options.data ? JSON.stringify(options.data) : undefined
  })
  const payload = await response.json()
  if (response.status === 401 || response.status === 403) {
    accessToken = ""
    sessionStorage.removeItem("admin_access_token")
    showLogin()
  }
  return payload
}

function showLogin() {
  $(".login-gate").hidden = false
  $(".login-card input[name='password']").value = ""
}

function hideLogin() { $(".login-gate").hidden = true }

async function loginAdmin(event) {
  event.preventDefault()
  const form = event.currentTarget
  const button = form.querySelector("button[type='submit']")
  const data = Object.fromEntries(new FormData(form))
  button.disabled = true
  button.textContent = "正在验证"
  try {
    const response = await fetch(`${API_BASE_URL}/auth/admin-login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data)
    }).then((item) => item.json())
    if (response.code !== 0) throw new Error(response.message || "登录失败")
    accessToken = response.data.token
    sessionStorage.setItem("admin_access_token", accessToken)
    $(".admin-user strong").textContent = response.data.user.display_name
    hideLogin()
    await init()
    toast("管理员登录成功")
  } catch (error) {
    toast(error.message || "登录失败", true)
  } finally {
    button.disabled = false
    button.textContent = "登录管理后台"
  }
}

function logoutAdmin() {
  accessToken = ""
  sessionStorage.removeItem("admin_access_token")
  showLogin()
  toast("已退出管理后台")
}

function toast(message, error = false) {
  const element = $(".toast")
  element.textContent = message
  element.classList.toggle("error", error)
  element.hidden = false
  clearTimeout(toast.timer)
  toast.timer = setTimeout(() => { element.hidden = true }, 2200)
}

function setConnection(online) {
  $(".connection-dot")?.classList.toggle("online", online)
  $(".connection-text").textContent = online ? "已连接 Flask 后端" : "后端连接失败"
}

const statusText = (status) => ({ uploaded: "待识别", recognizing: "识别中", extracting: "提取中", review_pending: "待复核", completed: "已完成", rejected: "已驳回" })[status] || status
const statusClass = (status) => status === "review_pending" ? "warn" : status === "rejected" ? "danger" : status === "completed" ? "" : "muted"
const chronicText = (types = []) => types.map((item) => ({ hypertension: "高血压", diabetes: "糖尿病", hyperlipidemia: "高血脂" })[item] || item).join("、") || "未填写"
const dateText = (value) => value ? String(value).replace("T", " ").slice(0, 16) : "-"

function renderPagination(kind, data) {
  const pagination = state.pagination[kind]
  pagination.page = data.page
  pagination.pageSize = data.page_size
  pagination.total = data.total
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))
  const element = $(`#${kind}-pagination`)
  element.innerHTML = `<span>共 <strong>${data.total}</strong> 条</span><button data-action="change-page" data-kind="${kind}" data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>上一页</button><span>第 <strong>${data.page}</strong> / ${totalPages} 页</span><button data-action="change-page" data-kind="${kind}" data-page="${data.page + 1}" ${data.page >= totalPages ? "disabled" : ""}>下一页</button>`
}

function rewindInvalidPage(kind, data) {
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))
  if (data.page <= totalPages) return false
  state.pagination[kind].page = totalPages
  return true
}

function updateBatchToolbar(kind) {
  const toolbar = $(`#${kind}-batch`)
  if (!toolbar) return
  const count = state.selected[kind].size
  toolbar.querySelector("strong").textContent = count
  toolbar.querySelectorAll("button").forEach((button) => { button.disabled = count === 0 })
  const selectAll = document.querySelector(`[data-select-all="${kind}"]`)
  const pageItems = state[kind]
  if (selectAll) {
    selectAll.checked = pageItems.length > 0 && pageItems.every((item) => state.selected[kind].has(item.id))
    selectAll.indeterminate = !selectAll.checked && pageItems.some((item) => state.selected[kind].has(item.id))
  }
}

function resetSelection(kind) {
  state.selected[kind].clear()
  updateBatchToolbar(kind)
}

async function loadDashboard() {
  const response = await api("/admin/dashboard")
  if (response.code !== 0) throw new Error(response.message)
  Object.entries(response.data.stats).forEach(([key, value]) => {
    const element = document.querySelector(`[data-stat="${key}"]`)
    if (element) element.textContent = value
  })
  $(".dashboard-users").innerHTML = response.data.users.length ? response.data.users.map((user) => `
    <div class="dashboard-user"><span>${escapeHtml(user.name.slice(0, 1))}</span><div><strong>${escapeHtml(user.name)}</strong><small>${escapeHtml(user.type)}</small></div><em class="tag warn">${escapeHtml(user.risk)}</em></div>
  `).join("") : '<div class="empty">暂无重点关注用户</div>'
}

async function loadUsers() {
  const keyword = $("#user-keyword")?.value.trim() || ""
  const pagination = state.pagination.users
  const response = await api(`/admin/users?page=${pagination.page}&page_size=${pagination.pageSize}&keyword=${encodeURIComponent(keyword)}`)
  if (response.code !== 0) throw new Error(response.message)
  if (rewindInvalidPage("users", response.data)) return loadUsers()
  state.users = response.data.items
  $("#users-body").innerHTML = state.users.length ? state.users.map((user) => `
    <tr><td class="name-cell"><strong>${escapeHtml(user.nickname)}</strong><small>ID ${user.id}${user.last_login_at ? ` · 最近登录 ${escapeHtml(dateText(user.last_login_at))}` : " · 尚未登录"}</small></td><td>${user.age || "-"} 岁</td><td>${escapeHtml(user.phone || "-")}</td><td><span class="tag">${escapeHtml(chronicText(user.chronic_types))}</span></td><td><span class="tag ${user.status === 1 ? "" : "danger"}">${user.status === 1 ? "正常" : "已停用"}</span></td><td>${escapeHtml(dateText(user.created_at))}</td><td><div class="row-actions"><button data-action="edit-user" data-id="${user.id}">编辑档案</button></div></td></tr>
  `).join("") : '<tr><td class="empty" colspan="7">没有匹配的用户</td></tr>'
  renderPagination("users", response.data)
}

async function loadReports() {
  const status = $("#report-status")?.value || ""
  const pagination = state.pagination.reports
  const response = await api(`/admin/reports?page=${pagination.page}&page_size=${pagination.pageSize}&status=${encodeURIComponent(status)}`)
  if (response.code !== 0) throw new Error(response.message)
  if (rewindInvalidPage("reports", response.data)) return loadReports()
  state.reports = response.data.items
  resetSelection("reports")
  $("#reports-body").innerHTML = state.reports.length ? state.reports.map((report) => `
    <tr><td><input type="checkbox" data-select-item="reports" data-id="${report.id}" aria-label="选择报告 ${escapeHtml(report.file_name)}" /></td><td class="name-cell"><strong>${escapeHtml(report.file_name)}</strong><small>${escapeHtml(dateText(report.created_at))}</small></td><td>${escapeHtml(report.user_name)}</td><td><span class="tag ${statusClass(report.status)}">${escapeHtml(statusText(report.status))}</span></td><td>${report.confidence == null ? "-" : `${Math.round(report.confidence * 100)}%`}</td><td title="${escapeHtml(report.summary)}">${escapeHtml(report.summary || "暂无摘要").slice(0, 24)}</td><td><div class="row-actions"><button data-action="review-report" data-id="${report.id}">审核</button></div></td></tr>
  `).join("") : '<tr><td class="empty" colspan="7">该状态下暂无报告</td></tr>'
  updateBatchToolbar("reports")
  renderPagination("reports", response.data)
}

async function loadFoods() {
  const keyword = $("#food-keyword")?.value.trim() || ""
  const pagination = state.pagination.foods
  const response = await api(`/admin/foods?page=${pagination.page}&page_size=${pagination.pageSize}&keyword=${encodeURIComponent(keyword)}`)
  if (response.code !== 0) throw new Error(response.message)
  if (rewindInvalidPage("foods", response.data)) return loadFoods()
  state.foods = response.data.items
  resetSelection("foods")
  $("#foods-body").innerHTML = state.foods.length ? state.foods.map((food) => `
    <tr><td><input type="checkbox" data-select-item="foods" data-id="${food.id}" aria-label="选择食物 ${escapeHtml(food.name)}" /></td><td class="name-cell"><strong>${escapeHtml(food.name)}</strong><small>ID ${food.id}</small></td><td>${escapeHtml(food.category || "未分类")} / ${escapeHtml(food.unit)}</td><td>${food.calories} kcal</td><td>${food.sugar} g</td><td>${food.fat} g</td><td>${food.salt} g</td><td><div class="row-actions"><button data-action="edit-food" data-id="${food.id}">编辑</button><button class="delete" data-action="delete-food" data-id="${food.id}">删除</button></div></td></tr>
  `).join("") : '<tr><td class="empty" colspan="8">没有匹配的食物</td></tr>'
  updateBatchToolbar("foods")
  renderPagination("foods", response.data)
}

async function loadAnnouncements() {
  const pagination = state.pagination.announcements
  const response = await api(`/admin/announcements?page=${pagination.page}&page_size=${pagination.pageSize}`)
  if (response.code !== 0) throw new Error(response.message)
  if (rewindInvalidPage("announcements", response.data)) return loadAnnouncements()
  state.announcements = response.data.items
  resetSelection("announcements")
  $(".announcement-list").innerHTML = state.announcements.length ? state.announcements.map((item) => `
    <article class="announcement-card"><input type="checkbox" data-select-item="announcements" data-id="${item.id}" aria-label="选择公告 ${escapeHtml(item.title)}" /><div><h3>${escapeHtml(item.title)} <span class="tag ${item.is_published ? "" : "muted"}">${item.is_published ? "已发布" : "草稿"}</span></h3><p>${escapeHtml(item.content)}</p><small>更新于 ${escapeHtml(dateText(item.updated_at))}</small></div><div class="row-actions"><button data-action="edit-announcement" data-id="${item.id}">编辑</button><button class="delete" data-action="delete-announcement" data-id="${item.id}">删除</button></div></article>
  `).join("") : '<div class="empty">暂无系统公告</div>'
  updateBatchToolbar("announcements")
  renderPagination("announcements", response.data)
}

function openModal(type, item = null) {
  modalContext = { type, id: item?.id || null, initialStatus: item?.status }
  const title = $(".modal-title")
  const subtitle = $(".modal-subtitle")
  const fields = $(".modal-fields")
  if (type === "user") {
    const selectedTypes = new Set(item.chronic_types || [])
    title.textContent = "编辑用户健康档案"
    subtitle.textContent = `${item.nickname} · 用户 ID ${item.id} · 当前 BMI ${item.bmi || "未计算"}`
    fields.innerHTML = `
      <label><span>昵称</span><input name="nickname" maxlength="30" value="${escapeHtml(item.nickname)}" required /></label>
      <label><span>手机号</span><input name="phone" inputmode="numeric" maxlength="11" value="${escapeHtml(item.phone || "")}" placeholder="可留空" /></label>
      <label><span>账号状态</span><select name="status"><option value="1" ${item.status === 1 ? "selected" : ""}>正常（允许登录）</option><option value="0" ${item.status === 0 ? "selected" : ""}>停用（立即退出）</option></select></label>
      <label><span>性别</span><select name="gender"><option value="">未填写</option>${["男", "女", "其他"].map((value) => `<option value="${value}" ${item.gender === value ? "selected" : ""}>${value}</option>`).join("")}</select></label>
      <label><span>年龄</span><input name="age" type="number" min="1" max="120" value="${escapeHtml(item.age || "")}" required /></label>
      <label><span>身高 cm</span><input name="height_cm" type="number" min="80" max="240" step="0.1" value="${escapeHtml(item.height_cm || "")}" required /></label>
      <label><span>体重 kg</span><input name="weight_kg" type="number" min="20" max="300" step="0.1" value="${escapeHtml(item.weight_kg || "")}" required /></label>
      <fieldset class="wide check-group"><legend>慢病类型</legend>${[["hypertension", "高血压"], ["diabetes", "糖尿病"], ["hyperlipidemia", "高血脂"]].map(([value, label]) => `<label><input type="checkbox" name="chronic_types" value="${value}" ${selectedTypes.has(value) ? "checked" : ""} /><span>${label}</span></label>`).join("")}</fieldset>
      <label class="wide"><span>既往病史</span><textarea name="medical_history" maxlength="1000" placeholder="填写既往疾病或检查情况">${escapeHtml(item.medical_history || "")}</textarea></label>
      <label class="wide"><span>用药情况</span><textarea name="medication" maxlength="1000" placeholder="填写当前用药名称和剂量">${escapeHtml(item.medication || "")}</textarea></label>`
  } else if (type === "food") {
    title.textContent = item ? "编辑食物" : "新增食物"
    subtitle.textContent = "营养数值均按所填单位记录"
    fields.innerHTML = [
      ["name", "食物名称", item?.name || "", "text"], ["category", "分类", item?.category || "", "text"], ["unit", "单位", item?.unit || "100g", "text"],
      ["calories", "热量 kcal", item?.calories ?? 0, "number"], ["sugar", "糖 g", item?.sugar ?? 0, "number"], ["fat", "脂肪 g", item?.fat ?? 0, "number"], ["salt", "盐 g", item?.salt ?? 0, "number"]
    ].map(([name, label, value, inputType]) => `<label><span>${label}</span><input name="${name}" type="${inputType}" step="0.01" min="0" value="${escapeHtml(value)}" required /></label>`).join("")
  } else if (type === "announcement") {
    title.textContent = item ? "编辑公告" : "新增公告"
    subtitle.textContent = "发布后可用于健康提醒和系统通知"
    fields.innerHTML = `<label class="wide"><span>标题</span><input name="title" maxlength="150" value="${escapeHtml(item?.title || "")}" required /></label><label class="wide"><span>内容</span><textarea name="content" maxlength="5000" required>${escapeHtml(item?.content || "")}</textarea></label><label class="wide"><span>发布状态</span><select name="is_published"><option value="false" ${item?.is_published ? "" : "selected"}>保存为草稿</option><option value="true" ${item?.is_published ? "selected" : ""}>立即发布</option></select></label>`
  } else {
    title.textContent = "审核体检报告"
    subtitle.textContent = `${item.file_name} · ${item.user_name}`
    fields.innerHTML = `<label class="wide"><span>审核结论</span><select name="status"><option value="completed">审核通过</option><option value="rejected">驳回报告</option><option value="review_pending">保留待复核</option></select></label><label class="wide"><span>审核说明</span><textarea name="review_note" maxlength="500" placeholder="填写审核依据或需要重新识别的原因">${escapeHtml(item.summary || "")}</textarea></label>`
  }
  $(".modal-backdrop").hidden = false
}

function closeModal() { $(".modal-backdrop").hidden = true; modalContext = null }

async function submitModal(event) {
  event.preventDefault()
  if (!modalContext) return
  const formData = new FormData(event.currentTarget)
  let response
  if (modalContext.type === "user") {
    const data = Object.fromEntries(formData)
    data.age = Number(data.age)
    data.height_cm = Number(data.height_cm)
    data.weight_kg = Number(data.weight_kg)
    data.status = Number(data.status)
    data.chronic_types = formData.getAll("chronic_types")
    if (data.status === 0 && modalContext.initialStatus !== 0 && !window.confirm("停用后该用户现有登录会立即失效，确认继续吗？")) return
    response = await api(`/admin/users/${modalContext.id}`, { method: "PUT", data })
    if (response.code === 0) await Promise.all([loadUsers(), loadDashboard()])
  } else if (modalContext.type === "food") {
    const data = Object.fromEntries(formData)
    for (const key of ["calories", "sugar", "fat", "salt"]) data[key] = Number(data[key])
    response = await api(modalContext.id ? `/admin/foods/${modalContext.id}` : "/admin/foods", { method: modalContext.id ? "PUT" : "POST", data })
    if (response.code === 0) await loadFoods()
  } else if (modalContext.type === "announcement") {
    const data = Object.fromEntries(formData)
    data.is_published = data.is_published === "true"
    response = await api(modalContext.id ? `/admin/announcements/${modalContext.id}` : "/admin/announcements", { method: modalContext.id ? "PUT" : "POST", data })
    if (response.code === 0) await loadAnnouncements()
  } else {
    response = await api(`/admin/reports/${modalContext.id}/review`, { method: "PATCH", data: Object.fromEntries(formData) })
    if (response.code === 0) { await Promise.all([loadReports(), loadDashboard()]) }
  }
  if (response.code !== 0) return toast(response.message || "保存失败", true)
  closeModal()
  toast(response.message || "保存成功")
}

async function handleAction(event) {
  const button = event.target.closest("[data-action], [data-go]")
  if (!button) return
  if (button.dataset.go) return switchView(button.dataset.go)
  const id = Number(button.dataset.id)
  const action = button.dataset.action
  if (action === "search-users") { state.pagination.users.page = 1; return loadUsers() }
  if (action === "filter-reports") { state.pagination.reports.page = 1; return loadReports() }
  if (action === "search-foods") { state.pagination.foods.page = 1; return loadFoods() }
  if (action === "change-page") {
    const kind = button.dataset.kind
    const loader = { users: loadUsers, reports: loadReports, foods: loadFoods, announcements: loadAnnouncements }[kind]
    if (!loader) return
    state.pagination[kind].page = Number(button.dataset.page)
    return loader()
  }
  if (action === "edit-user") {
    const response = await api(`/admin/users/${id}`)
    if (response.code !== 0) return toast(response.message || "用户档案加载失败", true)
    return openModal("user", response.data)
  }
  if (action === "batch-review") {
    const ids = Array.from(state.selected.reports)
    const status = button.dataset.status
    const actionName = status === "completed" ? "通过" : "驳回"
    if (!ids.length || !confirm(`确定批量${actionName}选中的 ${ids.length} 份报告吗？`)) return
    const response = await api("/admin/reports/batch-review", { method: "PATCH", data: { ids, status, review_note: `管理员批量${actionName}` } })
    if (response.code === 0) await Promise.all([loadReports(), loadDashboard()])
    return toast(response.message || `报告批量${actionName}完成`, response.code !== 0)
  }
  if (action === "batch-delete-foods") {
    const ids = Array.from(state.selected.foods)
    if (!ids.length || !confirm(`确定删除选中的 ${ids.length} 条食物数据吗？该操作不可撤销。`)) return
    const response = await api("/admin/foods/batch-delete", { method: "POST", data: { ids } })
    if (response.code === 0) await loadFoods()
    return toast(response.message || "食物批量删除完成", response.code !== 0)
  }
  if (action === "batch-publish") {
    const ids = Array.from(state.selected.announcements)
    const isPublished = button.dataset.published === "true"
    if (!ids.length || !confirm(`确定将选中的 ${ids.length} 条公告${isPublished ? "发布" : "设为草稿"}吗？`)) return
    const response = await api("/admin/announcements/batch-publish", { method: "PATCH", data: { ids, is_published: isPublished } })
    if (response.code === 0) await Promise.all([loadAnnouncements(), loadDashboard()])
    return toast(response.message || "公告状态批量更新完成", response.code !== 0)
  }
  if (action === "new-food") return openModal("food")
  if (action === "edit-food") return openModal("food", state.foods.find((item) => item.id === id))
  if (action === "new-announcement") return openModal("announcement")
  if (action === "edit-announcement") return openModal("announcement", state.announcements.find((item) => item.id === id))
  if (action === "review-report") return openModal("report", state.reports.find((item) => item.id === id))
  if (action === "delete-food" && confirm("确定删除该食物吗？")) {
    const response = await api(`/admin/foods/${id}`, { method: "DELETE" }); if (response.code === 0) await loadFoods(); return toast(response.message || "食物已删除", response.code !== 0)
  }
  if (action === "delete-announcement" && confirm("确定删除该公告吗？")) {
    const response = await api(`/admin/announcements/${id}`, { method: "DELETE" }); if (response.code === 0) await loadAnnouncements(); return toast(response.message || "公告已删除", response.code !== 0)
  }
}

function handleSelection(event) {
  const selectAll = event.target.closest("[data-select-all]")
  if (selectAll) {
    const kind = selectAll.dataset.selectAll
    state[kind].forEach((item) => selectAll.checked ? state.selected[kind].add(item.id) : state.selected[kind].delete(item.id))
    document.querySelectorAll(`[data-select-item="${kind}"]`).forEach((checkbox) => { checkbox.checked = selectAll.checked })
    updateBatchToolbar(kind)
    return
  }
  const checkbox = event.target.closest("[data-select-item]")
  if (!checkbox) return
  const kind = checkbox.dataset.selectItem
  const id = Number(checkbox.dataset.id)
  checkbox.checked ? state.selected[kind].add(id) : state.selected[kind].delete(id)
  updateBatchToolbar(kind)
}

const viewNames = { dashboard: "数据概览", users: "用户管理", reports: "报告审核", foods: "食物营养库", announcements: "系统公告" }
function switchView(view) {
  $$(".sidebar nav button").forEach((button) => button.classList.toggle("active", button.dataset.view === view))
  $$(".view").forEach((item) => item.classList.toggle("active", item.id === `${view}-view`))
  $(".view-title").textContent = viewNames[view]
  const loader = { dashboard: loadDashboard, users: loadUsers, reports: loadReports, foods: loadFoods, announcements: loadAnnouncements }[view]
  loader?.().catch((error) => toast(error.message, true))
}

async function init() {
  if (!accessToken) {
    showLogin()
    return
  }
  try {
    await ensureLogin()
    await Promise.all([loadDashboard(), loadUsers(), loadReports(), loadFoods(), loadAnnouncements()])
    setConnection(true)
  } catch (error) {
    setConnection(false)
    toast(error.message || "后台加载失败", true)
    if (!accessToken) showLogin()
  }
}

$$(".sidebar nav button").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)))
document.addEventListener("click", handleAction)
document.addEventListener("change", handleSelection)
$(".modal-card").addEventListener("submit", submitModal)
$(".modal-close").addEventListener("click", closeModal)
$(".modal-cancel").addEventListener("click", closeModal)
$(".modal-backdrop").addEventListener("click", (event) => { if (event.target === event.currentTarget) closeModal() })
$(".login-card").addEventListener("submit", loginAdmin)
$(".logout-button").addEventListener("click", logoutAdmin)
init()
