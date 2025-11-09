<template>
  <div ref="rootEl" class="refinance-widget">
    <HeaderSection
      title="Рефинансирование кредитов"
      subtitle="Анализируйте активные кредиты и выбирайте лучшие предложения с одним кликом."
      :is-disabled="isLoading"
      :refresh-label="refreshButtonLabel"
      @refresh="handleRefreshRequest"
    />

    <section v-if="isAuthRequired" class="state state-auth">
      <h2>Требуется авторизация</h2>
      <p>Мы запросили токен доступа у основного приложения. Если доступ не появился, нажмите кнопку ниже.</p>
      <button class="btn btn-primary" type="button" @click="requestAuthTokenFromParent">Запросить токен ещё раз</button>
    </section>

    <section v-else class="content">
      <div v-if="!state.agreementAccepted" class="state state-consent">
        <h2>Необходим доступ к данным</h2>
        <p>
          Чтобы показать актуальные кредиты и предложения, подпишите соглашение на доступ к данным, нажав кнопку выше.
        </p>
        <button class="btn btn-primary" type="button" @click="handleRefreshRequest">
          Подписать согласие
        </button>
      </div>

      <div v-else>
        <div class="multi-actions-trigger" v-if="!state.multiSelectMode && externalLoans.length > 1 && !isMobile">
          <button class="btn btn-secondary" type="button" @click="enableMultiSelect">
            Выбрать несколько кредитов
          </button>
        </div>

        <div class="multi-actions" v-if="state.multiSelectMode && !isMobile">
          <div class="multi-summary">
            <strong>Выбрано кредитов: {{ state.multiSelectedLoanIds.length }}</strong>
            <span v-if="state.multiSelectedLoanIds.length">
              {{ formatCurrency(sumSelectedBalances) }} общий остаток
            </span>
          </div>
          <div class="multi-buttons">
            <button
              class="btn btn-secondary"
              type="button"
              @click="clearMultiSelection"
              :disabled="!state.multiSelectedLoanIds.length || state.isMultiSubmitting"
            >
              Снять выбор
            </button>
            <button
              class="btn btn-primary"
              type="button"
              @click="openBulkRefinance"
              :disabled="state.multiSelectedLoanIds.length < 2 || state.isMultiSubmitting"
            >
              Оформить пакетную заявку
            </button>
          </div>
          <div class="multi-status" v-if="state.isMultiSubmitting">
            <span class="spinner"></span>
            Формируем пакетную заявку...
          </div>
          <div
            class="multi-result"
            v-if="state.multiSubmissionResult"
            :class="state.multiSubmissionResult.status"
          >
            {{ state.multiSubmissionResult.message }}
          </div>
        </div>

        <div
          v-if="externalIssues"
          class="status-alert"
          role="alert"
        >
          <span class="status-alert__icon">⚠️</span>
          <div class="status-alert__content">
            <strong>Ограниченная доступность внешних банков.</strong>
            <p>{{ externalIssues }}</p>
          </div>
        </div>

        <InfoSection
          :cards="infoCards"
          :content-state="infoContentState"
        />

        <CreditsSection
          :state="creditsState"
          :loans="externalLoans"
          :error-messages="errorMessages"
          :loading-message="creditsLoadingMessage"
          :empty-title="creditsEmptyState.title"
          :empty-description="creditsEmptyState.description"
          :selected-loan-id="state.selectedLoanId"
          :is-mobile="isMobile"
          :current-slide="currentSlide"
          :is-prev-disabled="currentSlide === 0"
          :is-next-disabled="currentSlide >= externalLoans.length - 1"
          :loans-track-ref="setLoansTrack"
          :format-currency="formatCurrency"
          :format-percent="formatPercent"
          :format-term="formatTerm"
          :allow-multi-select="!isMobile"
          :multi-selected-ids="state.multiSelectedLoanIds"
          @retry="handleRefreshRequest"
          @select-loan="selectLoan"
          @next-loan="nextLoan"
          @prev-loan="prevLoan"
          @go-to-loan="goToLoan"
          @open-application="openApplicationModal"
          @toggle-multi="toggleMultiSelection"
        />
      </div>
    </section>

    <ApplicationModal
      :is-open="state.applicationModalOpen"
      :selected-loan="selectedLoan"
      :format-currency="formatCurrency"
      :format-percent="formatPercent"
      :desired-term-months="state.applicationForm.desiredTermMonths"
      :comment="state.applicationForm.comment"
      :submission-success="state.submissionSuccess"
      :submission-error="state.submissionError"
      :is-submitting="state.isSubmitting"
      @close="closeApplicationModal"
      @submit="submitApplication"
      @update:desired-term-months="state.applicationForm.desiredTermMonths = $event"
      @update:comment="state.applicationForm.comment = $event"
    />

    <DataAccessAgreementModal
      :is-open="state.agreementModalOpen"
      :is-processing="state.agreementProcessing"
      :error-message="state.agreementError"
      @confirm="confirmAgreementAndRefresh"
      @cancel="closeAgreementModal"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import HeaderSection from './components/HeaderSection.vue';
