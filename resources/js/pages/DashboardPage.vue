<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'

const stats = ref(null)
const error = ref('')
onMounted(async () => { try { stats.value = (await api.get('/admin/dashboard')).data.stats } catch (e) { error.value = errorMessage(e) } })
const cards = [
  ['products', 'Catalog products', 'garments ready for mirrors'],
  ['orders_today', 'Orders today', 'requests created today'],
  ['pending_orders', 'Open workflow', 'orders needing attention'],
  ['online_mirrors', 'Online mirrors', 'devices currently connected'],
]
</script>
<template>
  <PageHeader eyebrow="Operations" title="Retail overview" description="A live snapshot of your virtual fitting room network." />
  <p v-if="error" class="form-error">{{ error }}</p>
  <section class="stats-grid">
    <article v-for="card in cards" :key="card[0]" class="stat-card"><span>{{ card[1] }}</span><strong>{{ stats?.[card[0]] ?? '—' }}</strong><small>{{ card[2] }}</small></article>
  </section>
  <section class="split-grid">
    <article class="panel hero-panel"><p class="eyebrow">Today’s revenue</p><h2>{{ Number(stats?.revenue_today || 0).toLocaleString('ar-EG') }} EGP</h2><p class="muted">Revenue from completed and active orders created today.</p><router-link class="btn btn-primary" to="/orders">Open live orders</router-link></article>
    <article class="panel checklist"><p class="eyebrow">Launch checklist</p><h2>Connect your first mirror</h2><ol><li>Create a mirror device</li><li>Use the pairing code in the Python client</li><li>Upload a transparent garment texture</li><li>Start receiving fitting-room requests</li></ol><router-link class="text-link" to="/mirrors">Manage devices →</router-link></article>
  </section>
</template>
