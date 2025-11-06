<template>
  <section class="content credits-section">
    <div v-if="state === 'loading'" class="state state-loading">
      <div class="loader"></div>
      <p>{{ loadingMessage }}</p>
    </div>

    <div v-else-if="state === 'error'" class="state state-error">
      <h2>Не удалось получить данные</h2>
      <ul>
        <li v-for="(message, index) in errorMessages" :key="index">{{ message }}</li>
      </ul>
      <button class="btn btn-primary" type="button" @click="$emit('retry')">Попробовать снова</button>
    </div>

    <div v-else-if="state === 'empty'" class="state state-empty">
      <div class="empty-icon">🔍</div>
      <h2>{{ emptyTitle }}</h2>
      <p>{{ emptyDescription }}</p>
    </div>

    <LoanCardsWrapper
      v-else
      :loans="loans"
      :selected-loan-id="selectedLoanId"
      :is-mobile="isMobile"
      :current-slide="currentSlide"
      :is-prev-disabled="isPrevDisabled"
      :is-next-disabled="isNextDisabled"
      :loans-track-ref="loansTrackRef"
      :format-currency="formatCurrency"
      :format-percent="formatPercent"
      :format-term="formatTerm"
      @select-loan="(agreementId, index) => $emit('select-loan', agreementId, index)"
      @next-loan="$emit('next-loan')"
      @prev-loan="$emit('prev-loan')"
      @go-to-loan="$emit('go-to-loan', $event)"
      @open-application="$emit('open-application', $event)"
    />
  </section>
</template>

<script setup>
import LoanCardsWrapper from './LoanCardsWrapper.vue';

const props = defineProps({
  loans: {
    type: Array,
    default: () => [],
  },
  state: {
    type: String,
    default: 'ready',
  },
  errorMessages: {
    type: Array,
    default: () => [],
  },
  loadingMessage: {
    type: String,
    default: 'Загружаем данные кредитов и предложения...'},
  emptyTitle: {
    type: String,
    default: 'Кредиты не найдены',
  },
  emptyDescription: {
    type: String,
    default: 'Чтобы получить предложения по рефинансированию, оформите кредит или свяжитесь с банком.',
  },
  selectedLoanId: {
    type: [String, Number, null],
    default: null,
  },
  isMobile: {
    type: Boolean,
    default: false,
  },
  currentSlide: {
    type: Number,
    default: 0,
  },
  isPrevDisabled: {
    type: Boolean,
    default: false,
  },
  isNextDisabled: {
    type: Boolean,
    default: false,
  },
  loansTrackRef: {
    type: [Object, Function],
    default: null,
  },
  formatCurrency: {
    type: Function,
    required: true,
  },
  formatPercent: {
    type: Function,
    required: true,
  },
  formatTerm: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(['select-loan', 'next-loan', 'prev-loan', 'go-to-loan', 'open-application']);

// Ensure props are used to avoid compile warnings
void props;
void emit;
</script>
