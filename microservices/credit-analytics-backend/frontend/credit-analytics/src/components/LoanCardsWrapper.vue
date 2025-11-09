<template>
  <div
    class="loans-section"
    :class="{ 'loans-section--carousel': isMobile }"
  >
    <div
      v-if="isMobile && loans.length > 1"
      class="loans-carousel-controls"
    >
      <button
        class="carousel-btn carousel-btn--prev"
        type="button"
        :disabled="isPrevDisabled"
        @click="$emit('prev-loan')"
        aria-label="Предыдущий кредит"
      >
        ‹
      </button>
      <button
        class="carousel-btn carousel-btn--next"
        type="button"
        :disabled="isNextDisabled"
        @click="$emit('next-loan')"
        aria-label="Следующий кредит"
      >
        ›
      </button>
    </div>

    <div
      :ref="loansTrackRef"
      class="loans-grid"
      :class="{ 'loans-grid--carousel': isMobile }"
    >
      <LoanCard
        v-for="(loan, index) in loans"
        :key="loan.agreement_id"
        :loan="loan"
        :format-currency="formatCurrency"
        :format-percent="formatPercent"
        :format-term="formatTerm"
        :selected="loan.agreement_id === selectedLoanId"
        :allow-multi-select="allowMultiSelect"
        :multi-selected="multiSelectedIds.includes(loan.agreement_id)"
        @select="() => $emit('select-loan', loan.agreement_id, index)"
        @open-application="() => $emit('open-application', loan.agreement_id)"
        @toggle-multi="() => $emit('toggle-multi', loan.agreement_id)"
      />
    </div>

    <div
      v-if="isMobile && loans.length > 1"
      class="carousel-dots"
      role="tablist"
    >
      <button
        v-for="(loan, index) in loans"
        :key="`dot-${loan.agreement_id}`"
        type="button"
        class="carousel-dot"
        :class="{ active: index === currentSlide }"
        @click="$emit('go-to-loan', index)"
        :aria-label="`Показать кредит ${index + 1}`"
      ></button>
    </div>
  </div>
</template>

<script setup>
import LoanCard from './LoanCard.vue';

const props = defineProps({
  loans: {
    type: Array,
    default: () => [],
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
  allowMultiSelect: {
    type: Boolean,
    default: false,
  },
  multiSelectedIds: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits([
  'select-loan',
  'next-loan',
  'prev-loan',
  'go-to-loan',
  'open-application',
  'toggle-multi',
]);

void props;
void emit;
</script>

<style scoped>
.loans-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loans-section--carousel {
  gap: 16px;
}

.loans-carousel-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.carousel-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(92, 108, 255, 0.12);
  color: #3a4dff;
  font-size: 26px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 6px 12px rgba(74, 91, 255, 0.15);
}

.carousel-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.carousel-btn:not(:disabled):hover {
  transform: translateY(-2px);
}

.loans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}

.loans-grid--carousel {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  gap: 16px;
  padding-bottom: 4px;
  -webkit-overflow-scrolling: touch;
}

.loans-grid--carousel::-webkit-scrollbar {
  display: none;
}

.carousel-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.carousel-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(74, 91, 255, 0.25);
  border: none;
  padding: 0;
  cursor: pointer;
}

.carousel-dot.active {
  background: #4a5bff;
}

@media (min-width: 768px) {
  .loans-section {
    overflow: hidden;
  }

  .loans-section .loans-grid {
    max-height: clamp(320px, 60vh, 580px);
    overflow: hidden;
  }

  .loans-section .loans-grid {
    max-height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;
    scrollbar-gutter: stable both-edges;
  }

  .loans-section .loans-grid::-webkit-scrollbar {
    width: 6px;
  }

  .loans-section .loans-grid::-webkit-scrollbar-thumb {
    background: rgba(74, 91, 255, 0.35);
    border-radius: 999px;
  }

  .loans-section .loans-grid::-webkit-scrollbar-track {
    background: transparent;
  }
}

@media (max-width: 1024px) {
  .loans-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }
}

@media (max-width: 768px) {
  .loans-grid {
    display: flex;
    flex-direction: column;
  }

  .loans-grid--carousel {
    flex-direction: row;
  }
}
</style>
