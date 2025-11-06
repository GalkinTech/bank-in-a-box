<template>
  <section class="content">
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

    <div
      v-else
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
        <article
          v-for="(loan, index) in loans"
          :key="loan.agreement_id"
          class="loan-card"
          :class="{ selected: loan.agreement_id === selectedLoanId }"
          @click="$emit('select-loan', loan.agreement_id, index)"
        >
          <header class="loan-card__header">
            <div>
              <h3>{{ loan.product_name || 'Кредитный договор' }}</h3>
              <p class="muted">Договор № {{ loan.agreement_id }}</p>
            </div>
            <div class="loan-card__status">{{ loan.status === 'active' ? 'Активен' : loan.status }}</div>
          </header>

          <div class="loan-card__body">
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
                <button
                  class="btn btn-primary"
                  type="button"
                  @click.stop="$emit('open-application', loan.agreement_id)"
                >
                  Подать заявку
                </button>
              </div>
            </div>
            <div v-else class="offer offer--empty">
              <p>Для данного кредита пока нет актуальных предложений. Попробуйте обновить данные позже.</p>
            </div>
          </div>
        </article>
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
  </section>
</template>

<script setup>
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
