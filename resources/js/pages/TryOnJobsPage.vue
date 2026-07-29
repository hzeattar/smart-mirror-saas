<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const jobs = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  try {
    jobs.value = (await api.get('/admin/try-on-jobs')).data.data
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  setInterval(load, 10000)
})
</script>

<template>
  <PageHeader eyebrow="AI" title="Try-on jobs" description="Generated fitting-room results from smart mirrors." />
  <p v-if="error" class="form-error">{{ error }}</p>
  <section class="table-panel">
    <table>
      <thead><tr><th>Status</th><th>Product</th><th>Mirror</th><th>Provider</th><th>Timing</th><th>Result</th></tr></thead>
      <tbody>
        <tr v-for="job in jobs" :key="job.id">
          <td><StatusPill :value="job.status" /></td>
          <td><strong>{{ job.product?.name || 'Deleted product' }}</strong><small>{{ job.product?.sku || job.id }}</small></td>
          <td>{{ job.mirror?.location_name || 'Unknown mirror' }}<small>{{ job.mirror?.device_name || '' }}</small></td>
          <td>{{ job.provider }}</td>
          <td>
            {{ new Date(job.created_at).toLocaleString() }}
            <small v-if="job.completed_at">Completed {{ new Date(job.completed_at).toLocaleTimeString() }}</small>
            <small v-if="job.failed_at" class="danger-text">{{ job.error || 'Failed' }}</small>
          </td>
          <td><a v-if="job.result_url" class="text-link" :href="job.result_url" target="_blank">Open result</a><span v-else class="muted">Waiting</span></td>
        </tr>
      </tbody>
    </table>
    <div v-if="!loading && !jobs.length" class="empty-state"><h3>No AI jobs yet</h3><p>Use AI Snapshot from the mirror to create the first job.</p></div>
  </section>
</template>
