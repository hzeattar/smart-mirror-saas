<script setup>
import { computed } from 'vue'

const props = defineProps({ value: { type: String, default: 'unknown' } })
const display = computed(() => props.value.replaceAll('_', ' '))
const statusClass = computed(() => `status-${props.value.toLowerCase().replaceAll(' ', '_')}`)
</script>
<template><span class="status-pill" :class="statusClass"><i></i>{{ display }}</span></template>
