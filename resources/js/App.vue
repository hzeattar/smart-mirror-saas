<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const publicView = computed(() => route.meta.public || route.meta.guest)

onMounted(() => {
  if (auth.isAuthenticated.value && !route.meta.public) auth.refresh().catch(() => {})
})

async function signOut() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <router-view v-if="publicView" />
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">SM</span><div><strong>Smart Mirror</strong><small>{{ auth.state.user?.tenant?.name || 'Retail OS' }}</small></div></div>
      <nav>
        <router-link to="/"><span>◫</span> Overview</router-link>
        <router-link to="/products"><span>◩</span> Products</router-link>
        <router-link to="/orders"><span>◎</span> Live orders</router-link>
        <router-link to="/try-on-jobs"><span>AI</span> Try-on jobs</router-link>
        <router-link to="/mirrors"><span>◇</span> Mirrors</router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="avatar">{{ auth.state.user?.name?.slice(0, 1) || 'A' }}</div>
        <div class="user-meta"><strong>{{ auth.state.user?.name }}</strong><small>{{ auth.state.user?.role }}</small></div>
        <button class="icon-btn" @click="signOut" title="Sign out">↗</button>
      </div>
    </aside>
    <main class="main"><router-view /></main>
  </div>
</template>