import InfoSection from './components/InfoSection.vue';
import CreditsSection from './components/CreditsSection.vue';
import ApplicationModal from './components/ApplicationModal.vue';
import DataAccessAgreementModal from './components/DataAccessAgreementModal.vue';

const state = reactive({
  loans: [],
  offers: [],
  isLoadingLoans: false,
  isLoadingOffers: false,
  isLoadingStatus: false,
  initialLoadCompleted: false,
  errorLoans: null,
  errorOffers: null,
  errorStatus: null,
  banksStatus: null,
  selectedLoanId: null,
  applicationModalOpen: false,
  applicationForm: {
    desiredTermMonths: '',
    comment: '',
  },
  isSubmitting: false,
  submissionError: null,
  submissionSuccess: false,
  parentModalActive: false,
  agreementModalOpen: false,
  agreementProcessing: false,
  agreementError: null,
  agreementAccepted: false,
  multiSelectMode: false,
  multiSelectedLoanIds: [],
  isMultiSubmitting: false,
  multiSubmissionResult: null,
});

const authToken = ref(null);
const tokenRequestTimestamp = ref(0);
const devAutoAuth = import.meta.env.DEV;
const devAuthToken = import.meta.env.VITE_DEV_AUTH_TOKEN;
const rootEl = ref(null);
const lastSentHeight = ref(0);
let resizeObserver = null;
const loansTrack = ref(null);
const setLoansTrack = (element) => {
  loansTrack.value = element;
};
const currentSlide = ref(0);
const isMobile = ref(false);
let trackScrollHandler = null;
const TOKEN_STORAGE_KEY = 'creditAnalyticsToken';
const AGREEMENT_ACCEPTED_KEY = 'creditAnalyticsAgreementAccepted';

const sendToParent = (type, payload) => {
  if (typeof window === 'undefined') {
    return;
  }
  if (!window.parent || window.parent === window) {
    return;
  }
  window.parent.postMessage(
    {
      type,
      payload,
    },
    '*'
  );
};

const buildParentModalPayload = (loan) => {
  if (!loan) {
    return null;
  }

  const offer = loan.offer || null;

  const formattedOffer = offer
    ? {
        suggestedRate: offer.suggested_rate ?? offer.rate ?? null,
        suggestedRateFormatted: formatPercent(offer.suggested_rate ?? offer.rate),
        monthlyPayment: offer.monthly_payment ?? offer.monthlyPayment ?? null,
        monthlyPaymentFormatted: formatCurrency(
          offer.monthly_payment ?? offer.monthlyPayment
        ),
        savings: loan.offerSavings ?? offer.savings ?? null,
        savingsFormatted: formatCurrency(loan.offerSavings ?? offer.savings),
        description: offer.description ?? null,
      }
    : null;

  return {
    loan: {
      agreementId: loan.agreement_id,
      productName: loan.product_name || loan.productName || null,
      originBank: loan.origin_bank || loan.source || null,
      bankName: loan.bank_name || loan.origin_bank_name || null,
      outstandingBalance: loan.outstandingBalance ?? null,
      outstandingBalanceFormatted: formatCurrency(loan.outstandingBalance),
      currentRate: loan.currentRate ?? null,
      currentRateFormatted: formatPercent(loan.currentRate),
      currentMonthlyPayment: loan.currentMonthlyPayment ?? null,
      currentMonthlyPaymentFormatted: formatCurrency(loan.currentMonthlyPayment),
      loanTermMonths: loan.remainingTermMonths ?? null,
      loanTermFormatted: formatTerm(loan.remainingTermMonths),
      offer: formattedOffer,
      offerSavings: loan.offerSavings ?? formattedOffer?.savings ?? null,
      offerSavingsFormatted:
        formatCurrency(loan.offerSavings ?? formattedOffer?.savings ?? null),
      accountNumber: loan.account_number || loan.accountNumber || null,
    },
    defaults: {
      desiredTermMonths: '',
      comment: '',
    },
  };
};

const ensureBearer = (token) => {
  if (!token) {
    return '';
  }
  return token.startsWith('Bearer') ? token : `Bearer ${token}`;
};

const normalizeToken = (value) => {
  if (!value || typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
};

const readTokenFromQuery = () => {
  try {
    const params = new URLSearchParams(window.location.search);
    const token =
      params.get('token') || params.get('authToken') || params.get('access_token');
    return normalizeToken(token);
  } catch (error) {
    console.warn('[credit-analytics] Failed to read token from query', error);
    return null;
  }
};

const readTokenFromGlobal = () => {
  const globalValue =
    typeof window !== 'undefined' ? window.__CREDIT_ANALYTICS_TOKEN__ : undefined;
  return normalizeToken(globalValue);
};

const readTokenFromStorage = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const stored = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
    return normalizeToken(stored);
  } catch (error) {
    console.warn('[credit-analytics] Failed to read token from storage', error);
    return null;
  }
};

const persistToken = (token) => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (error) {
    console.warn('[credit-analytics] Failed to persist token', error);
  }
};

const clearPersistedToken = () => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (error) {
    console.warn('[credit-analytics] Failed to clear persisted token', error);
  }
};

const readAgreementAcceptance = () => {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    const stored = window.sessionStorage.getItem(AGREEMENT_ACCEPTED_KEY);
    return stored === 'true';
  } catch (error) {
    console.warn('[credit-analytics] Failed to read agreement acceptance', error);
    return false;
  }
};

