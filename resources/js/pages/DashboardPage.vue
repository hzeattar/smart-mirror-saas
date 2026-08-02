<script setup>
import { computed, onMounted, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'

const stats = ref(null)
const loading = ref(false)
const error = ref('')
const refreshedAt = ref(null)

const cards = [
  ['products', 'Catalog products', 'garments ready for mirrors'],
  ['orders_today', 'Orders today', 'requests created today'],
  ['pending_orders', 'Open workflow', 'orders needing attention'],
  ['online_mirrors', 'Online mirrors', 'devices currently connected'],
  ['mirror_sessions_today', 'Mirror sessions', 'devices sending telemetry today'],
  ['ai_batches_today', 'AI batches', 'gallery sessions created today'],
  ['ai_completion_rate', 'AI completion', 'completed jobs percentage'],
  ['ai_average_processing_seconds', 'AI seconds', 'average completed job time'],
  ['average_fps_today', 'Avg FPS', 'reported by kiosk telemetry today'],
  ['capture_completion_rate', 'Capture rate', 'captures submitted after burst'],
]

const revenue = computed(() => Number(stats.value?.revenue_today || 0).toLocaleString('ar-EG'))

async function load() {
  loading.value = true
  error.value = ''
  try {
    stats.value = (await api.get('/admin/dashboard')).data.stats
    refreshedAt.value = new Date()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="Operations" title="Retail overview" description="A live snapshot of your virtual fitting room network.">
    <button class="btn btn-secondary" :disabled="loading" @click="load">{{ loading ? 'Refreshing...' : 'Refresh' }}</button>
  </PageHeader>

  <p v-if="error" class="form-error">{{ error }}</p>
  <p v-if="refreshedAt" class="muted page-note">Last refreshed {{ refreshedAt.toLocaleTimeString() }}</p>

  <section class="stats-grid">
    <article v-for="card in cards" :key="card[0]" class="stat-card">
      <span>{{ card[1] }}</span>
      <strong>{{ stats?.[card[0]] ?? '-' }}</strong>
      <small>{{ card[2] }}</small>
    </article>
  </section>

  <section class="split-grid">
    <article class="panel hero-panel">
      <p class="eyebrow">Today's revenue</p>
      <h2>{{ revenue }} EGP</h2>
      <p class="muted">Revenue from completed and active orders created today.</p>
      <router-link class="btn btn-primary" to="/orders">Open live orders</router-link>
    </article>
    <article class="panel checklist">
      <p class="eyebrow">Launch checklist</p>
      <h2>Keep the pilot healthy</h2>
      <ol>
        <li>Use production-ready products only.</li>
        <li>Keep one mirror online and sending telemetry.</li>
        <li>Check mock AI batches after every kiosk run.</li>
        <li>Review failed jobs before store opening.</li>
      </ol>
      <router-link class="text-link" to="/mirrors">Manage devices -></router-link>
    </article>
  </section>
</template>
