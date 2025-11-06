<template>
  <div ref="rootEl" class="refinance-widget">
    <HeaderSection
      title="Рефинансирование кредитов"
      subtitle="Анализируйте активные кредиты и выбирайте лучшие предложения с одним кликом."
      :is-disabled="isLoading"
      @refresh="refreshAll"
    />

    <section v-if="isAuthRequired" class="state state-auth">
      <h2>Требуется авторизация</h2>
      <p>Мы запросили токен доступа у основного приложения. Если доступ не появился, нажмите кнопку ниже.</p>
      <button class="btn btn-primary" type="button" @click="requestAuthTokenFromParent">Запросить токен ещё раз</button>
    </section>

    <section v-else class="content">
      <InfoSection
        :cards="infoCards"
        :content-state="infoContentState"
      />

      <CreditsSection
        :state="creditsState"
        :loans="loansWithOffers"
        :error-messages="errorMessages"
        :loading-message="creditsLoadingMessage"
        :empty-title="creditsEmptyState.title"
        :empty-description="creditsEmptyState.description"
        :selected-loan-id="state.selectedLoanId"
        :is-mobile="isMobile"
        :current-slide="currentSlide"
        :is-prev-disabled="currentSlide === 0"
        :is-next-disabled="currentSlide >= loansWithOffers.length - 1"
        :loans-track-ref="setLoansTrack"
        :format-currency="formatCurrency"
        :format-percent="formatPercent"
        :format-term="formatTerm"
        @retry="refreshAll"
        @select-loan="selectLoan"
        @next-loan="nextLoan"
        @prev-loan="prevLoan"
        @go-to-loan="goToLoan"
        @open-application="openApplicationModal"
      />
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
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import HeaderSection from './components/HeaderSection.vue';
import InfoSection from './components/InfoSection.vue';
import CreditsSection from './components/CreditsSection.vue';
import ApplicationModal from './components/ApplicationModal.vue';

const state = reactive({
  loans: [],
  offers: [],
  isLoadingLoans: false,
  isLoadingOffers: false,
  initialLoadCompleted: false,
  errorLoans: null,
  errorOffers: null,
  selectedLoanId: null,
  applicationModalOpen: false,
  applicationForm: {
    desiredTermMonths: '',
    comment: '',
  },
  isSubmitting: false,
  submissionError: null,
  submissionSuccess: false,
});

const authToken = ref(null);
const tokenRequestTimestamp = ref(0);
const devAutoAuth = import.meta.env.DEV;
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

const ensureBearer = (token) => {
  if (!token) {
    return '';
  }
  return token.startsWith('Bearer') ? token : `Bearer ${token}`;
};

