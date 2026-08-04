<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { fal } from '@fal-ai/client'
import QRCode from 'qrcode'

const DEFAULT_API_URL = 'https://smart-mirror-saas-production.up.railway.app'
const TOKEN_KEY = 'smart_mirror_live_token'
const MODEL = 'decart/lucy2-vton/realtime'

const params = new URLSearchParams(window.location.search)
const apiUrl = ref((params.get('apiUrl') || DEFAULT_API_URL).replace(/\/$/, ''))
const pairingCode = ref(params.get('pairingCode') || '')
const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const products = ref([])
const selectedIndex = ref(0)
const video = ref(null)
const overlay = ref(null)
const qrCanvas = ref(null)
const resultImageUrl = ref('')
const qrVisible = ref(false)
const lastError = ref('')
const proxyStatus = ref('unchecked')
const phase = ref('pairing')
const connectionState = ref('idle')
const session = ref(null)
const secondsLeft = ref(Number(params.get('maxSeconds') || 20))
const logLines = ref([])

const pairingForm = reactive({
  pairing_code: pairingCode.value,
  device_name: 'Live Restyle Web Kiosk',
})

let stream = null
let animationFrame = 0
let frameTimer = 0
let countdownTimer = 0
let sessionStartedAt = 0
let falConnection = null
let finishingSession = false
let touchStartX = 0
let touchStartY = 0

const currentProduct = computed(() => products.value[selectedIndex.value] || null)
const liveConfig = ref({
  enabled: false,
  blocked_reason: 'not_loaded',
  provider: 'fal',
  model: MODEL,
  max_seconds: 20,
  local_proxy_url: 'http://127.0.0.1:8787',
})

const productReferenceUrl = computed(() => (
  currentProduct.value?.texture_image_url || currentProduct.value?.base_image_url || ''
))

const resultQrText = computed(() => (
  resultImageUrl.value || productReferenceUrl.value || `${apiUrl.value}/products`
))

function appendLog(event, payload = {}) {
  logLines.value.unshift({
    event,
    at: new Date().toLocaleTimeString(),
    payload,
  })
  logLines.value = logLines.value.slice(0, 8)
}

