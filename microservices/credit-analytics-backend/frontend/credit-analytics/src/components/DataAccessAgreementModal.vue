<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="handleBackdropClick">
    <div class="modal modal--agreement">
      <header class="modal-header">
        <div>
          <h2>Подписание доступа к данным</h2>
          <p class="modal-subtitle">
            Перед обновлением сведений требуется подтвердить доступ к данным, полученным из партнёрских банков.
          </p>
        </div>
        <button class="modal-close" type="button" aria-label="Закрыть" @click="emitCancel">×</button>
      </header>

      <section class="agreement-body">
        <article class="agreement-section">
          <h3>Краткие условия</h3>
          <ul class="agreement-list">
            <li>Банки-партнёры предоставляют актуальные данные о кредитах.</li>
            <li>Данные используются только для расчёта предложений по рефинансированию.</li>
            <li>Вы можете отозвать согласие на доступ к данным в любой момент.</li>
          </ul>
        </article>
        <article class="agreement-section">
          <h3>Договор доступа к данным</h3>
          <p>
            Нажимая «Подписать и обновить», вы подтверждаете, что ознакомились с условиями доступа к данным и разрешаете
            системе инициировать запрос к внешним банковским API.
          </p>
        </article>
        <label class="agreement-checkbox">
          <input type="checkbox" v-model="localAccepted" :disabled="isProcessing" />
          <span>Я подтверждаю условия доступа к данным и готов продолжить обновление</span>
        </label>
        <div v-if="errorMessage" class="alert alert-error">
          {{ errorMessage }}
        </div>
      </section>

      <footer class="modal-actions">
        <button class="btn btn-secondary" type="button" @click="emitCancel" :disabled="isProcessing">
          Отмена
        </button>
        <button
          class="btn btn-primary"
          type="button"
          @click="handleConfirm"
          :disabled="!localAccepted || isProcessing"
        >
          <span v-if="isProcessing" class="spinner"></span>
          Подписать и обновить
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  isProcessing: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: [String, null],
    default: null,
  },
});

const emit = defineEmits(['confirm', 'cancel']);

const localAccepted = ref(false);

watch(
  () => props.isOpen,
  (isOpen) => {
    if (isOpen) {
      localAccepted.value = false;
    }
  }
);

const handleConfirm = () => {
  if (!localAccepted.value || props.isProcessing) {
    return;
  }
  emit('confirm');
};

const emitCancel = () => {
  if (props.isProcessing) {
    return;
  }
  emit('cancel');
};

const handleBackdropClick = () => {
  emitCancel();
};
</script>

<style scoped>
.modal--agreement {
  width: min(640px, 100%);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.modal-subtitle {
  margin-top: 6px;
  color: #5d6c82;
  font-size: 0.95rem;
}

.agreement-body {
  display: grid;
  gap: 18px;
}

.agreement-section {
  display: grid;
  gap: 10px;
}

.agreement-section h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}

.agreement-section p {
  margin: 0;
  color: #4a556a;
  line-height: 1.5;
}

.agreement-list {
  margin: 0;
  padding-left: 20px;
  display: grid;
  gap: 6px;
  color: #4a556a;
}

.agreement-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 0.95rem;
  color: #273247;
}

.agreement-checkbox input {
  margin-top: 4px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