const clampIndex = (index) => {
  const maxIndex = Math.max(loansWithOffers.value.length - 1, 0);
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
  const loan = loansWithOffers.value[targetIndex];
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
    const loan = loansWithOffers.value[slide];
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

const infoContentState = computed(() => {
  if (isLoading.value) {
    return 'loading';
  }
  if (hasError.value || !loansWithOffers.value.length) {
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
  if (!loansWithOffers.value.length) {
    return 'empty';
  }
  return 'ready';
});

const creditsLoadingMessage = computed(() => 'Загружаем данные кредитов и предложения...');

const creditsEmptyState = computed(() => ({
  title: 'Кредиты не найдены',
  description: 'Чтобы получить предложения по рефинансированию, оформите кредит или свяжитесь с банком.',
}));

const refreshAll = async () => {
  if (!authToken.value) {
    state.initialLoadCompleted = true;
    scheduleHeightUpdate();
    return;
  }

  state.initialLoadCompleted = false;
  await Promise.all([loadLoans(), loadOffers()]);
  state.initialLoadCompleted = true;
  scheduleHeightUpdate();
};

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

const selectedLoan = computed(() => {
  return loansWithOffers.value.find((loan) => loan.agreement_id === state.selectedLoanId) || null;
});

const summary = computed(() => {
  if (!loansWithOffers.value.length) {
    return {
      totalOutstanding: 0,
      averageRate: 0,
      totalPotentialSavings: 0,
      totalOffers: 0,
    };
  }

  const accumulator = loansWithOffers.value.reduce(
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
  state.applicationModalOpen = true;
  state.applicationForm.desiredTermMonths = '';
  state.applicationForm.comment = '';
  state.submissionError = null;
  state.submissionSuccess = false;
};

const closeApplicationModal = () => {
  state.applicationModalOpen = false;
  state.submissionError = null;
  state.submissionSuccess = false;
};

const notifyParent = (payload) => {
  if (window.parent && window.parent !== window) {
    window.parent.postMessage(
      {
        type: 'REFINANCE_APPLICATION_SUBMITTED',
        payload,
      },
      '*'
    );
  }
};

const submitApplication = async () => {
  if (!selectedLoan.value) {
    return;
  }

  state.isSubmitting = true;
  state.submissionError = null;

  const payload = {
    agreement_id: selectedLoan.value.agreement_id,
    desired_term_months: state.applicationForm.desiredTermMonths
      ? Number(state.applicationForm.desiredTermMonths)
      : undefined,
    comment: state.applicationForm.comment || undefined,
  };

  try {
    const response = await fetchJson('/api/refinance/applications', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    state.submissionSuccess = true;
    notifyParent({
      agreementId: selectedLoan.value.agreement_id,
      status: response?.status || 'submitted',
      payload,
    });
  } catch (error) {
    if (error.status === 404) {
      console.warn('Endpoint /api/refinance/applications отсутствует. Используем мок-ответ.');
      state.submissionSuccess = true;
      notifyParent({
        agreementId: selectedLoan.value.agreement_id,
        status: 'mock-submitted',
        payload,
      });
    } else {
      state.submissionError = describeError(error, 'Не удалось отправить заявку. Попробуйте позже.');
    }
  } finally {
    state.isSubmitting = false;
    scheduleHeightUpdate();
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
    const token = data.payload.token;
    authToken.value = token;
    sessionStorage.setItem('creditAnalyticsToken', token);
  }

  if (data.type === 'REFRESH_REFINANCE_WIDGET') {
    refreshAll();
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

  const storedToken = sessionStorage.getItem('creditAnalyticsToken');
  if (storedToken) {
    authToken.value = storedToken;
  } else if (devAutoAuth) {
    const mockToken = 'dev-mock-token';
    authToken.value = mockToken;
    sessionStorage.setItem('creditAnalyticsToken', mockToken);
  } else {
    requestAuthTokenFromParent();
  }
});

onUnmounted(() => {
  window.removeEventListener('message', handleMessage);
  window.removeEventListener('resize', handleViewportChange);
  window.removeEventListener('orientationchange', handleViewportChange);
  resizeObserver?.disconnect();
  detachTrackScroll();
});

watch(loansWithOffers, (items) => {
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

    const index = loansWithOffers.value.findIndex(
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
</script>

<style>
.refinance-widget {
  min-height: 100%;
  padding: 32px clamp(20px, 6vw, 48px);
  /* background: linear-gradient(160deg, #f5f7fa 0%, #ffffff 60%, #f0f4ff 100%); */
  color: #1f2d3d;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.widget-header h1 {
  font-size: clamp(2rem, 3vw, 2.5rem);
  font-weight: 700;
  margin-bottom: 8px;
}

.widget-header p {
  color: #51606f;
  max-width: 560px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.summary-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 20px 24px;
  box-shadow: 0 12px 32px rgba(41, 72, 152, 0.08);
  border: 1px solid rgba(79, 114, 205, 0.1);
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  font-size: 1.8rem;
  font-weight: 700;
}

.summary-card .summary-caption {
  font-size: 0.85rem;
  color: inherit;
  opacity: 0.8;
}

.summary-card .summary-value.savings {
  color: #1fbb56;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.loans-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
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

.loan-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  border: 1px solid rgba(89, 122, 200, 0.12);
  box-shadow: 0 10px 28px rgba(36, 66, 156, 0.08);
  display: flex;
  flex-direction: column;
  padding: 22px;
  gap: 18px;
  transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
  scroll-snap-align: center;
  flex: 0 0 calc(100% - 32px);
}

.loan-card:hover,
.loan-card.selected {
  transform: translateY(-4px);
  box-shadow: 0 16px 38px rgba(35, 60, 140, 0.14);
  border-color: rgba(89, 122, 200, 0.35);
}

.loan-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.loan-card__header h3 {
  font-size: 1.2rem;
  margin-bottom: 6px;
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
  gap: 18px;
}

.loan-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
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
  border-radius: 16px;
  border: 1px dashed rgba(92, 108, 255, 0.35);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  gap: 12px;
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
  font-size: 1.2rem;
  font-weight: 600;
}

.offer-item .value.savings {
  color: #1fbb56;
}

.offer-actions {
  display: flex;
  justify-content: flex-end;
}

.btn {
  border: none;
  border-radius: 14px;
  padding: 10px 18px;
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

.state {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 40px 32px;
  text-align: center;
  box-shadow: 0 14px 32px rgba(40, 60, 120, 0.12);
  border: 1px solid rgba(85, 110, 190, 0.1);
}

.state h2 {
  margin-bottom: 12px;
}

.state p {
  margin-bottom: 24px;
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
  gap: 16px;
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
    padding: 24px 16px 64px;
  }
}
</style>