async function mirrorFetch(path, options = {}) {
  const response = await fetch(`${apiUrl.value}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      Authorization: `Bearer ${token.value}`,
      ...(options.headers || {}),
    },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.message || data.error || `HTTP ${response.status}`)
  }
  return data
}

async function pair() {
  lastError.value = ''
  try {
    const response = await fetch(`${apiUrl.value}/api/mirrors/pair`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(pairingForm),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.message || 'Pairing failed')
    }
    token.value = data.token
    localStorage.setItem(TOKEN_KEY, data.token)
    appendLog('paired', { mirror: data.mirror?.id })
    await boot()
  } catch (error) {
    lastError.value = error.message || String(error)
  }
}

function clearPairing() {
  localStorage.removeItem(TOKEN_KEY)
  token.value = ''
  phase.value = 'pairing'
  appendLog('pairing_cleared')
}

async function boot() {
  try {
    phase.value = token.value ? 'loading' : 'pairing'
    if (!token.value) return
    await Promise.all([loadConfig(), loadCatalog(), startCamera(), checkProxy()])
    phase.value = liveConfig.value.enabled ? 'ready' : 'blocked'
    drawOverlay()
  } catch (error) {
    lastError.value = error.message || String(error)
    phase.value = 'error'
    appendLog('boot_failed', { error: lastError.value })
  }
}

async function loadConfig() {
  const data = await mirrorFetch('/api/mirror/live-restyle-config')
  liveConfig.value = data.live_restyle
  secondsLeft.value = Math.min(20, Number(params.get('maxSeconds') || data.live_restyle.max_seconds || 20))
  appendLog('config_loaded', { enabled: data.live_restyle.enabled, blocked: data.live_restyle.blocked_reason })
}

async function loadCatalog() {
  const data = await mirrorFetch('/api/mirror/catalog')
  products.value = data.products || []
  appendLog('catalog_loaded', { count: products.value.length })
}

async function startCamera() {
  stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
    audio: false,
  })
  await nextTick()
  if (video.value) {
    video.value.srcObject = stream
    await video.value.play()
  }
  appendLog('camera_opened')
}

async function checkProxy() {
  try {
    const response = await fetch(`${liveConfig.value.local_proxy_url}/health`, { method: 'GET' })
    const data = await response.json()
    proxyStatus.value = data.ok ? 'ready' : 'error'
  } catch {
    proxyStatus.value = 'offline'
  }
}

async function logEvent(event, severity = 'info', payload = {}) {
  if (!token.value) return
  try {
    await mirrorFetch('/api/mirror/session-events', {
      method: 'POST',
      body: JSON.stringify({
        session_id: session.value?.id || `live-web-${Date.now()}`,
        events: [{
          sequence: Date.now(),
          severity,
          event,
          payload,
        }],
      }),
    })
  } catch {
    appendLog('event_log_failed', { event })
  }
}

async function startLiveRestyle() {
  if (!currentProduct.value) {
    lastError.value = 'No mirror-ready products are available.'
    return
  }
  lastError.value = ''
  resultImageUrl.value = ''
  qrVisible.value = false
  phase.value = 'connecting'
  connectionState.value = 'starting'

  try {
    const data = await mirrorFetch('/api/mirror/live-restyle-sessions', {
      method: 'POST',
      body: JSON.stringify({
        product_id: currentProduct.value.id,
        reference_image_url: productReferenceUrl.value,
        prompt: promptForProduct(currentProduct.value),
        max_seconds: secondsLeft.value,
      }),
    })
    session.value = data.session
    secondsLeft.value = data.session.max_seconds
    sessionStartedAt = Date.now()
    await logEvent('live_restyle_started', 'info', { product_id: currentProduct.value.id })
    try {
      connectFal()
    } catch (error) {
      lastError.value = error.message || String(error)
      await finishSession('failed')
      return
    }
    beginFrameLoop()
    beginCountdown()
    phase.value = 'live'
  } catch (error) {
    lastError.value = error.message || String(error)
    phase.value = 'error'
    await logEvent('live_restyle_failed', 'error', { error: lastError.value })
  }
}

function connectFal() {
  falConnection = fal.realtime.connect(MODEL, {
    connectionKey: `live-restyle-${session.value.id}`,
    throttleInterval: 220,
    maxBuffering: 2,
    tokenProvider: async (app) => {
      const response = await fetch(`${liveConfig.value.local_proxy_url}/realtime-token`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ app, session_id: session.value.id, max_seconds: session.value.max_seconds }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.error || 'fal token request failed')
      }
      return data.token
    },
    tokenExpirationSeconds: Math.min(120, session.value.max_seconds + 10),
    onResult: async (result) => {
      connectionState.value = 'result'
      const nextUrl = extractImageUrl(result)
      if (nextUrl) {
        resultImageUrl.value = nextUrl
        await renderQr()
      }
    },
    onError: async (error) => {
      connectionState.value = 'failed'
      lastError.value = error.message || 'fal realtime failed'
      appendLog('fal_error', { error: lastError.value })
      await logEvent('live_restyle_failed', 'error', { error: lastError.value })
      if (phase.value === 'live') {
        await finishSession('failed')
      }
    },
  })
  connectionState.value = 'connected'
  appendLog('fal_connected')
  logEvent('fal_connected')
}

function beginFrameLoop() {
  clearInterval(frameTimer)
  frameTimer = window.setInterval(() => {
    if (!falConnection || !video.value || video.value.readyState < 2 || phase.value !== 'live') return
    const frame = captureFrameDataUrl()
    if (!frame) return
    falConnection.send({
      image_url: frame,
      reference_image_url: productReferenceUrl.value,
      prompt: promptForProduct(currentProduct.value),
      request_id: `${session.value.id}-${Date.now()}`,
    })
  }, 260)
}

function beginCountdown() {
  clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    const elapsed = Math.floor((Date.now() - sessionStartedAt) / 1000)
    secondsLeft.value = Math.max(0, session.value.max_seconds - elapsed)
    if (secondsLeft.value <= 0) {
      finishSession('completed')
    }
  }, 250)
}

function captureFrameDataUrl() {
  const source = video.value
  if (!source?.videoWidth) return ''
  const canvas = document.createElement('canvas')
  canvas.width = 640
  canvas.height = Math.round((source.videoHeight / source.videoWidth) * canvas.width) || 360
  const ctx = canvas.getContext('2d')
  ctx.translate(canvas.width, 0)
  ctx.scale(-1, 1)
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.74)
}

async function finishSession(status = 'cancelled') {
  if (finishingSession) return
  finishingSession = true
  clearInterval(frameTimer)
  clearInterval(countdownTimer)
  frameTimer = 0
  countdownTimer = 0
  try {
    falConnection?.close()
  } catch {
    // Connection close errors should not keep the kiosk in live mode.
  }
  falConnection = null

  const duration = sessionStartedAt ? Math.min(session.value?.max_seconds || 20, Math.round((Date.now() - sessionStartedAt) / 1000)) : 0
  if (session.value) {
    try {
      await mirrorFetch(`/api/mirror/live-restyle-sessions/${session.value.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status, duration_seconds: duration, error: status === 'failed' ? lastError.value : null }),
      })
      await fetch(`${liveConfig.value.local_proxy_url}/sessions/${session.value.id}/end`, { method: 'POST' }).catch(() => {})
      await logEvent(status === 'completed' ? 'live_restyle_ended' : 'live_restyle_failed', status === 'failed' ? 'error' : 'info', { duration })
    } catch (error) {
      appendLog('session_finish_failed', { error: error.message })
    }
  }
  session.value = null
  connectionState.value = 'idle'
  phase.value = liveConfig.value.enabled ? 'ready' : 'blocked'
  secondsLeft.value = liveConfig.value.max_seconds || 20
  finishingSession = false
}

