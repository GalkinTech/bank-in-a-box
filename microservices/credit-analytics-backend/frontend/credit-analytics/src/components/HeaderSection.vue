<template>
  <header class="widget-header">
    <div class="header-text">
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>
    <div class="header-actions">
      <button
        class="btn btn-secondary"
        type="button"
        :disabled="isDisabled"
        @click="emit('refresh')"
      >
        {{ refreshLabel }}
      </button>
    </div>
  </header>
</template>

<script setup>
const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    required: true,
  },
  refreshLabel: {
    type: String,
    default: 'Обновить данные',
  },
  isDisabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['refresh']);
</script>
