<template>
  <section v-if="contentState === 'ready'" class="summary-grid">
    <article
      v-for="(card, index) in cards"
      :key="card.label ?? index"
      class="summary-card"
      :class="{ primary: card.variant === 'primary' }"
    >
      <div class="summary-label">{{ card.label }}</div>
      <div class="summary-value" :class="card.valueClass">{{ card.value }}</div>
      <div class="summary-caption">{{ card.caption }}</div>
    </article>
  </section>
</template>

<script setup>
const props = defineProps({
  cards: {
    type: Array,
    default: () => [],
  },
  contentState: {
    type: String,
    default: 'ready',
  },
});

void props;
</script>
