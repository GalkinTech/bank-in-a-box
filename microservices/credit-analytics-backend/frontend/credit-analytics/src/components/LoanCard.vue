<template>
  <article
    class="loan-card"
    :class="{ selected, 'multi-selected': multiSelected }"
  >
    <div
      v-if="allowMultiSelect"
      class="loan-card__multi"
    >
      <label class="multi-checkbox">
        <input
          type="checkbox"
          :checked="multiSelected"
          @change.stop="toggleMultiSelection"
        />
        <span></span>
      </label>
    </div>
    <div class="loan-card__content" @click="handleSelect">
      <header class="loan-card__header">
        <div>
          <h3>
            {{ loan.product_display_type || 'Кредит' }}
            <template v-if="loan.product_display_name">
              · {{ loan.product_display_name }}
            </template>
          </h3>
          <p class="muted">Договор № {{ loan.agreement_id }}</p>
        </div>
        <div class="loan-card__status">
          {{ loan.status === 'active' ? 'Активен' : loan.status }}
        </div>
      </header>

      <div class="loan-card__body">
        <div class="loan-details">
          <div class="detail">
            <span class="label">Остаток долга</span>
            <span class="value">{{ formatCurrency(loan.outstandingBalance) }}</span>
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

        <div v-if="loan.offer" class="offer">
          <div class="offer-header">
            <span class="offer-badge">Новая ставка</span>
            <span class="offer-rate">{{ formatPercent(loan.offer.suggested_rate) }}</span>
          </div>
          <div class="offer-body">
            <div class="offer-item">
              <span class="label">Ежемесячный платёж</span>
              <span class="value">{{ formatCurrency(loan.offer.monthly_payment) }}</span>
            </div>
            <div class="offer-item">
              <span class="label">Экономия</span>
              <span class="value savings">{{ formatCurrency(loan.offerSavings) }}</span>
            </div>
          </div>
          <div class="offer-actions">
            <button class="btn btn-primary" type="button" @click.stop="handleOpenApplication">
              Подать заявку
            </button>
          </div>
        </div>
        <div v-else class="offer offer--empty">
          <p>Для данного кредита пока нет актуальных предложений. Попробуйте обновить данные позже.</p>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
const props = defineProps({
  loan: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
  allowMultiSelect: {
    type: Boolean,
    default: false,
  },
  multiSelected: {
    type: Boolean,
    default: false,
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

const emit = defineEmits(['select', 'open-application', 'toggle-multi']);

const handleSelect = () => {
  if (!props.loan?.agreement_id) {
    return;
  }
  emit('select', props.loan.agreement_id);
};

const handleOpenApplication = () => {
  if (!props.loan?.agreement_id) {
    return;
  }
  emit('open-application', props.loan.agreement_id);
};

const toggleMultiSelection = () => {
  if (!props.loan?.agreement_id) {
    return;
  }
  emit('toggle-multi', props.loan.agreement_id);
};
</script>

<style scoped>
.loan-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 18px;
  border: 1px solid rgba(89, 122, 200, 0.1);
  box-shadow: 0 8px 24px rgba(36, 66, 156, 0.07);
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
  scroll-snap-align: center;
  flex: 0 0 calc(100% - 32px);
  position: relative;
}

.loan-card__multi {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
}

.loan-card__content {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loan-card:hover,
.loan-card.selected {
  transform: translateY(-4px);
  box-shadow: 0 16px 38px rgba(35, 60, 140, 0.14);
  border-color: rgba(89, 122, 200, 0.35);
}

.loan-card.multi-selected {
  border-color: rgba(31, 187, 86, 0.6);
  box-shadow: 0 10px 24px rgba(31, 187, 86, 0.18);
}

.multi-checkbox {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
}

.multi-checkbox input {
  opacity: 0;
  position: absolute;
  inset: 0;
  margin: 0;
}

.multi-checkbox span {
  display: inline-block;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 2px solid rgba(74, 91, 255, 0.4);
  background: white;
  transition: all 0.2s ease;
}

.multi-checkbox input:checked + span {
  background: linear-gradient(135deg, #4a5bff, #24c0ff);
  border-color: transparent;
  box-shadow: 0 6px 12px rgba(74, 91, 255, 0.25);
}

.multi-checkbox span::after {
  content: '';
  position: absolute;
  opacity: 0;
  width: 6px;
  height: 12px;
  border-right: 2px solid white;
  border-bottom: 2px solid white;
  transform: rotate(45deg) translate(-1px, -2px);
  transition: opacity 0.2s ease;
}

.multi-checkbox input:checked + span::after {
  opacity: 1;
}

.loan-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.loan-card__header h3 {
  font-size: 1.1rem;
  margin-bottom: 4px;
}

.muted {
  color: #6b7a90;
  font-size: 0.9rem;
}

.loan-card__status {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(92, 108, 255, 0.12);
  color: #4a5bff;
  font-weight: 600;
  font-size: 0.85rem;
}

.loan-card__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

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

.offer {
  border-radius: 14px;
  border: 1px dashed rgba(92, 108, 255, 0.32);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: linear-gradient(135deg, rgba(92, 108, 255, 0.08), rgba(120, 198, 255, 0.08));
}

.offer--empty {
  border-style: solid;
  border-color: rgba(120, 130, 160, 0.2);
  background: rgba(242, 245, 252, 0.6);
  color: #526178;
  font-size: 0.9rem;
}

.offer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.offer-badge {
  padding: 4px 10px;
  background: rgba(74, 91, 255, 0.2);
  border-radius: 999px;
  color: #3a4dff;
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.offer-rate {
  font-size: 1.6rem;
  font-weight: 700;
  color: #273377;
}

.offer-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}

.offer-item .label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6f7c91;
  margin-bottom: 4px;
}

.offer-item .value {
  font-size: 1.1rem;
  font-weight: 600;
}

.offer-item .value.savings {
  color: #1fbb56;
}

.offer-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .loan-card {
    flex: 0 0 calc(100% - 40px);
    margin-right: 0;
  }
}
</style>