function nextProduct(direction) {
  if (products.value.length < 2) return
  const count = products.value.length
  selectedIndex.value = (selectedIndex.value + direction + count) % count
  appendLog('outfit_changed', { product_id: currentProduct.value?.id })
  logEvent('outfit_changed', 'info', { product_id: currentProduct.value?.id })
}

async function showQr() {
  qrVisible.value = true
  await renderQr()
}

async function renderQr() {
  await nextTick()
  if (!qrCanvas.value) return
  await QRCode.toCanvas(qrCanvas.value, resultQrText.value, {
    width: 220,
    margin: 1,
    color: { dark: '#06121d', light: '#ffffff' },
  })
}

function promptForProduct(product) {
  return `photorealistic live virtual try-on, retail mirror, keep face and body identity, replace outfit with ${product?.name || 'selected outfit'}, clean store lighting`
}

function extractImageUrl(result) {
  return result?.image?.url
    || result?.images?.[0]?.url
    || result?.output?.image?.url
    || result?.output?.images?.[0]?.url
    || result?.frame?.url
    || result?.url
    || ''
}

function onKey(event) {
  if (event.key === 'ArrowRight') nextProduct(1)
  if (event.key === 'ArrowLeft') nextProduct(-1)
  if (event.key.toLowerCase() === 'q') showQr()
  if (event.key === 'Escape') finishSession('cancelled')
  if (event.key === 'Enter' && phase.value === 'ready') startLiveRestyle()
}

function onTouchStart(event) {
  touchStartX = event.changedTouches?.[0]?.clientX || 0
  touchStartY = event.changedTouches?.[0]?.clientY || 0
}

function onTouchEnd(event) {
  const end = event.changedTouches?.[0]
  if (!end) return
  const dx = end.clientX - touchStartX
  const dy = end.clientY - touchStartY
  if (Math.abs(dx) > 90 && Math.abs(dx) > Math.abs(dy) * 1.4) {
    nextProduct(dx < 0 ? 1 : -1)
  }
}