const persistAgreementAcceptance = (accepted) => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    if (accepted) {
      window.sessionStorage.setItem(AGREEMENT_ACCEPTED_KEY, 'true');
    } else {
      window.sessionStorage.removeItem(AGREEMENT_ACCEPTED_KEY);
    }
  } catch (error) {
    console.warn('[credit-analytics] Failed to persist agreement acceptance', error);
  }
};

const applyAuthToken = (token, { persist = true } = {}) => {
  const normalized = normalizeToken(token);
  if (!normalized) {
    return;
  }
  authToken.value = normalized;
  if (persist) {
    persistToken(normalized);
  }
};

const clampIndex = (index) => {
  const maxIndex = Math.max(externalLoans.value.length - 1, 0);
  return Math.min(Math.max(index, 0), maxIndex);
};

const scrollToSlide = (index) => {
  const track = loansTrack.value;
  if (!track) {
    return;
  }

  const targetIndex = clampIndex(index);
  const width = track.clientWidth;
  if (!width) {
    return;
  }

  const targetScroll = targetIndex * width;
  track.scrollTo({ left: targetScroll, behavior: 'smooth' });
  requestAnimationFrame(() => scheduleHeightUpdate());
};

const goToLoan = (index) => {
  const targetIndex = clampIndex(index);
  currentSlide.value = targetIndex;
  const loan = externalLoans.value[targetIndex];
  if (loan) {
    state.selectedLoanId = loan.agreement_id;
  }
  if (isMobile.value) {
    scrollToSlide(targetIndex);
  }
};

const nextLoan = () => {
  goToLoan(currentSlide.value + 1);
};

const prevLoan = () => {
  goToLoan(currentSlide.value - 1);
};

const selectLoan = (agreementId, index) => {
  state.selectedLoanId = agreementId;
  if (isMobile.value) {
    goToLoan(index);
  }
};

const handleTrackScroll = () => {
  if (!isMobile.value) {
    return;
  }
  const track = loansTrack.value;
  if (!track) {
    return;
  }
  const width = track.clientWidth || 1;
  const slide = clampIndex(Math.round(track.scrollLeft / width));
  if (slide !== currentSlide.value) {
    currentSlide.value = slide;
    const loan = externalLoans.value[slide];
    if (loan && loan.agreement_id !== state.selectedLoanId) {
      state.selectedLoanId = loan.agreement_id;
    }
  }
  scheduleHeightUpdate();
};

const detachTrackScroll = () => {
  if (trackScrollHandler && loansTrack.value) {
    loansTrack.value.removeEventListener('scroll', trackScrollHandler);
  }
  trackScrollHandler = null;
};

const attachTrackScroll = () => {
  detachTrackScroll();
  const track = loansTrack.value;
  if (!track) {
    return;
  }
  trackScrollHandler = () => handleTrackScroll();
  track.addEventListener('scroll', trackScrollHandler, { passive: true });
};

const handleViewportChange = () => {
  const mobile = window.matchMedia('(max-width: 767px)').matches;
  if (mobile !== isMobile.value) {
    isMobile.value = mobile;
  }
  if (isMobile.value) {
    nextTick(() => {
      attachTrackScroll();
      scrollToSlide(currentSlide.value);
    });
  } else {
    detachTrackScroll();
    currentSlide.value = clampIndex(currentSlide.value);
    if (loansTrack.value) {
      loansTrack.value.scrollTo({ left: 0 });
    }
  }
  scheduleHeightUpdate();
};

const describeError = (error, fallback) => {
  if (!error) {
    return fallback;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error.message) {
    return error.message;
  }
  if (error.status) {
    return `Ошибка ${error.status}`;
  }
  return fallback;
};

const sendWidgetHeight = (height) => {
  if (!window.parent || window.parent === window) {
    return;
  }

  const nextHeight = Math.max(Math.ceil(height || 0), 0);
  if (!nextHeight || Math.abs(nextHeight - lastSentHeight.value) < 1) {
    return;
  }

  lastSentHeight.value = nextHeight;
  window.parent.postMessage(
    {
      type: 'CREDIT_ANALYTICS_HEIGHT',
      payload: { height: nextHeight },
    },
    '*'
  );
};

const scheduleHeightUpdate = () => {
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(() => {
      const element = rootEl.value;
      const measured =
        element?.offsetHeight ||
        document.body.scrollHeight ||
        document.documentElement.scrollHeight;
      sendWidgetHeight(measured);
    });
  } else {
    const element = rootEl.value;
    const measured =
      element?.offsetHeight ||
      document.body.scrollHeight ||
      document.documentElement.scrollHeight;
    sendWidgetHeight(measured);
  }
};

const fetchJson = async (path, options = {}) => {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (authToken.value) {
    headers.set('Authorization', ensureBearer(authToken.value));
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const error = new Error(
      payload?.error || payload?.message || response.statusText || 'Неизвестная ошибка'
    );
    error.status = response.status;
    error.details = payload?.details ?? payload;
    throw error;
  }

  return payload;
};

