<script setup>
defineProps({ value: { type: String, default: 'unknown' } })
</script>
<template><span class="status-pill" :class="`status-${value}`"><i></i>{{ value.replaceAll('_', ' ') }}</span></template>
