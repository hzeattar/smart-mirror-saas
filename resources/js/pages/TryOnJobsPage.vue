<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const jobs = ref([])
const batches = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  try {
    const [batchResponse, jobResponse] = await Promise.all([
      api.get('/admin/try-on-batches'),
      api.get('/admin/try-on-jobs'),
    ])
    batches.value = batchResponse.data.data
    jobs.value = jobResponse.data.data
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
    <div class="section-heading">
      <div>
        <h3>Outfit batches</h3>
        <p>Hybrid mirror gallery sessions grouped by snapshot.</p>
      </div>
    </div>
    <table>
      <thead><tr><th>Status</th><th>Mirror</th><th>Progress</th><th>Outfits</th><th>Created</th></tr></thead>
      <tbody>
        <tr v-for="batch in batches" :key="batch.id">
          <td><StatusPill :value="batch.status" /></td>
          <td>{{ batch.mirror?.location_name || 'Unknown mirror' }}<small>{{ batch.mirror?.device_name || '' }}</small></td>
          <td>{{ batch.completed_count }}/{{ batch.outfit_count }} ready<small v-if="batch.failed_count" class="danger-text">{{ batch.failed_count }} failed</small></td>
          <td>
            <div v-for="job in batch.jobs" :key="job.id" class="stacked-line">
              <span>{{ job.product?.name || 'Deleted product' }}</span>
              <a v-if="job.result_url" class="text-link" :href="job.result_url" target="_blank">Open</a>
            </div>
          </td>
          <td>{{ new Date(batch.created_at).toLocaleString() }}<small v-if="batch.error" class="danger-text">{{ batch.error }}</small></td>
        </tr>
      </tbody>
    </table>
    <div v-if="!loading && !batches.length" class="empty-state"><h3>No outfit batches yet</h3><p>Run the hybrid mirror experience to create the first gallery batch.</p></div>
  </section>
  <section class="table-panel">
    <div class="section-heading">
      <div>
        <h3>Individual jobs</h3>
        <p>Single AI outputs and batch child jobs.</p>
      </div>
    </div>
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