function drawOverlay() {
  const canvas = overlay.value
  const ctx = canvas?.getContext('2d')
  if (!canvas || !ctx) return
  const resize = () => {
    const bounds = canvas.getBoundingClientRect()
    canvas.width = Math.round(bounds.width * devicePixelRatio)
    canvas.height = Math.round(bounds.height * devicePixelRatio)
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
  }
  resize()
  const render = (time) => {
    const w = canvas.clientWidth
    const h = canvas.clientHeight
    ctx.clearRect(0, 0, w, h)
    const cx = w / 2
    const top = h * 0.28
    const bottom = h * 0.83
    const shoulder = Math.min(w * 0.34, 420)
    const waist = shoulder * 0.54
    const scan = top + ((time / 8) % (bottom - top))

    ctx.save()
    ctx.globalAlpha = phase.value === 'live' ? 0.95 : 0.72
    ctx.strokeStyle = '#58e0b5'
    ctx.lineWidth = 2
    ctx.shadowColor = '#58e0b5'
    ctx.shadowBlur = 18
    ctx.beginPath()
    ctx.moveTo(cx - shoulder / 2, top)
    ctx.quadraticCurveTo(cx - shoulder * 0.34, h * 0.52, cx - waist / 2, bottom)
    ctx.moveTo(cx + shoulder / 2, top)
    ctx.quadraticCurveTo(cx + shoulder * 0.34, h * 0.52, cx + waist / 2, bottom)
    ctx.moveTo(cx - shoulder / 2, top)
    ctx.lineTo(cx + shoulder / 2, top)
    ctx.stroke()

    for (let i = 0; i < 10; i += 1) {
      const y = top + i * ((bottom - top) / 9)
      const width = shoulder - (shoulder - waist) * ((y - top) / (bottom - top))
      ctx.globalAlpha = 0.18
      ctx.beginPath()
      ctx.moveTo(cx - width / 2, y)
      ctx.lineTo(cx + width / 2, y)
      ctx.stroke()
    }

    ctx.globalAlpha = 0.88
    ctx.strokeStyle = '#70a7ff'
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.moveTo(cx - shoulder / 2, scan)
    ctx.lineTo(cx + shoulder / 2, scan)
    ctx.stroke()

    ctx.shadowBlur = 0
    for (let i = 0; i < 42; i += 1) {
      const angle = i * 0.42 + time / 850
      const radiusX = shoulder * (0.62 + (i % 5) * 0.035)
      const radiusY = (bottom - top) * (0.28 + (i % 7) * 0.014)
      const x = cx + Math.cos(angle) * radiusX
      const y = h * 0.58 + Math.sin(angle * 1.7) * radiusY
      if (y < top - 24 || y > bottom + 30) continue
      ctx.fillStyle = i % 3 === 0 ? '#58e0b5' : '#70a7ff'
      ctx.globalAlpha = 0.35 + (i % 4) * 0.08
      ctx.beginPath()
      ctx.arc(x, y, 2.2, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.restore()
    animationFrame = requestAnimationFrame(render)
  }
  cancelAnimationFrame(animationFrame)
  animationFrame = requestAnimationFrame(render)
  window.addEventListener('resize', resize)
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  boot()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  cancelAnimationFrame(animationFrame)
  clearInterval(frameTimer)
  clearInterval(countdownTimer)
  try {
    falConnection?.close()
  } catch {
    // Ignore shutdown race.
  }
  stream?.getTracks?.().forEach((track) => track.stop())
})
</script>

<template>
  <main class="live-restyle" @touchstart.passive="onTouchStart" @touchend.passive="onTouchEnd">
    <video ref="video" playsinline muted autoplay></video>
    <canvas ref="overlay" class="live-overlay"></canvas>

    <section class="live-topbar">
      <div>
        <span>Live Restyle</span>
        <strong>{{ phase === 'live' ? 'SCANNING' : phase.toUpperCase() }}</strong>
      </div>
      <div>
        <span>fal proxy</span>
        <strong>{{ proxyStatus }}</strong>
      </div>
      <div>
        <span>time</span>
        <strong>{{ secondsLeft }}s</strong>
      </div>
      <button class="live-icon-btn" @click="phase === 'live' ? finishSession('cancelled') : clearPairing()">Exit</button>
    </section>

    <form v-if="phase === 'pairing'" class="live-panel live-pairing" @submit.prevent="pair">
      <h1>Pair kiosk</h1>
      <label>API URL<input v-model="apiUrl"></label>
      <label>Pairing code<input v-model="pairingForm.pairing_code" autocomplete="one-time-code" required></label>
      <button>Connect</button>
      <p v-if="lastError">{{ lastError }}</p>
    </form>

    <section v-else-if="phase === 'blocked'" class="live-panel live-status-panel">
      <h1>Live Restyle is off</h1>
      <p>{{ liveConfig.blocked_reason }}</p>
      <button @click="boot">Refresh</button>
    </section>

    <section v-else-if="phase === 'error'" class="live-panel live-status-panel">
      <h1>Needs attention</h1>
      <p>{{ lastError }}</p>
      <button @click="boot">Retry</button>
    </section>

    <section v-else-if="phase === 'ready'" class="live-action">
      <div>
        <span>{{ currentProduct?.sku || 'OUTFIT' }}</span>
        <strong>{{ currentProduct?.name || 'No product' }}</strong>
      </div>
      <button @click="nextProduct(-1)">Prev</button>
      <button class="primary" @click="startLiveRestyle">Start</button>
      <button @click="nextProduct(1)">Next</button>
    </section>

    <section v-else-if="phase === 'connecting'" class="live-panel live-status-panel">
      <h1>Connecting</h1>
      <p>Starting a capped realtime session.</p>
    </section>

    <section v-if="phase === 'live'" class="live-gallery">
      <button class="live-icon-btn" @click="nextProduct(-1)">Prev</button>
      <article>
        <img v-if="resultImageUrl" :src="resultImageUrl" alt="Live restyle result">
        <img v-else-if="productReferenceUrl" :src="productReferenceUrl" alt="Selected outfit">
        <div>
          <span>{{ connectionState }}</span>
          <strong>{{ currentProduct?.name }}</strong>
          <small>{{ currentProduct?.price }} {{ currentProduct?.currency }}</small>
        </div>
      </article>
      <button class="live-icon-btn" @click="nextProduct(1)">Next</button>
      <button class="live-icon-btn" @click="showQr">QR</button>
    </section>

    <section v-if="qrVisible" class="live-qr">
      <canvas ref="qrCanvas"></canvas>
      <button @click="qrVisible = false">Close</button>
    </section>

    <aside class="live-debug">
      <div v-for="line in logLines" :key="line.at + line.event">{{ line.at }} {{ line.event }}</div>
    </aside>
  </main>
</template>

<style scoped>
.live-restyle {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: #03070d;
  color: #eef7ff;
}

.live-restyle video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scaleX(-1);
  opacity: 0.82;
}

