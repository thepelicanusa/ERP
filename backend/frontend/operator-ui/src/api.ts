const API = 'http://localhost:8000'
const headers = () => ({
  'Content-Type': 'application/json',
  'Authorization': 'Bearer dev',
})

export async function getMyTasks() {
  const r = await fetch(`${API}/tasks/my`, { headers: headers() })
  return r.json()
}

export async function getTask(taskId: string) {
  const r = await fetch(`${API}/tasks/${taskId}`, { headers: headers() })
  return r.json()
}

export async function completeStep(taskId: string, stepId: string, value: string, reason?: string) {
  const r = await fetch(`${API}/tasks/${taskId}/steps/${stepId}/complete`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ value, reason }),
  })
  return r.json()
}

export async function listItems() {
  const r = await fetch(`${API}/inventory/items`, { headers: headers() })
  return r.json()
}
export async function createItem(sku: string, description?: string) {
  const r = await fetch(`${API}/inventory/items`, { method: 'POST', headers: headers(), body: JSON.stringify({ sku, description }) })
  return r.json()
}

export async function listLocations() {
  const r = await fetch(`${API}/inventory/locations`, { headers: headers() })
  return r.json()
}
export async function createLocation(code: string, type: string) {
  const r = await fetch(`${API}/inventory/locations`, { method: 'POST', headers: headers(), body: JSON.stringify({ code, type }) })
  return r.json()
}

export async function createReceipt(ref: string, lines: {sku: string, qty: number}[]) {
  const r = await fetch(`${API}/docs/receipts`, { method: 'POST', headers: headers(), body: JSON.stringify({ ref, lines }) })
  return r.json()
}
export async function listReceipts() {
  const r = await fetch(`${API}/docs/receipts`, { headers: headers() })
  return r.json()
}
export async function generateReceiptTasks(receiptId: string, staging_location_code = "STAGE") {
  const r = await fetch(`${API}/docs/receipts/${receiptId}/generate-tasks`, { method: 'POST', headers: headers(), body: JSON.stringify({ staging_location_code }) })
  return r.json()
}

export async function createOrder(ref: string, lines: {sku: string, qty: number}[]) {
  const r = await fetch(`${API}/docs/orders`, { method: 'POST', headers: headers(), body: JSON.stringify({ ref, lines }) })
  return r.json()
}
export async function listOrders() {
  const r = await fetch(`${API}/docs/orders`, { headers: headers() })
  return r.json()
}
export async function generateOrderTasks(orderId: string) {
  const r = await fetch(`${API}/docs/orders/${orderId}/generate-tasks`, { method: 'POST', headers: headers() })
  return r.json()
}

export async function createCount(ref: string, locations: string[]) {
  const r = await fetch(`${API}/docs/counts`, { method: 'POST', headers: headers(), body: JSON.stringify({ ref, locations }) })
  return r.json()
}
export async function listCounts() {
  const r = await fetch(`${API}/docs/counts`, { headers: headers() })
  return r.json()
}
export async function generateCountTasks(countId: string) {
  const r = await fetch(`${API}/docs/counts/${countId}/generate-tasks`, { method: 'POST', headers: headers() })
  return r.json()
}

export async function listBalances() {
  const r = await fetch(`${API}/inventory/balances`, { headers: headers() })
  return r.json()
}


export async function listCountSubmissions(status='PENDING_REVIEW') {
  const r = await fetch(`${API}/counts/submissions?status=${encodeURIComponent(status)}`, { headers: headers() })
  return r.json()
}
export async function approveCountSubmission(id: string, reason?: string) {
  const r = await fetch(`${API}/counts/submissions/${id}/approve`, { method: 'POST', headers: headers(), body: JSON.stringify({ reason }) })
  return r.json()
}


export async function listExceptions(kind?: string, status: string = 'OPEN') {
  const q = new URLSearchParams()
  if (kind) q.set('kind', kind)
  if (status) q.set('status', status)
  const r = await fetch(`${API}/exceptions?${q.toString()}`, { headers: headers() })
  return r.json()
}
export async function resolveException(id: string) {
  const r = await fetch(`${API}/exceptions/${id}/resolve`, { method: 'POST', headers: headers(), body: JSON.stringify({}) })
  return r.json()
}

