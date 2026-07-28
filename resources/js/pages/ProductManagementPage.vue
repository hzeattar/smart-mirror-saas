<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const products = ref([]), categories = ref([]), loading = ref(false), saving = ref(false)
const error = ref(''), success = ref(''), showForm = ref(false), editingId = ref(null)
const emptySize = () => ({ size_label: '', shoulder_width_cm: '', chest_width_cm: '', height_cm: '' })
const form = reactive({ name:'', sku:'', category_id:'', description:'', unit_price:'', currency:'EGP', status:'active', sizes:[emptySize()], base_image:null, texture_image:null })
const formTitle = computed(() => editingId.value ? 'Edit product' : 'Add product')

async function load() { loading.value=true; try { const [p,c]=await Promise.all([api.get('/admin/products'),api.get('/admin/categories')]); products.value=p.data.data; categories.value=c.data.categories } catch(e){error.value=errorMessage(e)} finally{loading.value=false} }
onMounted(load)
function reset(){ Object.assign(form,{name:'',sku:'',category_id:'',description:'',unit_price:'',currency:'EGP',status:'active',sizes:[emptySize()],base_image:null,texture_image:null}); editingId.value=null; showForm.value=false }
function openNew(){ reset(); showForm.value=true }
function edit(p){ editingId.value=p.id; Object.assign(form,{name:p.name,sku:p.sku||'',category_id:p.category_id||'',description:p.description||'',unit_price:p.unit_price,currency:p.currency,status:p.status,sizes:p.sizing_charts.map(s=>({size_label:s.size_label,shoulder_width_cm:s.shoulder_width_cm,chest_width_cm:s.chest_width_cm,height_cm:s.height_cm})),base_image:null,texture_image:null}); showForm.value=true; scrollTo({top:0,behavior:'smooth'}) }
function addSize(){form.sizes.push(emptySize())}
function removeSize(i){if(form.sizes.length>1) form.sizes.splice(i,1)}
function file(event,key){form[key]=event.target.files[0]||null}
async function save(){saving.value=true;error.value='';success.value='';try{const body=new FormData();Object.entries(form).forEach(([k,v])=>{if(k==='sizes')body.append('sizes',JSON.stringify(v));else if(v!==null&&v!=='')body.append(k,v)});form.sizes.forEach((s,i)=>Object.entries(s).forEach(([k,v])=>body.append(`sizes[${i}][${k}]`,v)));body.delete('sizes');if(editingId.value){body.append('_method','PUT');await api.post(`/admin/products/${editingId.value}`,body)}else await api.post('/admin/products',body);success.value='Product saved successfully.';reset();await load()}catch(e){error.value=errorMessage(e)}finally{saving.value=false}}
async function remove(p){if(!confirm(`Delete ${p.name}?`))return;await api.delete(`/admin/products/${p.id}`);await load()}
async function reprocess(p){await api.post(`/admin/products/${p.id}/reprocess`);await load()}
</script>
<template>
  <PageHeader eyebrow="Catalog" title="Products & sizing" description="Upload garment assets and precise measurements used by the AR engine."><button class="btn btn-primary" @click="openNew">+ Add product</button></PageHeader>
  <p v-if="error" class="form-error">{{ error }}</p><p v-if="success" class="form-success">{{ success }}</p>
  <section v-if="showForm" class="panel product-form">
    <div class="panel-heading"><div><p class="eyebrow">Product editor</p><h2>{{ formTitle }}</h2></div><button class="icon-btn" @click="reset">×</button></div>
    <form @submit.prevent="save">
      <div class="form-grid"><label>Product name<input v-model="form.name" required></label><label>SKU<input v-model="form.sku"></label><label>Category<select v-model="form.category_id"><option value="">Uncategorized</option><option v-for="c in categories" :value="c.id" :key="c.id">{{c.name}}</option></select></label><label>Status<select v-model="form.status"><option value="active">Active</option><option value="draft">Draft</option><option value="inactive">Inactive</option></select></label><label>Price<input v-model="form.unit_price" type="number" min="0" step="0.01" required></label><label>Currency<input v-model="form.currency" maxlength="3" required></label></div>
      <label>Description<textarea v-model="form.description" rows="3"></textarea></label>
      <div class="upload-grid"><label class="upload-box"><strong>Base garment image</strong><span>JPG/PNG. Background removal runs automatically.</span><input type="file" accept="image/*" @change="file($event,'base_image')"></label><label class="upload-box"><strong>Transparent texture</strong><span>Optional PNG/WebP supplied directly to the mirror.</span><input type="file" accept="image/png,image/webp" @change="file($event,'texture_image')"></label></div>
      <div class="sizes-header"><div><p class="eyebrow">Sizing chart</p><h3>Exact garment measurements (cm)</h3></div><button type="button" class="btn btn-secondary" @click="addSize">+ Add size</button></div>
      <div class="size-row" v-for="(size,i) in form.sizes" :key="i"><label>Label<input v-model="size.size_label" placeholder="M" required></label><label>Shoulder<input v-model="size.shoulder_width_cm" type="number" step="0.1" required></label><label>Chest<input v-model="size.chest_width_cm" type="number" step="0.1" required></label><label>Height<input v-model="size.height_cm" type="number" step="0.1" required></label><button type="button" class="icon-btn danger" @click="removeSize(i)">×</button></div>
      <div class="form-actions"><button type="button" class="btn btn-secondary" @click="reset">Cancel</button><button class="btn btn-primary" :disabled="saving">{{saving?'Saving…':'Save product'}}</button></div>
    </form>
  </section>
  <section class="product-grid">
    <article class="product-card" v-for="p in products" :key="p.id"><div class="product-image"><img v-if="p.texture_image_url||p.base_image_url" :src="p.texture_image_url||p.base_image_url"><span v-else>No image</span></div><div class="product-body"><div class="product-title"><div><small>{{p.sku||'NO SKU'}}</small><h3>{{p.name}}</h3></div><StatusPill :value="p.status" /></div><div class="product-meta"><span>{{p.sizing_charts.length}} sizes</span><strong>{{Number(p.unit_price).toLocaleString('ar-EG')}} {{p.currency}}</strong></div><StatusPill :value="p.background_removal_status" /><div class="card-actions"><button class="text-btn" @click="edit(p)">Edit</button><button v-if="p.base_image_path" class="text-btn" @click="reprocess(p)">Reprocess</button><button class="text-btn danger-text" @click="remove(p)">Delete</button></div></div></article>
    <div v-if="!loading&&!products.length" class="empty-state"><h3>No products yet</h3><p>Add your first garment and its physical sizing chart.</p><button class="btn btn-primary" @click="openNew">Create product</button></div>
  </section>
</template>
