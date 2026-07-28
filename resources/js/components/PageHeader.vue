<script setup>
defineProps({ title: String, eyebrow: String, description: String })
</script>
<template>
  <header class="page-header">
    <div><p class="eyebrow">{{ eyebrow }}</p><h1>{{ title }}</h1><p v-if="description" class="muted">{{ description }}</p></div>
    <div class="header-actions"><slot /></div>
  </header>
</template>