const toNumber = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const calculateMonthlyPayment = (principal, annualRate, months) => {
  const amount = toNumber(principal);
  const rate = toNumber(annualRate);
  const term = toNumber(months);

  if (!amount || !term || term <= 0) {
    return null;
  }

  const monthlyRate = rate ? rate / 12 / 100 : 0;

  if (monthlyRate === 0) {
    return amount / term;
  }

  const denominator = 1 - Math.pow(1 + monthlyRate, -term);
  if (denominator === 0) {
    return null;
  }

  return (amount * monthlyRate) / denominator;
};

const extractBalance = (loan) => {
  const balances = Array.isArray(loan.balance) ? loan.balance : [];
  const amount = balances[0]?.amount?.amount ?? balances[0]?.amount ?? loan.balance?.amount;
  return toNumber(amount);
};

const loadLoans = async () => {
  state.isLoadingLoans = true;
  state.errorLoans = null;

  try {
    const response = await fetchJson('/api/loans/active');
    state.loans = Array.isArray(response?.data) ? response.data : [];
  } catch (error) {
    state.errorLoans = describeError(error, 'Не удалось получить список кредитов');
  } finally {
    state.isLoadingLoans = false;
  }
};

const loadOffers = async () => {
  state.isLoadingOffers = true;
  state.errorOffers = null;

  try {
    const response = await fetchJson('/api/refinance/suggestions');
    state.offers = Array.isArray(response?.data) ? response.data : [];
  } catch (error) {
    state.errorOffers = describeError(error, 'Не удалось получить предложения по рефинансированию');
  } finally {
    state.isLoadingOffers = false;
  }
};

const loadExternalStatus = async () => {
  state.isLoadingStatus = true;
  state.errorStatus = null;

  try {
    const response = await fetchJson('/api/refinance/status');
    state.banksStatus = response?.data ?? null;
  } catch (error) {
    state.errorStatus = describeError(error, 'Не удалось проверить статус внешних банков');
    state.banksStatus = null;
  } finally {
    state.isLoadingStatus = false;
  }
};

const infoContentState = computed(() => {
  if (isLoading.value) {
    return 'loading';
  }
  if (hasError.value || !externalLoans.value.length) {
    return 'hidden';
  }
  return 'ready';
});

const creditsState = computed(() => {
  if (isLoading.value) {
    return 'loading';
  }
  if (hasError.value) {
    return 'error';
  }
  if (!externalLoans.value.length) {
    return 'empty';
  }
  return 'ready';
});

const creditsLoadingMessage = computed(() => 'Загружаем данные кредитов и предложения...');

const creditsEmptyState = computed(() => ({
  title: 'Кредиты не найдены',
  description: 'Чтобы получить предложения по рефинансированию, оформите кредит или свяжитесь с банком.',
}));

const refreshButtonLabel = computed(() => (state.agreementAccepted ? 'Обновить данные' : 'Подписать согласие'));

const refreshAll = async () => {
  if (!authToken.value) {
    state.initialLoadCompleted = true;
    scheduleHeightUpdate();
    return;
  }

  state.initialLoadCompleted = false;
  await Promise.all([loadLoans(), loadOffers(), loadExternalStatus()]);
  state.initialLoadCompleted = true;
  scheduleHeightUpdate();
};

const openAgreementModal = () => {
  state.agreementError = null;
  state.agreementModalOpen = true;
  scheduleHeightUpdate();
};

const closeAgreementModal = () => {
  state.agreementModalOpen = false;
  state.agreementProcessing = false;
  scheduleHeightUpdate();
};

const confirmAgreementAndRefresh = async () => {
  if (state.agreementProcessing) {
    return;
  }

  state.agreementProcessing = true;
  state.agreementError = null;

  try {
    await new Promise((resolve) => setTimeout(resolve, 750));
    state.agreementAccepted = true;
    persistAgreementAcceptance(true);
    closeAgreementModal();
    await refreshAll();
  } catch (error) {
    console.error('[credit-analytics] Failed to process agreement confirmation', error);
    state.agreementError = 'Не удалось подтвердить согласие. Попробуйте ещё раз.';
  } finally {
    state.agreementProcessing = false;
    scheduleHeightUpdate();
  }
};

const resetAgreementAcceptance = ({ showModal = false } = {}) => {
  persistAgreementAcceptance(false);
  state.agreementAccepted = false;
  state.agreementProcessing = false;
  state.agreementError = null;
  state.loans = [];
  state.offers = [];
  state.selectedLoanId = null;
  state.multiSelectedLoanIds = [];
  state.multiSelectMode = false;

  if (showModal) {
    openAgreementModal();
  } else {
    state.agreementModalOpen = false;
    scheduleHeightUpdate();
  }
};

const ensureAgreementAccepted = () => {
  const storedAccepted = readAgreementAcceptance();

  if (!storedAccepted) {
    resetAgreementAcceptance({ showModal: true });
    return false;
  }

  if (!state.agreementAccepted) {
    state.agreementAccepted = true;
  }

  return true;
};

const handleRefreshRequest = () => {
  if (!ensureAgreementAccepted()) {
    return;
  }
  refreshAll();
};

if (typeof window !== 'undefined') {
  window.resetCreditAnalyticsAgreement = () => resetAgreementAcceptance({ showModal: true });
}