.live-restyle::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(3, 7, 13, 0.78), transparent 22%, transparent 78%, rgba(3, 7, 13, 0.8));
  pointer-events: none;
}

.live-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.live-topbar,
.live-action,
.live-gallery,
.live-panel,
.live-qr,
.live-debug {
  position: relative;
  z-index: 2;
}

.live-topbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
}

.live-topbar div,
.live-action,
.live-gallery article,
.live-panel,
.live-qr {
  border: 1px solid rgba(111, 188, 255, 0.24);
  background: rgba(5, 13, 24, 0.68);
  backdrop-filter: blur(14px);
}

.live-topbar div {
  display: grid;
  gap: 4px;
  min-width: 116px;
  padding: 10px 14px;
  border-radius: 8px;
}

.live-topbar span,
.live-action span,
.live-gallery span,
.live-gallery small {
  color: #9db6cb;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0;
}

.live-icon-btn,
.live-action button,
.live-panel button,
.live-qr button {
  border: 0;
  border-radius: 8px;
  padding: 12px 16px;
  color: #06121d;
  background: #58e0b5;
  font-weight: 800;
}

.live-icon-btn {
  background: rgba(238, 247, 255, 0.9);
}

.live-panel {
  width: min(440px, calc(100% - 32px));
  margin: 13vh auto 0;
  padding: 24px;
  border-radius: 8px;
  display: grid;
  gap: 14px;
}

.live-panel h1 {
  margin: 0;
  font-size: 34px;
  letter-spacing: 0;
}

.live-panel p {
  color: #bed2e7;
  margin: 0;
}

.live-panel label {
  display: grid;
  gap: 8px;
  color: #bed2e7;
  font-size: 13px;
  font-weight: 700;
}

.live-panel input {
  border: 1px solid rgba(111, 188, 255, 0.28);
  background: #06101c;
  color: #eef7ff;
  border-radius: 8px;
  padding: 12px;
}

.live-action {
  position: absolute;
  left: 50%;
  bottom: 34px;
  transform: translateX(-50%);
  display: grid;
  grid-template-columns: minmax(240px, 420px) auto auto auto;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
}

.live-action div {
  display: grid;
  gap: 4px;
}

.live-action strong,
.live-gallery strong {
  overflow-wrap: anywhere;
}

.live-action .primary {
  background: #70a7ff;
}

.live-gallery {
  position: absolute;
  right: 24px;
  bottom: 30px;
  display: grid;
  grid-template-columns: auto minmax(280px, 420px) auto;
  gap: 10px;
  align-items: center;
}

.live-gallery article {
  min-height: 180px;
  border-radius: 8px;
  padding: 12px;
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 14px;
  align-items: center;
}

.live-gallery img {
  width: 130px;
  height: 160px;
  border-radius: 6px;
  object-fit: contain;
  background: #e8edf2;
}

.live-gallery div {
  display: grid;
  gap: 8px;
}

.live-qr {
  position: absolute;
  left: 28px;
  bottom: 30px;
  padding: 14px;
  border-radius: 8px;
  display: grid;
  gap: 12px;
}

.live-debug {
  position: absolute;
  left: 24px;
  top: 96px;
  color: #8da5ba;
  font: 11px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace;
  opacity: 0.84;
  max-width: 320px;
}

@media (max-width: 760px) {
  .live-topbar {
    flex-wrap: wrap;
    padding: 12px;
  }

  .live-action,
  .live-gallery {
    left: 12px;
    right: 12px;
    bottom: 16px;
    transform: none;
    grid-template-columns: 1fr 1fr;
  }

  .live-gallery article {
    grid-column: 1 / -1;
    grid-template-columns: 96px 1fr;
  }

  .live-gallery img {
    width: 96px;
    height: 124px;
  }
}
</style>
