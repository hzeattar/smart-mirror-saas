<script setup>
import { onMounted, ref } from 'vue'
import api,{errorMessage} from '../lib/api'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
const mirrors=ref([]),locationName=ref(''),error=ref(''),created=ref(null)
async function load(){try{mirrors.value=(await api.get('/admin/mirrors')).data.mirrors}catch(e){error.value=errorMessage(e)}}
async function create(){try{created.value=(await api.post('/admin/mirrors',{location_name:locationName.value})).data.mirror;locationName.value='';await load()}catch(e){error.value=errorMessage(e)}}
async function rotate(m){if(!confirm('This disconnects the current device. Continue?'))return;created.value=(await api.post(`/admin/mirrors/${m.id}/rotate-code`)).data.mirror;await load()}
onMounted(load)
</script>
<template>
  <PageHeader eyebrow="Devices" title="Smart mirrors" description="Pair and monitor camera clients installed inside your stores." />
  <p v-if="error" class="form-error">{{error}}</p>
  <section class="split-grid mirror-setup"><form class="panel" @submit.prevent="create"><p class="eyebrow">New device</p><h2>Create a pairing code</h2><label>Mirror location<input v-model="locationName" placeholder="Cairo Festival City — Fitting Room 2" required></label><button class="btn btn-primary">Generate code</button></form><article class="panel code-panel"><p class="eyebrow">Latest pairing code</p><template v-if="created"><div class="pairing-code">{{created.pairing_code}}</div><p>Run the Python client and enter this code. Pairing rotates the device API token securely.</p></template><p v-else class="muted">Create or rotate a mirror to reveal a one-time pairing code.</p></article></section>
  <section class="table-panel"><table><thead><tr><th>Location</th><th>Device</th><th>Status</th><th>Last seen</th><th>Session</th><th>Latest AI</th><th></th></tr></thead><tbody><tr v-for="m in mirrors" :key="m.id"><td><strong>{{m.location_name}}</strong><small>{{m.public_id}}</small></td><td>{{m.device_name||'Not paired'}}</td><td><StatusPill :value="m.status" /></td><td>{{m.last_seen_at?new Date(m.last_seen_at).toLocaleString():'Never'}}</td><td><template v-if="m.session_health"><strong>{{m.session_health.last_fps || 'â€”'}} FPS</strong><small>{{m.session_health.last_event || 'runtime'}}</small></template><template v-else-if="m.latest_session_event"><strong>{{m.latest_session_event.fps || 'â€”'}} FPS</strong><small>{{m.latest_session_event.event}}</small></template><span v-else class="muted">No telemetry</span></td><td><template v-if="m.latest_try_on_batch"><StatusPill :value="m.latest_try_on_batch.status" /><small>{{m.latest_try_on_batch.completed_count}}/{{m.latest_try_on_batch.outfit_count}} outfits</small></template><template v-else-if="m.latest_try_on_job"><StatusPill :value="m.latest_try_on_job.status" /><small>{{new Date(m.latest_try_on_job.created_at).toLocaleString()}}</small></template><span v-else class="muted">None</span></td><td><button class="text-btn" @click="rotate(m)">Rotate code</button></td></tr></tbody></table></section>
</template>