const offersByLoanId = computed(() => {
  return state.offers.reduce((acc, loan) => {
    const loanId = loan?.refinance_offer?.loan_id || loan?.loan_id || loan?.agreement_id;
    if (loanId) {
      acc[loanId] = loan.refinance_offer || loan.offer || loan;
    }
    return acc;
  }, {});
});

const loansWithOffers = computed(() => {
  return state.loans.map((loan) => {
    const offer = offersByLoanId.value[loan.agreement_id];
    const outstandingBalance = extractBalance(loan) ?? toNumber(loan.amount);
    const currentRate = toNumber(loan.interest_rate);
    const termMonths = toNumber(loan.term_months) ?? toNumber(offer?.assumptions?.term_months);
    const currentMonthlyPayment = calculateMonthlyPayment(outstandingBalance, currentRate, termMonths);

    return {
      ...loan,
      outstandingBalance,
      currentRate,
      remainingTermMonths: termMonths,
      currentMonthlyPayment,
      offer,
      offerSavings: toNumber(offer?.savings),
      balanceError: loan.balance_error?.message || loan.balance_error?.detail || null,
    };
  });
});

const isExternalLoan = (loan) => {
  if (!loan) {
    return false;
  }
  if (loan.source) {
    return loan.source === 'external';
  }
  if (loan.origin_bank) {
    return loan.origin_bank !== 'self';
  }
  return false;
};

const externalLoans = computed(() => {
  return loansWithOffers.value.filter((loan) => isExternalLoan(loan));
});

const selectedLoan = computed(() => {
  return externalLoans.value.find((loan) => loan.agreement_id === state.selectedLoanId) || null;
});

const summary = computed(() => {
  if (!externalLoans.value.length) {
    return {
      totalOutstanding: 0,
      averageRate: 0,
      totalPotentialSavings: 0,
      totalOffers: 0,
    };
  }

  const accumulator = externalLoans.value.reduce(
    (acc, loan) => {
      const outstanding = loan.outstandingBalance ?? 0;
      const rate = loan.currentRate ?? 0;
      const savings = loan.offerSavings ?? 0;

      acc.totalOutstanding += outstanding;
      acc.rateSum += rate;
      acc.count += loan.currentRate != null ? 1 : 0;
      acc.totalPotentialSavings += savings;
      acc.totalOffers += loan.offer ? 1 : 0;

      return acc;
    },
    {
      totalOutstanding: 0,
      rateSum: 0,
      count: 0,
      totalPotentialSavings: 0,
      totalOffers: 0,
    }
  );

  return {
    totalOutstanding: accumulator.totalOutstanding,
    averageRate: accumulator.count ? accumulator.rateSum / accumulator.count : 0,
    totalPotentialSavings: accumulator.totalPotentialSavings,
    totalOffers: accumulator.totalOffers,
  };
});

const errorMessages = computed(() => {
  return [state.errorLoans, state.errorOffers].filter(Boolean);
});

const banksHealth = computed(() => {
  const raw = state.banksStatus?.banks ?? [];
  return raw;
});

const externalBanksDown = computed(() => {
  return banksHealth.value.some((item) => item?.status !== 'up');
});

const externalIssues = computed(() => {
  if (state.errorStatus) {
    return state.errorStatus;
  }
  if (!banksHealth.value.length) {
    return null;
  }
  const problematic = banksHealth.value.filter((item) => item?.status !== 'up');
  if (!problematic.length) {
    return null;
  }
  const description = problematic
    .map((item) => `${item?.name || item?.code || 'банк'} (${item.healthUrl || item.baseUrl})`)
    .join(', ');
  return `Внешние банки недоступны: ${description}. Предложения по рефинансированию могут быть ограничены.`;
});

const isLoading = computed(() => {
  if (!state.initialLoadCompleted) {
    return true;
  }
  return state.isLoadingLoans || state.isLoadingOffers;
});

const hasError = computed(() => Boolean(state.errorLoans || state.errorOffers));

const isAuthRequired = computed(() => !devAutoAuth && !authToken.value);

const formatCurrency = (value) => {
  const number = toNumber(value);
  if (number == null) {
    return '—';
  }
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(number);
};

const formatPercent = (value) => {
  const number = toNumber(value);
  if (number == null) {
    return '—';
  }
  return `${number.toFixed(2)}%`;
};

const formatTerm = (months) => {
  const number = toNumber(months);
  if (!number) {
    return '—';
  }
  if (number < 12) {
    return `${number} мес.`;
  }
  const years = Math.floor(number / 12);
  const remainder = number % 12;
  if (!remainder) {
    return `${years} ${declineWord(years, ['год', 'года', 'лет'])}`;
  }
  return `${years} ${declineWord(years, ['год', 'года', 'лет'])} ${remainder} мес.`;
};

const declineWord = (value, words) => {
  const absValue = Math.abs(value) % 100;
  const lastDigit = absValue % 10;
  if (absValue > 10 && absValue < 20) {
    return words[2];
  }
  if (lastDigit > 1 && lastDigit < 5) {
    return words[1];
  }
  if (lastDigit === 1) {
    return words[0];
  }
  return words[2];
};