export async function listWaves() {
  const r = await fetch(`${API}/waves`, { headers: headers() })
  return r.json()
}
export async function createWave(code: string, order_ids: string[]) {
  const r = await fetch(`${API}/waves`, { method: 'POST', headers: headers(), body: JSON.stringify({ code, order_ids }) })
  return r.json()
}
export async function getWave(id: string) {
  const r = await fetch(`${API}/waves/${id}`, { headers: headers() })
  return r.json()
}
export async function releaseWave(id: string) {
  const r = await fetch(`${API}/waves/${id}/release`, { method: 'POST', headers: headers() })
  return r.json()
}
export async function listBackorders(status='OPEN') {
  const r = await fetch(`${API}/backorders?status=${encodeURIComponent(status)}`, { headers: headers() })
  return r.json()
}


// --- MES (ISA-95 L3) ---
export async function mesQueue(work_center_id?: string) {
  const qs = work_center_id ? `?work_center_id=${encodeURIComponent(work_center_id)}` : ''
  return jget(`/erp/mes/dispatch/queue${qs}`)
}
export async function listMOs() { return jget(`/erp/mes/production-orders`) }
export async function getMO(id: string) { return jget(`/erp/mes/production-orders/${id}`) }
export async function moRelease(id: string) { return jpost(`/erp/mes/production-orders/${id}/release`, {}) }
export async function moOpStart(id: string, seq: number) { return jpost(`/erp/mes/production-orders/${id}/ops/${seq}/start`, {}) }
export async function moOpStop(id: string, seq: number, done: boolean = true) { return jpost(`/erp/mes/production-orders/${id}/ops/${seq}/stop`, { done }) }
export async function moIssue(id: string, item_id: string, from_location_id: string, qty: number) {
  return jpost(`/erp/mes/production-orders/${id}/issue`, { item_id, from_location_id, qty })
}
export async function moReceive(id: string, to_location_id: string, qty: number) {
  return jpost(`/erp/mes/production-orders/${id}/receive`, { to_location_id, qty })
}
export async function moLabor(id: string, minutes: number, seq?: number, labor_rate?: number, operator?: string) {
  return jpost(`/erp/mes/production-orders/${id}/labor`, { minutes, seq, labor_rate, operator })
}
export async function moScrap(id: string, item_id: string, qty: number, reason_code?: string, seq?: number) {
  return jpost(`/erp/mes/production-orders/${id}/scrap`, { item_id, qty, reason_code, seq })
}
export async function moQC(id: string, check_code: string, result: 'PASS'|'FAIL'|'HOLD', measured?: any, seq?: number) {
  return jpost(`/erp/mes/production-orders/${id}/qc`, { check_code, result, measured, seq })
}
export async function moClose(id: string) { return jpost(`/erp/mes/production-orders/${id}/close`, {}) }


export async function moQcRelease(id: string, note?: string) {
  return jpost(`/erp/mes/production-orders/${id}/qc/release`, { note })
}


// --- MES Guided Scan Engine (v16) ---
export async function mesStartScanSession(mode: 'START_OP'|'ISSUE'|'RECEIVE'|'QC') {
  const r = await fetch(`${API}/erp/mes/scan/sessions`, { method: 'POST', headers: headers(), body: JSON.stringify({ mode }) })
  return r.json()
}
export async function mesGetScanSession(session_id: string) {
  const r = await fetch(`${API}/erp/mes/scan/sessions/${session_id}`, { headers: headers() })
  return r.json()
}
export async function mesSubmitScan(session_id: string, raw: string) {
  const r = await fetch(`${API}/erp/mes/scan/sessions/${session_id}/scan`, { method: 'POST', headers: headers(), body: JSON.stringify({ raw }) })
  return r.json()
}


export async function mesListScanSessions() {
  const r = await fetch(`${API}/erp/mes/scan/sessions`, { headers: headers() })
  return r.json()
}
export async function mesCancelScanSession(session_id: string, note?: string) {
  const r = await fetch(`${API}/erp/mes/scan/sessions/${session_id}/cancel`, { method: 'POST', headers: headers(), body: JSON.stringify({ note }) })
  return r.json()
}
