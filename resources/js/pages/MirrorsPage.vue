<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const mirrors = ref([])
const locationName = ref('')
const error = ref('')
const success = ref('')
const created = ref(null)
const editing = ref(null)
const savingProfile = ref(false)
const loading = ref(false)
const refreshedAt = ref(null)

const profileForm = reactive({
  experience_mode: 'hybrid',
  outfit_count: 3,
  auto_start_delay_seconds: 1.5,
  capture_burst_count: 5,
  capture_duration_seconds: 2,
  gallery_timeout_seconds: 45,
  poll_interval_seconds: 2.5,
  pose_every_n: 3,
  hand_every_n: 3,
  kiosk_health_hud: true,
  gestures: {
    cooldown_seconds: 1.1,
    hold_seconds: 0.75,
    swipe_distance: 0.2,
  },
})

const hasMirrors = computed(() => mirrors.value.length > 0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    mirrors.value = (await api.get('/admin/mirrors')).data.mirrors
    refreshedAt.value = new Date()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

async function create() {
  error.value = ''
  success.value = ''
  try {
    created.value = (await api.post('/admin/mirrors', { location_name: locationName.value })).data.mirror
    locationName.value = ''
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

async function rotate(mirror) {
  if (!confirm('This disconnects the current device. Continue?')) return
  created.value = (await api.post(`/admin/mirrors/${mirror.id}/rotate-code`)).data.mirror
  await load()
}

function dateTime(value) {
  return value ? new Date(value).toLocaleString() : 'Never'
}

function profile(mirror) {
  return mirror.kiosk_profile?.config || {}
}

function startEdit(mirror) {
  editing.value = mirror
  const config = profile(mirror)
  Object.assign(profileForm, {
    experience_mode: config.experience_mode || 'hybrid',
    outfit_count: Number(config.outfit_count || 3),
    auto_start_delay_seconds: Number(config.auto_start_delay_seconds || 1.5),
    capture_burst_count: Number(config.capture_burst_count || 5),
    capture_duration_seconds: Number(config.capture_duration_seconds || 2),
    gallery_timeout_seconds: Number(config.gallery_timeout_seconds || 45),
    poll_interval_seconds: Number(config.poll_interval_seconds || 2.5),
    pose_every_n: Number(config.pose_every_n || 3),
    hand_every_n: Number(config.hand_every_n || 3),
    kiosk_health_hud: config.kiosk_health_hud !== false,
    gestures: {
      cooldown_seconds: Number(config.gestures?.cooldown_seconds || 1.1),
      hold_seconds: Number(config.gestures?.hold_seconds || 0.75),
      swipe_distance: Number(config.gestures?.swipe_distance || 0.2),
    },
  })
}

async function saveProfile() {
  if (!editing.value) return
  savingProfile.value = true
  error.value = ''
  success.value = ''
  try {
    await api.patch(`/admin/mirrors/${editing.value.id}/kiosk-config`, { config: profileForm })
    success.value = 'Kiosk profile updated. The client will reload it automatically.'
    editing.value = null
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    savingProfile.value = false
  }
}

function latestAi(mirror) {
  return mirror.latest_try_on_batch || mirror.latest_try_on_job || null
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="Pilot control" title="Store mirror control center" description="Monitor camera health, AI status, telemetry, and remote kiosk profiles for each mirror.">
    <button class="btn btn-secondary" :disabled="loading" @click="load">{{ loading ? 'Refreshing...' : 'Refresh' }}</button>
  </PageHeader>

  <p v-if="error" class="form-error">{{ error }}</p>
  <p v-if="success" class="form-success">{{ success }}</p>
  <p v-if="refreshedAt" class="muted page-note">Last refreshed {{ refreshedAt.toLocaleTimeString() }}</p>

  <section class="split-grid mirror-setup">
    <form class="panel" @submit.prevent="create">
      <p class="eyebrow">New device</p>
      <h2>Create a pairing code</h2>
      <label>Mirror location<input v-model="locationName" placeholder="Main Store - Fitting Room 1" required></label>
      <button class="btn btn-primary">Generate code</button>
    </form>
    <article class="panel code-panel">
      <p class="eyebrow">Latest pairing code</p>
      <template v-if="created">
        <div class="pairing-code">{{ created.pairing_code }}</div>
        <p>Run the Python client with this one-time code. Pairing rotates the device API token securely.</p>
      </template>
      <p v-else class="muted">Create or rotate a mirror to reveal a one-time pairing code.</p>
    </article>
  </section>

  <section class="mirror-control-grid" v-if="hasMirrors">
    <article class="panel mirror-card" v-for="mirror in mirrors" :key="mirror.id">
      <div class="mirror-card-head">
        <div>
          <p class="eyebrow">Mirror</p>
          <h2>{{ mirror.location_name }}</h2>
          <small>{{ mirror.device_name || 'Not paired' }} - {{ mirror.public_id }}</small>
        </div>
        <StatusPill :value="mirror.health?.status || mirror.status" />
      </div>

      <div class="badge-row">
        <span v-for="badge in mirror.health?.badges || []" :key="badge" class="health-badge">{{ badge }}</span>
      </div>

      <div class="metric-grid">
        <div><span>Last heartbeat</span><strong>{{ dateTime(mirror.last_seen_at) }}</strong></div>
        <div><span>FPS</span><strong>{{ mirror.health?.last_fps || '-' }}</strong></div>
        <div><span>Last gesture/event</span><strong>{{ mirror.health?.last_event || mirror.latest_session_event?.event || '-' }}</strong></div>
        <div><span>Profile version</span><strong>v{{ mirror.kiosk_profile?.version || 1 }}</strong></div>
        <div><span>Last telemetry</span><strong>{{ dateTime(mirror.health?.last_event_at || mirror.latest_session_event?.occurred_at) }}</strong></div>
        <div><span>Health severity</span><strong>{{ mirror.health?.severity || 'info' }}</strong></div>
        <div><span>Camera</span><strong>{{ mirror.health?.badges?.includes('No Camera') ? 'Check camera' : 'No error' }}</strong></div>
        <div><span>Profile mode</span><strong>{{ mirror.kiosk_profile?.config?.experience_mode || 'hybrid' }}</strong></div>
      </div>

      <div class="ops-grid">
        <div>
          <span>Latest AI</span>
          <template v-if="latestAi(mirror)">
            <StatusPill :value="latestAi(mirror).status" />
            <small v-if="mirror.latest_try_on_batch">{{ mirror.latest_try_on_batch.completed_count }}/{{ mirror.latest_try_on_batch.outfit_count }} outfits</small>
            <small v-else>{{ dateTime(latestAi(mirror).created_at) }}</small>
          </template>
          <strong v-else>None</strong>
        </div>
        <div>
          <span>API/AI status</span>
          <strong>{{ mirror.health?.badges?.includes('API Errors') ? 'API errors' : (mirror.health?.badges?.includes('AI Failing') ? 'AI failing' : 'Nominal') }}</strong>
        </div>
        <div>
          <span>Session</span>
          <strong>{{ mirror.health?.session_id || '-' }}</strong>
          <small>{{ mirror.health?.severity || 'info' }}</small>
        </div>
      </div>

      <div class="card-actions">
        <button class="text-btn" @click="startEdit(mirror)">Edit kiosk profile</button>
        <button class="text-btn" @click="rotate(mirror)">Rotate code</button>
      </div>
    </article>
  </section>
  <section v-else class="empty-state">
    <h3>No mirrors yet</h3>
    <p>Create a mirror and pair the Windows kiosk client.</p>
  </section>

  <section v-if="editing" class="panel profile-editor">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">Remote profile</p>
        <h2>{{ editing.location_name }}</h2>
      </div>
      <button class="icon-btn" @click="editing = null">x</button>
    </div>

    <form @submit.prevent="saveProfile">
      <div class="form-grid">
        <label>Experience mode
          <select v-model="profileForm.experience_mode">
            <option value="hybrid">Hybrid</option>
            <option value="live">Live fallback</option>
          </select>
        </label>
        <label>Outfit count<input v-model.number="profileForm.outfit_count" type="number" min="1" max="5"></label>
        <label>Auto-start delay<input v-model.number="profileForm.auto_start_delay_seconds" type="number" step="0.1" min="0.3" max="10"></label>
        <label>Burst count<input v-model.number="profileForm.capture_burst_count" type="number" min="1" max="10"></label>
        <label>Capture duration<input v-model.number="profileForm.capture_duration_seconds" type="number" step="0.1" min="0.5" max="8"></label>
        <label>Gallery timeout<input v-model.number="profileForm.gallery_timeout_seconds" type="number" min="5" max="300"></label>
        <label>Poll interval<input v-model.number="profileForm.poll_interval_seconds" type="number" step="0.1" min="1" max="15"></label>
        <label>Pose every N frames<input v-model.number="profileForm.pose_every_n" type="number" min="1" max="6"></label>
        <label>Hand every N frames<input v-model.number="profileForm.hand_every_n" type="number" min="1" max="6"></label>
        <label>Gesture cooldown<input v-model.number="profileForm.gestures.cooldown_seconds" type="number" step="0.05" min="0.2" max="5"></label>
        <label>Hold seconds<input v-model.number="profileForm.gestures.hold_seconds" type="number" step="0.05" min="0.2" max="3"></label>
        <label>Swipe distance<input v-model.number="profileForm.gestures.swipe_distance" type="number" step="0.01" min="0.05" max="0.8"></label>
        <label class="check-label"><input v-model="profileForm.kiosk_health_hud" type="checkbox"> Show health HUD</label>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="editing = null">Cancel</button>
        <button class="btn btn-primary" :disabled="savingProfile">{{ savingProfile ? 'Saving...' : 'Save profile' }}</button>
      </div>
    </form>
  </section>
</template>