const infoCards = computed(() => [
  {
    label: 'Текущая задолженность',
    value: formatCurrency(summary.value.totalOutstanding),
    caption: 'По активным кредитам',
    variant: 'primary',
  },
  {
    label: 'Средняя ставка',
    value: formatPercent(summary.value.averageRate),
    caption: 'Текущие условия по кредитам',
  },
  {
    label: 'Потенциальная экономия',
    value: formatCurrency(summary.value.totalPotentialSavings),
    caption: 'При переходе на предложение',
    valueClass: 'savings',
  },
  {
    label: 'Предложений доступно',
    value: summary.value.totalOffers,
    caption: 'Для активных договоров',
  },
]);

const openApplicationModal = (agreementId) => {
  state.selectedLoanId = agreementId;
  state.applicationForm.desiredTermMonths = '';
  state.applicationForm.comment = '';
  state.submissionError = null;
  state.submissionSuccess = false;

  if (typeof window !== 'undefined' && window.parent && window.parent !== window) {
    nextTick(() => {
      const loan = selectedLoan.value;
      const payload = buildParentModalPayload(loan);

      if (payload) {
        sendToParent('OPEN_REFINANCE_APPLICATION_MODAL', payload);
        state.parentModalActive = true;
      } else {
        state.applicationModalOpen = true;
      }
    });
  } else {
    state.applicationModalOpen = true;
  }
};

const closeApplicationModal = () => {
  closeApplicationModalInternal();
};

const closeApplicationModalInternal = (options = {}) => {
  const { notifyParent = true } = options;

  if (state.parentModalActive && notifyParent) {
    sendToParent('CLOSE_REFINANCE_APPLICATION_MODAL', {
      reason: options.reason || 'iframe-close',
    });
  }

  state.applicationModalOpen = false;
  state.submissionError = null;
  state.submissionSuccess = false;
  state.parentModalActive = false;
};

const notifyParent = (payload) => {
  sendToParent('REFINANCE_APPLICATION_SUBMITTED', payload);
};

const submitApplication = async (options = {}) => {
  const triggeredByParent = options.trigger === 'parent';
  if (!selectedLoan.value) {
    if (triggeredByParent) {
      sendToParent('REFINANCE_APPLICATION_RESULT', {
        status: 'error',
        message: 'Кредит не выбран',
      });
    }
    return;
  }

  state.isSubmitting = true;
  state.submissionError = null;

  if (triggeredByParent) {
    sendToParent('REFINANCE_APPLICATION_RESULT', {
      status: 'submitting',
    });
  }

  const payload = {
    agreement_id: selectedLoan.value.agreement_id,
    desired_term_months: state.applicationForm.desiredTermMonths
      ? Number(state.applicationForm.desiredTermMonths)
      : undefined,
    comment: state.applicationForm.comment || undefined,
  };

  let submissionOutcome = {
    status: 'success',
    responseStatus: 'submitted',
    errorMessage: null,
  };

  try {
    const endpoint = '/api/refinance/applications?force_real=true';
    const response = await fetchJson(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        force_real: true,
      }),
      headers: {
        'X-Force-Real': 'true',
      },
    });

    state.submissionSuccess = true;
    submissionOutcome.responseStatus = response?.status || 'submitted';
    notifyParent({
      agreementId: selectedLoan.value.agreement_id,
      status: submissionOutcome.responseStatus,
      payload,
    });
  } catch (error) {
    if (error.status === 404) {
      console.warn('Endpoint /api/refinance/applications отсутствует. Используем мок-ответ.');
      state.submissionSuccess = true;
      submissionOutcome.responseStatus = 'mock-submitted';
      notifyParent({
        agreementId: selectedLoan.value.agreement_id,
        status: 'mock-submitted',
        payload,
      });
    } else {
      submissionOutcome.status = 'error';
      state.submissionError = describeError(
        error,
        'Не удалось отправить заявку. Попробуйте позже.'
      );
      submissionOutcome.errorMessage = state.submissionError;
    }
  } finally {
    state.isSubmitting = false;
    scheduleHeightUpdate();
  }

  if (triggeredByParent) {
    if (submissionOutcome.status === 'success') {
      sendToParent('REFINANCE_APPLICATION_RESULT', {
        status: 'success',
        agreementId: selectedLoan.value?.agreement_id,
        responseStatus: submissionOutcome.responseStatus,
      });
    } else {
      sendToParent('REFINANCE_APPLICATION_RESULT', {
        status: 'error',
        message: submissionOutcome.errorMessage,
      });
    }
  }
};

const requestAuthTokenFromParent = () => {
  const now = Date.now();
  if (now - tokenRequestTimestamp.value < 2000) {
    return;
  }
  tokenRequestTimestamp.value = now;

  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ type: 'CREDIT_ANALYTICS_TOKEN_REQUEST' }, '*');
  }
};

