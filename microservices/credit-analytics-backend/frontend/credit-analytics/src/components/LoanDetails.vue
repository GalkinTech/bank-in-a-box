<template>
  <div class="loan-details">
    <div class="detail">
      <span class="label">Остаток долга</span>
      <span class="value">{{ formatCurrency(loan.outstandingBalance) }}</span>
      <span v-if="loan.balanceError" class="hint error">{{ loan.balanceError }}</span>
    </div>
    <div class="detail">
      <span class="label">Текущая ставка</span>
      <span class="value">{{ formatPercent(loan.currentRate) }}</span>
    </div>
    <div class="detail">
      <span class="label">Платёж</span>
      <span class="value">{{ formatCurrency(loan.currentMonthlyPayment) }}</span>
    </div>
    <div class="detail">
      <span class="label">Срок остаток</span>
      <span class="value">{{ formatTerm(loan.remainingTermMonths) }}</span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  loan: {
    type: Object,
    required: true,
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

void props;
</script>

<style scoped>
.loan-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.detail .label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #8693a6;
  margin-bottom: 4px;
}

.detail .value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #162035;
}

.hint {
  display: block;
  margin-top: 4px;
  font-size: 0.75rem;
  color: #8291a8;
}

.hint.error {
  color: #d14343;
}
</style>
