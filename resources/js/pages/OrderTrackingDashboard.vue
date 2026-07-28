<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api, { errorMessage } from '../lib/api'
import { createEcho } from '../lib/echo'
import { useAuth } from '../stores/auth'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const orders=ref([]),filter=ref(''),loading=ref(false),error=ref(''),live=ref(false)
const auth=useAuth();let timer=null,echo=null
const statuses=['pending','confirmed','preparing','ready','completed','cancelled']
const visible=computed(()=>filter.value?orders.value.filter(o=>o.status===filter.value):orders.value)
async function load(){loading.value=true;try{orders.value=(await api.get('/admin/orders',{params:{status:filter.value||undefined}})).data.data}catch(e){error.value=errorMessage(e)}finally{loading.value=false}}
async function update(order,status){await api.patch(`/admin/orders/${order.id}/status`,{status});order.status=status}
function upsert(incoming){const i=orders.value.findIndex(o=>o.public_id===incoming.id||o.id===incoming.id);if(i>=0)orders.value[i]={...orders.value[i],...incoming};else orders.value.unshift(incoming)}
onMounted(async()=>{await load();timer=setInterval(load,15000);echo=createEcho();const tenantId=auth.state.user?.tenant?.id;if(echo&&tenantId){echo.private(`tenant.${tenantId}.orders`).listen('.order.created',e=>upsert(e.order)).listen('.order.updated',e=>upsert(e.order));live.value=true}})
onBeforeUnmount(()=>{clearInterval(timer);if(echo){echo.disconnect()}})
</script>
<template>
  <PageHeader eyebrow="Fulfilment" title="Real-time orders" description="Requests created from smart mirrors and QR checkout."><div class="live-indicator" :class="{active:live}"><i></i>{{live?'WebSocket live':'Polling every 15s'}}</div></PageHeader>
  <div class="filter-bar"><button :class="{active:filter===''}" @click="filter='';load()">All</button><button v-for="s in statuses" :key="s" :class="{active:filter===s}" @click="filter=s;load()">{{s}}</button></div>
  <p v-if="error" class="form-error">{{error}}</p>
  <section class="orders-board">
    <article class="order-card" v-for="order in visible" :key="order.id"><div class="order-top"><div><small>{{order.order_number}}</small><h3>{{order.customer_name||'In-store customer'}}</h3><p>{{order.mirror?.location_name||order.mirror_location||'QR checkout'}}</p></div><StatusPill :value="order.status" /></div><div class="order-items"><div v-for="item in order.items" :key="item.id"><span>{{item.quantity}}× {{item.product_name}} <small v-if="item.size_label">/ {{item.size_label}}</small></span><strong>{{Number(item.line_total).toLocaleString('ar-EG')}}</strong></div></div><div class="order-total"><span>{{new Date(order.created_at).toLocaleString()}}</span><strong>{{Number(order.total).toLocaleString('ar-EG')}} {{order.currency}}</strong></div><select :value="order.status" @change="update(order,$event.target.value)"><option v-for="s in statuses" :value="s" :key="s">Move to {{s}}</option></select></article>
    <div v-if="!loading&&!visible.length" class="empty-state"><h3>No orders in this view</h3><p>New requests will appear automatically.</p></div>
  </section>
</template>
