<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const products = ref([])
const categories = ref([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const showForm = ref(false)
const editingId = ref(null)

const emptySize = () => ({
  size_label: '',
  shoulder_width_cm: '',
  chest_width_cm: '',
  waist_width_cm: '',
  hip_width_cm: '',
  sleeve_length_cm: '',
  fit_ease_cm: '4',
  height_cm: '',
})

const defaultFitProfile = () => ({
  shoulder_expand: '0.10',
  top_offset_ratio: '0.07',
  height_ratio: '1.28',
  forearm_occlusion: true,
})

const defaultTextureAnchor = () => ({ left: '0', right: '0', top: '0', bottom: '0' })

const form = reactive({
  name: '',
  sku: '',
  category_id: '',
  description: '',
  garment_type: 'tshirt',
  unit_price: '',
  currency: 'EGP',
  status: 'active',
  sizes: [emptySize()],
  fit_profile: defaultFitProfile(),
  texture_anchor: defaultTextureAnchor(),
  base_image: null,
  texture_image: null,
})

const formTitle = computed(() => editingId.value ? 'Edit product' : 'Add product')

async function load() {
  loading.value = true
  try {
    const [productResponse, categoryResponse] = await Promise.all([
      api.get('/admin/products'),
      api.get('/admin/categories'),
    ])
    products.value = productResponse.data.data
    categories.value = categoryResponse.data.categories
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

onMounted(load)

function reset() {
  Object.assign(form, {
    name: '',
    sku: '',
    category_id: '',
    description: '',
    garment_type: 'tshirt',
    unit_price: '',
    currency: 'EGP',
    status: 'active',
    sizes: [emptySize()],
    fit_profile: defaultFitProfile(),
    texture_anchor: defaultTextureAnchor(),
    base_image: null,
    texture_image: null,
  })
  editingId.value = null
  showForm.value = false
}

function openNew() {
  reset()
  showForm.value = true
}

function edit(product) {
  editingId.value = product.id
  Object.assign(form, {
    name: product.name,
    sku: product.sku || '',
    category_id: product.category_id || '',
    description: product.description || '',
    garment_type: product.garment_type || 'tshirt',
    unit_price: product.unit_price,
    currency: product.currency,
    status: product.status,
    sizes: product.sizing_charts.map((size) => ({
      size_label: size.size_label,
      shoulder_width_cm: size.shoulder_width_cm,
      chest_width_cm: size.chest_width_cm,
      waist_width_cm: size.waist_width_cm || '',
      hip_width_cm: size.hip_width_cm || '',
      sleeve_length_cm: size.sleeve_length_cm || '',
      fit_ease_cm: size.fit_ease_cm || '4',
      height_cm: size.height_cm,
    })),
    fit_profile: { ...defaultFitProfile(), ...(product.fit_profile || {}) },
    texture_anchor: { ...defaultTextureAnchor(), ...(product.texture_anchor || {}) },
    base_image: null,
    texture_image: null,
  })
  showForm.value = true
  scrollTo({ top: 0, behavior: 'smooth' })
}

function addSize() { form.sizes.push(emptySize()) }
function removeSize(index) { if (form.sizes.length > 1) form.sizes.splice(index, 1) }
function file(event, key) { form[key] = event.target.files[0] || null }

function appendNested(body, prefix, values) {
  Object.entries(values).forEach(([key, value]) => {
    if (value !== null && value !== '') {
      body.append(`${prefix}[${key}]`, typeof value === 'boolean' ? (value ? '1' : '0') : value)
    }
  })
}

async function save() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const body = new FormData()
    const scalarKeys = [
      'name', 'sku', 'category_id', 'description', 'garment_type',
      'unit_price', 'currency', 'status', 'base_image', 'texture_image',
    ]
    scalarKeys.forEach((key) => {
      const value = form[key]
      if (value !== null && value !== '') body.append(key, value)
    })
    appendNested(body, 'fit_profile', form.fit_profile)
    appendNested(body, 'texture_anchor', form.texture_anchor)
    form.sizes.forEach((size, index) => appendNested(body, `sizes[${index}]`, size))

    if (editingId.value) {
      body.append('_method', 'PUT')
      await api.post(`/admin/products/${editingId.value}`, body)
    } else {
      await api.post('/admin/products', body)
    }
    success.value = 'Product and fit measurements saved successfully.'
    reset()
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

async function remove(product) {
  if (!confirm(`Delete ${product.name}?`)) return
  await api.delete(`/admin/products/${product.id}`)
  await load()
}

async function reprocess(product) {
  await api.post(`/admin/products/${product.id}/reprocess`)
  await load()
}

function readiness(product) {
  if (!product.texture_image_url && !product.base_image_url) return 'needs_image'
  if (product.background_removal_status === 'failed') return 'failed'
  if (!product.texture_image_url) return 'preparing'
  return 'ready'
}
</script>

<template>
  <PageHeader eyebrow="Catalog" title="Products & sizing" description="Upload real garment assets and the measurements used by the Fit Engine v2.">
    <button class="btn btn-primary" @click="openNew">+ Add product</button>
  </PageHeader>

  <p v-if="error" class="form-error">{{ error }}</p>
  <p v-if="success" class="form-success">{{ success }}</p>

  <section v-if="showForm" class="panel product-form">
    <div class="panel-heading">
      <div><p class="eyebrow">Product editor</p><h2>{{ formTitle }}</h2></div>
      <button class="icon-btn" @click="reset">×</button>
    </div>

    <form @submit.prevent="save">
      <div class="form-grid">
        <label>Product name<input v-model="form.name" required></label>
        <label>SKU<input v-model="form.sku"></label>
        <label>Category
          <select v-model="form.category_id">
            <option value="">Uncategorized</option>
            <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
          </select>
        </label>
        <label>Garment type
          <select v-model="form.garment_type">
            <option value="tshirt">T-shirt</option>
            <option value="polo">Polo</option>
            <option value="hoodie">Hoodie</option>
            <option value="jacket">Jacket</option>
            <option value="dress">Dress</option>
            <option value="trousers">Trousers</option>
            <option value="suit">Suit</option>
            <option value="top">Other top</option>
          </select>
        </label>
        <label>Status
          <select v-model="form.status">
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
        <label>Price<input v-model="form.unit_price" type="number" min="0" step="0.01" required></label>
        <label>Currency<input v-model="form.currency" maxlength="3" required></label>
      </div>

      <label>Description<textarea v-model="form.description" rows="3"></textarea></label>

      <div class="upload-grid">
        <label class="upload-box">
          <strong>Front-facing store photo</strong>
          <span>Use a straight, centred product photo. Background removal runs automatically.</span>
          <input type="file" accept="image/*" @change="file($event, 'base_image')">
        </label>
        <label class="upload-box">
          <strong>Transparent fitting texture</strong>
          <span>Recommended: realistic front-facing PNG/WebP with the full garment visible.</span>
          <input type="file" accept="image/png,image/webp" @change="file($event, 'texture_image')">
        </label>
      </div>

      <div class="sizes-header">
        <div><p class="eyebrow">Sizing chart</p><h3>Flat garment measurements in centimetres</h3></div>
        <button type="button" class="btn btn-secondary" @click="addSize">+ Add size</button>
      </div>

      <div class="size-table-head">
        <span>Size</span><span>Shoulder</span><span>Chest</span><span>Waist</span><span>Hip</span><span>Sleeve</span><span>Length</span><span>Ease</span><span></span>
      </div>
      <div class="size-row size-row-v2" v-for="(size, index) in form.sizes" :key="index">
        <label><span>Label</span><input v-model="size.size_label" placeholder="M" required></label>
        <label><span>Shoulder</span><input v-model="size.shoulder_width_cm" type="number" step="0.1" required></label>
        <label><span>Chest</span><input v-model="size.chest_width_cm" type="number" step="0.1" required></label>
        <label><span>Waist</span><input v-model="size.waist_width_cm" type="number" step="0.1"></label>
        <label><span>Hip</span><input v-model="size.hip_width_cm" type="number" step="0.1"></label>
        <label><span>Sleeve</span><input v-model="size.sleeve_length_cm" type="number" step="0.1"></label>
        <label><span>Length</span><input v-model="size.height_cm" type="number" step="0.1" required></label>
        <label><span>Fit ease</span><input v-model="size.fit_ease_cm" type="number" step="0.1"></label>
        <button type="button" class="icon-btn danger" @click="removeSize(index)">×</button>
      </div>

      <details class="fit-tuning">
        <summary>Advanced AR fitting controls</summary>
        <div class="form-grid fit-grid">
          <label>Shoulder expansion<input v-model="form.fit_profile.shoulder_expand" type="number" min="0" max="0.5" step="0.01"></label>
          <label>Top offset ratio<input v-model="form.fit_profile.top_offset_ratio" type="number" min="-0.2" max="0.4" step="0.01"></label>
          <label>Garment height ratio<input v-model="form.fit_profile.height_ratio" type="number" min="0.8" max="2" step="0.01"></label>
          <label class="check-label"><input v-model="form.fit_profile.forearm_occlusion" type="checkbox"> Keep forearms in front of garment</label>
        </div>
      </details>

      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="reset">Cancel</button>
        <button class="btn btn-primary" :disabled="saving">{{ saving ? 'Saving…' : 'Save product' }}</button>
      </div>
    </form>
  </section>

  <section class="product-grid">
    <article class="product-card" v-for="product in products" :key="product.id">
      <div class="product-image">
        <img v-if="product.texture_image_url || product.base_image_url" :src="product.texture_image_url || product.base_image_url">
        <span v-else>No image</span>
      </div>
      <div class="product-body">
        <div class="product-title">
          <div><small>{{ product.sku || 'NO SKU' }}</small><h3>{{ product.name }}</h3></div>
          <StatusPill :value="product.status" />
        </div>
        <div class="product-meta">
          <span>{{ product.garment_type || 'top' }} · {{ product.sizing_charts.length }} sizes</span>
          <strong>{{ Number(product.unit_price).toLocaleString('ar-EG') }} {{ product.currency }}</strong>
        </div>
        <StatusPill :value="product.background_removal_status" />
        <div class="product-meta">
          <span>AI readiness</span>
          <StatusPill :value="readiness(product)" />
        </div>
        <div class="card-actions">
          <button class="text-btn" @click="edit(product)">Edit</button>
          <button v-if="product.base_image_path" class="text-btn" @click="reprocess(product)">Reprocess</button>
          <button class="text-btn danger-text" @click="remove(product)">Delete</button>
        </div>
      </div>
    </article>
    <div v-if="!loading && !products.length" class="empty-state">
      <h3>No products yet</h3><p>Add a garment image and its physical size chart.</p>
      <button class="btn btn-primary" @click="openNew">Create product</button>
    </div>
  </section>
</template>
