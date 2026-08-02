<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const evaluations = ref([])
const products = ref([])
const selectedProducts = ref([])
const sampleImages = ref([])
const provider = ref('mock')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')

async function load() {
  loading.value = true
  try {
    const [evaluationResponse, productResponse] = await Promise.all([
      api.get('/admin/ai-evaluations'),
      api.get('/admin/products', { params: { readiness: 'ai_candidate' } }),
    ])
    evaluations.value = evaluationResponse.data.data || []
    products.value = productResponse.data.data || []
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

function setSamples(event) {
  sampleImages.value = Array.from(event.target.files || [])
}

function toggleProduct(id) {
  if (selectedProducts.value.includes(id)) {
    selectedProducts.value = selectedProducts.value.filter((value) => value !== id)
    return
  }
  if (selectedProducts.value.length < 5) {
    selectedProducts.value = [...selectedProducts.value, id]
  }
}

async function createEvaluation() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const body = new FormData()
    body.append('provider', provider.value)
    selectedProducts.value.forEach((id) => body.append('product_ids[]', id))
    sampleImages.value.forEach((file) => body.append('sample_images[]', file))
    await api.post('/admin/ai-evaluations', body)
    selectedProducts.value = []
    sampleImages.value = []
    success.value = 'Evaluation batch queued.'
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

async function rate(evaluation, item, rating) {
  const response = await api.patch(`/admin/ai-evaluations/${evaluation.id}/items/${item.id}`, { rating })
  const index = evaluations.value.findIndex((entry) => entry.id === evaluation.id)
  if (index >= 0) evaluations.value[index] = response.data.evaluation
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="AI bench" title="Try-on evaluation" description="Run provider quality checks with real body samples before enabling cloud AI for kiosk users." />

  <p v-if="error" class="form-error">{{ error }}</p>
  <p v-if="success" class="form-success">{{ success }}</p>

  <section class="panel evaluation-form">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">New evaluation</p>
        <h2>Sample body photos + production-ready products</h2>
      </div>
      <StatusPill :value="provider" />
    </div>
    <form @submit.prevent="createEvaluation">
      <div class="form-grid">
        <label>Provider
          <select v-model="provider">
            <option value="mock">Mock</option>
            <option value="nvidia">NVIDIA evaluation</option>
          </select>
        </label>
        <label>Body samples
          <input type="file" accept="image/*" multiple required @change="setSamples">
        </label>
      </div>

      <div class="product-picker">
        <button
          v-for="product in products"
          :key="product.id"
          type="button"
          :class="{ active: selectedProducts.includes(product.id) }"
          @click="toggleProduct(product.id)"
        >
          <span>{{ product.name }}</span>
          <small>{{ product.sku }} - {{ product.readiness?.label || 'AI Candidate' }}</small>
        </button>
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" :disabled="saving || !selectedProducts.length || !sampleImages.length">
          {{ saving ? 'Queuing...' : 'Queue evaluation' }}
        </button>
      </div>
    </form>
  </section>

  <section class="evaluation-list">
    <article class="panel evaluation-card" v-for="evaluation in evaluations" :key="evaluation.id">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">{{ evaluation.provider }}</p>
          <h2>{{ evaluation.item_count }} generated comparisons</h2>
          <p class="muted">{{ evaluation.completed_count }}/{{ evaluation.item_count }} complete - usable rate {{ evaluation.usable_rate ?? '-' }}%</p>
        </div>
        <StatusPill :value="evaluation.status" />
      </div>

      <div class="evaluation-items">
        <article v-for="item in evaluation.items" :key="item.id" class="evaluation-item">
          <img :src="item.job?.result_url || item.sample_image_url" :alt="item.product?.name || 'Evaluation result'">
          <div>
            <strong>{{ item.product?.name }}</strong>
            <StatusPill :value="item.job?.status || 'queued'" />
            <small v-if="item.job?.error" class="danger-text">{{ item.job.error }}</small>
            <div class="rating-row">
              <button class="text-btn" :class="{ active: item.rating === 'good' }" @click="rate(evaluation, item, 'good')">Good</button>
              <button class="text-btn" :class="{ active: item.rating === 'usable' }" @click="rate(evaluation, item, 'usable')">Usable</button>
              <button class="text-btn danger-text" :class="{ active: item.rating === 'bad' }" @click="rate(evaluation, item, 'bad')">Bad</button>
            </div>
          </div>
        </article>
      </div>
    </article>
    <div v-if="!loading && !evaluations.length" class="empty-state">
      <h3>No evaluations yet</h3>
      <p>Queue a mock run first, then use this page for cloud provider quality checks.</p>
    </div>
  </section>
</template>