const handleMessage = (event) => {
  const { data } = event;
  if (!data || typeof data !== 'object') {
    return;
  }

  if (data.type === 'AUTH_TOKEN_RESPONSE' && data.payload?.token) {
    applyAuthToken(data.payload.token);
  }

  if (data.type === 'REFRESH_REFINANCE_WIDGET') {
    refreshAll();
  }

  if (data.type === 'REFINANCE_APPLICATION_MODAL_SUBMIT') {
    state.parentModalActive = true;
    state.applicationForm.desiredTermMonths =
      data.payload?.desired_term_months ?? '';
    state.applicationForm.comment = data.payload?.comment ?? '';
    submitApplication({ trigger: 'parent' });
  }

  if (data.type === 'REFINANCE_APPLICATION_MODAL_CLOSED') {
    closeApplicationModalInternal({ notifyParent: false, reason: 'parent-close' });
  }
};

onMounted(() => {
  window.addEventListener('message', handleMessage);

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      scheduleHeightUpdate();
    });
    const element = rootEl.value;
    if (element) {
      resizeObserver.observe(element);
    }
  }

  handleViewportChange();
  window.addEventListener('resize', handleViewportChange);
  window.addEventListener('orientationchange', handleViewportChange);
  scheduleHeightUpdate();

  const queryToken = readTokenFromQuery();
  const globalToken = queryToken ? null : readTokenFromGlobal();
  const storedToken = queryToken || globalToken ? null : readTokenFromStorage();
  const devToken = normalizeToken(devAuthToken);

  if (queryToken) {
    applyAuthToken(queryToken);
  } else if (globalToken) {
    applyAuthToken(globalToken);
  } else if (storedToken) {
    applyAuthToken(storedToken, { persist: false });
  } else if (devToken) {
    applyAuthToken(devToken, { persist: Boolean(devAutoAuth) });
  } else if (devAutoAuth) {
    applyAuthToken('dev-mock-token');
  } else {
    requestAuthTokenFromParent();
  }

  state.agreementAccepted = readAgreementAcceptance();
});

onUnmounted(() => {
  window.removeEventListener('message', handleMessage);
  window.removeEventListener('resize', handleViewportChange);
  window.removeEventListener('orientationchange', handleViewportChange);
  resizeObserver?.disconnect();
  detachTrackScroll();
});

watch(externalLoans, (items) => {
  if (!items.length) {
    state.selectedLoanId = null;
    currentSlide.value = 0;
    scheduleHeightUpdate();
    return;
  }

  const selectedIndex = items.findIndex((loan) => loan.agreement_id === state.selectedLoanId);
  if (selectedIndex === -1) {
    state.selectedLoanId = items[0].agreement_id;
    currentSlide.value = 0;
  } else {
    currentSlide.value = clampIndex(selectedIndex);
  }

  if (isMobile.value) {
    nextTick(() => {
      attachTrackScroll();
      scrollToSlide(currentSlide.value);
    });
  }

  scheduleHeightUpdate();
});

watch(authToken, (token, previous) => {
  if (token && token !== previous) {
    refreshAll();
    scheduleHeightUpdate();
  }
});

watch(
  () => state.selectedLoanId,
  (agreementId) => {
    if (!agreementId) {
      currentSlide.value = 0;
      return;
    }

    const index = externalLoans.value.findIndex(
      (loan) => loan.agreement_id === agreementId
    );

    if (index >= 0 && index !== currentSlide.value) {
      currentSlide.value = clampIndex(index);
      if (isMobile.value) {
        nextTick(() => scrollToSlide(currentSlide.value));
      }
    }
  }
);

watch(currentSlide, () => {
  if (isMobile.value) {
    nextTick(() => scheduleHeightUpdate());
  } else {
    scheduleHeightUpdate();
  }
});

watch(isMobile, (mobile) => {
  if (mobile) {
    nextTick(() => {
      attachTrackScroll();
      scrollToSlide(currentSlide.value);
      scheduleHeightUpdate();
    });
  } else {
    detachTrackScroll();
    if (loansTrack.value) {
      loansTrack.value.scrollTo({ left: 0 });
    }
    scheduleHeightUpdate();
  }
});

watch(
  () => loansTrack.value,
  (track) => {
    if (track && isMobile.value) {
      attachTrackScroll();
      nextTick(() => scrollToSlide(currentSlide.value));
    } else if (!track) {
      detachTrackScroll();
    }
  }
);

watch(isLoading, () => {
  scheduleHeightUpdate();
});

watch(
  () => state.applicationModalOpen,
  () => {
    scheduleHeightUpdate();
  }
);

watch(
  () => state.submissionSuccess,
  () => {
    scheduleHeightUpdate();
  }
);

watch(
  () => state.banksStatus,
  () => {
    scheduleHeightUpdate();
  }
);

/* конец setup */
</script>

<style>
.refinance-widget {
  min-height: 100%;
  padding: 24px clamp(16px, 5vw, 40px);
  /* background: linear-gradient(160deg, #ffffff 0%, #ffffff 60%, #f0f4ff 100%); */
  color: #1f2d3d;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.widget-header .header-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.widget-header h1 {
  font-size: clamp(2rem, 3vw, 2.5rem);
  font-weight: 700;
  margin: 0;
}

.widget-header p {
  color: #51606f;
  max-width: 560px;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}


.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

