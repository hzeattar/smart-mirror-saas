<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { errorMessage } from '../lib/api'

const email = ref('admin@smartmirror.test')
const password = ref('ChangeMe123!')
const error = ref('')
const auth = useAuth()
const router = useRouter()

async function submit() {
  error.value = ''
  try { await auth.login(email.value, password.value); router.push('/') }
  catch (e) { error.value = errorMessage(e) }
}
</script>
<template>
  <div class="auth-page">
    <div class="auth-visual"><div class="visual-orb"></div><div class="auth-copy"><span class="kicker">AR RETAIL OPERATING SYSTEM</span><h1>Turn every fitting room into a measurable sales channel.</h1><p>Manage garments, smart mirrors, sizing data and customer requests from one place.</p></div></div>
    <form class="auth-card" @submit.prevent="submit">
      <div class="brand"><span class="brand-mark">SM</span><div><strong>Smart Mirror</strong><small>Retail Console</small></div></div>
      <div><p class="eyebrow">Welcome back</p><h2>Sign in to your store</h2></div>
      <label>Email<input v-model="email" type="email" autocomplete="email" required></label>
      <label>Password<input v-model="password" type="password" autocomplete="current-password" required></label>
      <p v-if="error" class="form-error">{{ error }}</p>
      <button class="btn btn-primary btn-wide" :disabled="auth.state.loading">{{ auth.state.loading ? 'Signing in…' : 'Sign in' }}</button>
      <p class="demo-note">Demo credentials are prefilled when demo seeding is enabled.</p>
    </form>
  </div>
</template>
