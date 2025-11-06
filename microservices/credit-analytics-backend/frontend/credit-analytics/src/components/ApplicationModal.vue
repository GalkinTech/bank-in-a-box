<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="emitClose">
    <div class="modal">
      <header class="modal-header">
        <div>
          <h2>Заявка на рефинансирование</h2>
          <p v-if="selectedLoan" class="muted">Договор № {{ selectedLoan.agreement_id }}</p>
        </div>
        <button class="modal-close" type="button" aria-label="Закрыть" @click="emitClose">×</button>
      </header>

      <div v-if="submissionSuccess" class="modal-success">
        <div class="success-icon">✅</div>
        <h3>Заявка отправлена</h3>
        <p>Мы уведомим вас, как только банк обработает запрос.</p>
        <button class="btn btn-secondary" type="button" @click="emitClose">Готово</button>
      </div>

      <form v-else class="modal-form" @submit.prevent="emitSubmit">
        <div class="modal-grid" v-if="selectedLoan">
          <div>
            <h4>Текущие условия</h4>
            <ul class="modal-list">
              <li>
                <span class="label">Ставка</span>
                <span class="value">{{ formatPercent(selectedLoan.currentRate) }}</span>
              </li>
              <li>
                <span class="label">Ежемесячный платёж</span>
                <span class="value">{{ formatCurrency(selectedLoan.currentMonthlyPayment) }}</span>
              </li>
            </ul>
          </div>
          <div v-if="selectedLoan.offer">
            <h4>Новое предложение</h4>
            <ul class="modal-list">
              <li>
                <span class="label">Ставка</span>
                <span class="value">{{ formatPercent(selectedLoan.offer.suggested_rate) }}</span>
              </li>
              <li>
                <span class="label">Платёж</span>
                <span class="value">{{ formatCurrency(selectedLoan.offer.monthly_payment) }}</span>
              </li>
              <li>
                <span class="label">Экономия</span>
                <span class="value savings">{{ formatCurrency(selectedLoan.offerSavings) }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="form-group">
          <label for="desired-term" class="label">Желаемый срок (мес.)</label>
          <input
            id="desired-term"
            v-model="desiredTermModel"
            type="number"
            min="6"
            step="1"
            placeholder="Например, 24"
          />
          <span class="hint">Необязательно: если нужно изменить срок кредита.</span>
        </div>

        <div class="form-group">
          <label for="comment" class="label">Комментарий</label>
          <textarea
            id="comment"
            v-model="commentModel"
            rows="3"
            placeholder="Уточните пожелания или дополнительную информацию"
          ></textarea>
        </div>

        <div v-if="submissionError" class="alert alert-error">
          {{ submissionError }}
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" @click="emitClose">Отмена</button>
          <button class="btn btn-primary" type="submit" :disabled="isSubmitting">
            <span v-if="isSubmitting" class="spinner"></span>
            Отправить заявку
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  selectedLoan: {
    type: Object,
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
  desiredTermMonths: {
    type: [String, Number],
    default: '',
  },
  comment: {
    type: String,
    default: '',
  },
  submissionSuccess: {
    type: Boolean,
    default: false,
  },
  submissionError: {
    type: [String, null],
    default: null,
  },
  isSubmitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['close', 'submit', 'update:desiredTermMonths', 'update:comment']);

const desiredTermModel = computed({
  get: () => props.desiredTermMonths,
  set: (value) => emit('update:desiredTermMonths', value),
});

const commentModel = computed({
  get: () => props.comment,
  set: (value) => emit('update:comment', value),
});

const emitClose = () => emit('close');
const emitSubmit = () => emit('submit');
</script>