@media (min-width: 768px) {
  .credits-section {
    overflow: hidden;
  }

  .credits-section .loans-section {
    max-height: clamp(320px, 60vh, 580px);
    overflow: hidden;
  }

  .credits-section .loans-grid {
    max-height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;
    scrollbar-gutter: stable both-edges;
  }

  .credits-section .loans-grid::-webkit-scrollbar {
    width: 6px;
  }

  .credits-section .loans-grid::-webkit-scrollbar-thumb {
    background: rgba(74, 91, 255, 0.35);
    border-radius: 999px;
  }

  .credits-section .loans-grid::-webkit-scrollbar-track {
    background: transparent;
  }
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: clamp(32px, 5vw, 56px);
}

.summary-card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(41, 72, 152, 0.07);
  border: 1px solid rgba(79, 114, 205, 0.08);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-card.primary {
  background: linear-gradient(135deg, #5c6cff, #8897ff);
  color: #ffffff;
  border: none;
}

.summary-card .summary-label {
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: inherit;
  opacity: 0.7;
}

.summary-card .summary-value {
  font-size: 1.5rem;
  font-weight: 600;
}

.summary-card .summary-caption {
  font-size: 0.85rem;
  color: inherit;
  opacity: 0.8;
}

.summary-card .summary-value.savings {
  color: #1fbb56;
}

@media (max-width: 1024px) {
  .summary-grid {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    margin-bottom: clamp(16px, 2.5vw, 28px);
  }

  .refinance-widget {
    padding: 18px 12px 32px;
  }

  .content {
    gap: 16px;
  }

  .state {
    padding: 24px 18px;
  }

  .summary-card {
    padding: 14px 16px;
  }

  .summary-card .summary-label {
    font-size: clamp(0.68rem, 2.6vw, 0.82rem);
    letter-spacing: 0.05em;
    line-height: 1.2;
  }
}

.btn {
  border: none;
  border-radius: 14px;
  padding: 9px 16px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #4a5bff, #7a8dff);
  color: #ffffff;
  box-shadow: 0 10px 20px rgba(74, 91, 255, 0.2);
}

.btn-secondary {
  background: rgba(95, 108, 255, 0.12);
  color: #3a4dff;
  box-shadow: 0 6px 12px rgba(74, 91, 255, 0.15);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn:not(:disabled):hover {
  transform: translateY(-2px);
}

.status-alert {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 159, 67, 0.35);
  background: rgba(255, 188, 87, 0.12);
  color: #7a3300;
}

.status-alert__icon {
  font-size: 24px;
  line-height: 1;
}

.status-alert__content strong {
  display: block;
  margin-bottom: 4px;
}

.status-alert__content p {
  margin: 0;
  color: inherit;
  font-size: 14px;
}

.state {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  padding: 32px 28px;
  text-align: center;
  box-shadow: 0 12px 28px rgba(40, 60, 120, 0.1);
  border: 1px solid rgba(85, 110, 190, 0.1);
}

.state h2 {
  margin-bottom: 12px;
}

.state p {
  margin-bottom: 20px;
  color: #5d6c82;
}

.state-error ul {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  color: #d14343;
}

.state-empty .empty-icon {
  font-size: 3rem;
  margin-bottom: 12px;
}

.state-loading {
  display: grid;
  gap: 14px;
  justify-items: center;
}

.loader {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 4px solid rgba(74, 91, 255, 0.2);
  border-top-color: #4a5bff;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 14, 40, 0.55);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 999;
}

.modal {
  width: min(520px, 100%);
  background: #ffffff;
  border-radius: 22px;
  padding: 28px;
  box-shadow: 0 24px 60px rgba(22, 36, 94, 0.25);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.modal-header h2 {
  font-size: 1.4rem;
  margin-bottom: 6px;
}

.modal-close {
  background: transparent;
  border: none;
  font-size: 1.8rem;
  cursor: pointer;
  color: #69758a;
}

.modal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.modal-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.modal-list .label {
  font-size: 0.8rem;
  color: #6f7c91;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.modal-list .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #18223a;
}

.modal-list .value.savings {
  color: #1fbb56;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group input,
.form-group textarea {
  border-radius: 12px;
  border: 1px solid rgba(105, 119, 156, 0.3);
  padding: 12px 14px;
  font-size: 0.95rem;
  font-family: inherit;
  transition: border 0.2s ease, box-shadow 0.2s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #4a5bff;
  box-shadow: 0 0 0 3px rgba(74, 91, 255, 0.15);
}

.hint {
  font-size: 0.8rem;
  color: #7a889f;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.6);
  border-top-color: #ffffff;
  animation: spin 0.8s linear infinite;
}

.alert {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 0.95rem;
}

.alert-error {
  background: rgba(224, 67, 67, 0.1);
  color: #b92f2f;
  border: 1px solid rgba(224, 67, 67, 0.2);
}

.modal-success {
  display: grid;
  gap: 16px;
  justify-items: center;
  text-align: center;
}

.modal-success .success-icon {
  font-size: 3rem;
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

@media (max-width: 1024px) {
  .loans-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .modal-grid {
    grid-template-columns: 1fr;
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

  .loan-card {
    flex: 0 0 calc(100% - 40px);
    margin-right: 0;
  }

  .widget-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-card .summary-value {
    font-size: 1.5rem;
  }

  .summary-grid {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }

  .refinance-widget {
    padding: 18px 12px 32px;
  }
}
</style>
