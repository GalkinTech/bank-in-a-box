import { Router } from 'express';
import axios from 'axios';
import { bankApiClient, handleAxiosError } from '../../lib/bankApiClient.js';
import { config } from '../../config/env.js';
import { getMockLoanDetails, getMockBankProducts, getMockBankStatus } from '../../lib/mockData.js';
import { fetchExternalLoans } from '../../lib/externalLoansService.js';

const router = Router();

const DEFAULT_FALLBACK_RATE = 9;
const DEFAULT_FALLBACK_TERM = 24;
const DEFAULT_ASSUMED_ORIGINAL_RATE = 15;

const ensureAuthToken = (req) => {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    const error = new Error('Authorization header is required');
    error.status = 401;
    throw error;
  }
  return authHeader;
};

const toNumber = (value, fallback = null) => {
  if (value == null) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const calculateMonthlyPayment = (principal, annualRate, termMonths) => {
  const amount = toNumber(principal, 0);
  const months = toNumber(termMonths, 0);
  const rate = toNumber(annualRate, 0);

  if (!amount || !months || months <= 0) {
    return 0;
  }

  const monthlyRate = rate / 12 / 100;
  if (!monthlyRate) {
    return amount / months;
  }

  const denominator = 1 - Math.pow(1 + monthlyRate, -months);
  if (!denominator) {
    return amount / months;
  }

  return (amount * monthlyRate) / denominator;
};

const getRemainingMonths = (loan, product) => {
  const candidates = [
    toNumber(loan.term_months),
    toNumber(product?.termMonths),
  ].filter((value) => Number.isFinite(value) && value > 0);

  return candidates.length ? candidates[0] : DEFAULT_FALLBACK_TERM;
};

const normalizeProduct = (product) => {
  const productId = product.productId || product.product_id;
  const productType = (product.productType || product.product_type || '').toLowerCase();

  if (!productId || productType !== 'loan') {
    return null;
  }

  const interestRate = toNumber(product.interestRate ?? product.interest_rate);
  if (!Number.isFinite(interestRate)) {
    return null;
  }

  return {
    productId,
    productName: product.productName || product.name || 'Кредитное предложение банка',
    interestRate,
    minAmount: toNumber(product.minAmount ?? product.min_amount),
    maxAmount: toNumber(product.maxAmount ?? product.max_amount),
    termMonths: toNumber(product.termMonths ?? product.term_months),
  };
};

const filterEligibleProducts = (loan, products) => {
  const principal = toNumber(loan.amount, 0);
  if (!products.length) {
    return [];
  }

  if (!principal) {
    return [...products];
  }

  return products.filter((product) => {
    if (Number.isFinite(product.maxAmount) && principal > product.maxAmount) {
      return false;
    }
    return true;
  });
};

const buildOffer = (loan, product) => {
  const principal = toNumber(loan.amount, 0);
  if (!principal) {
    return null;
  }

  const originalRate = toNumber(loan.interest_rate, null);
  const rateToUse = product?.interestRate ?? Math.max(originalRate ? originalRate - 3 : DEFAULT_FALLBACK_RATE + 3, DEFAULT_FALLBACK_RATE);
  const remainingMonths = getRemainingMonths(loan, product);
  const monthlyPayment = calculateMonthlyPayment(principal, rateToUse, remainingMonths);

  let savingsRaw = null;
  const baselineRate = Number.isFinite(originalRate) && originalRate > 0 ? originalRate : DEFAULT_ASSUMED_ORIGINAL_RATE;
  if (baselineRate > rateToUse) {
    savingsRaw = (baselineRate - rateToUse) * principal * remainingMonths;
  }
  const savings = Number.isFinite(savingsRaw) ? Number((savingsRaw / 1200).toFixed(2)) : 0;

  return {
    loan_id: loan.agreement_id,
    original_rate: Number.isFinite(originalRate) && originalRate > 0 ? originalRate : null,
    suggested_rate: Number(rateToUse.toFixed(2)),
    monthly_payment: Number(monthlyPayment.toFixed(2)),
    total_cost: Number((monthlyPayment * remainingMonths).toFixed(2)),
    savings,
    source: product ? 'bank-product' : 'fallback',
    product_id: product?.productId ?? null,
    product_name: product?.productName ?? 'Рефинансирование банка',
    product_term_months: product?.termMonths ?? null,
    assumptions: {
      term_months: remainingMonths,
      principal,
    },
  };
};

const selectBestProductOffer = (loan, products) => {
  const eligible = filterEligibleProducts(loan, products);
  const candidates = eligible.length ? eligible : products;

  if (candidates.length) {
    const sorted = [...candidates].sort((a, b) => {
      if (a.interestRate !== b.interestRate) {
        return a.interestRate - b.interestRate;
      }

      const priority = (product) => {
        const name = (product.productName || '').toLowerCase();
        return name.includes('айтишная ипотека') ? 0 : 1;
      };

      const priorityDiff = priority(a) - priority(b);
      if (priorityDiff) {
        return priorityDiff;
      }

      return (a.termMonths || DEFAULT_FALLBACK_TERM) - (b.termMonths || DEFAULT_FALLBACK_TERM);
    });

    return buildOffer(loan, sorted[0]);
  }

  return buildOffer(loan, null);
};

const isExternalLoan = (loan) => {
  if (!loan) {
    return false;
  }

  if (loan.source) {
    return loan.source === 'external';
  }

  return Boolean(loan.origin_bank && loan.origin_bank !== 'self');
};

const enrichLoansWithOffers = (loans, products) =>
  loans.map((loan) => ({
    ...loan,
    refinance_offer: isExternalLoan(loan) ? selectBestProductOffer(loan, products) : null,
  }));

const fetchExternalBanks = async () => {
  if (!Array.isArray(config.externalBanks)) {
    return [];
  }

  return config.externalBanks;
};

const fetchProductsFromSource = async (baseUrl) => {
  if (!baseUrl) {
    return [];
  }

  const catalogUrl = `${baseUrl.replace(/\/$/, '')}/products`;

  try {
    const response = await axios.get(catalogUrl, {
      headers: {
        Accept: 'application/json',
      },
    });

    const rawProducts = Array.isArray(response.data?.data?.product)
      ? response.data.data.product
      : [];

    return rawProducts.map((product) => normalizeProduct(product)).filter(Boolean);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn('[refinance] failed to load loan products from source', {
      baseUrl,
      url: catalogUrl,
      message: error?.message,
      status: error?.response?.status,
    });
    return [];
  }
};

const expandSourceVariants = (source) => {
  if (!source) {
    return [];
  }

  try {
    const url = new URL(source);
    const variants = new Set([url.toString()]);

    if (['localhost', '127.0.0.1'].includes(url.hostname)) {
      const alternativeHosts = ['127.0.0.1', 'host.docker.internal'];
      alternativeHosts.forEach((host) => {
        if (host !== url.hostname) {
          const altUrl = new URL(url.toString());
          altUrl.hostname = host;
          variants.add(altUrl.toString());
        }
      });
    }

    return Array.from(variants);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn('[refinance] unable to parse product catalog url', { source, message: error?.message });
    return [source];
  }
};

const fetchLocalLoanProducts = async () => {
  const baseSources = [
    config.localProductCatalogBaseUrl,
    config.bankApiBaseUrl,
    process.env.ADDITIONAL_PRODUCT_CATALOG_URL,
  ]
    .map((source) => source?.trim())
    .filter(Boolean);

  const sources = baseSources.flatMap((source) => expandSourceVariants(source));

  const productsById = new Map();

  // Поддерживаем мок-режим, но приоритет отдаём живым данным
  for (const source of sources) {
    const products = await fetchProductsFromSource(source);
    for (const product of products) {
      if (!productsById.has(product.productId)) {
        productsById.set(product.productId, product);
      }
    }
  }

  if (productsById.size) {
    // eslint-disable-next-line no-console
    console.info('[refinance] loaded real loan products', {
      sources,
      total: productsById.size,
    });
    return Array.from(productsById.values());
  }

  return getMockBankProducts();
};

const normalizeBankHealth = (bank, result) => {
  const base = bank.baseUrl ?? '';
  const healthUrl = `${base.replace(/\/$/, '')}/health`;

  if (result.ok) {
    return {
      code: bank.code,
      name: bank.displayName ?? bank.code,
      baseUrl: base,
      status: 'up',
      healthUrl,
      httpStatus: result.status,
      message: null,
    };
  }

  return {
    code: bank.code,
    name: bank.displayName ?? bank.code,
    baseUrl: base,
    status: 'down',
    healthUrl,
    httpStatus: result.status ?? null,
    message: result.message ?? 'Недоступен',
  };
};

router.get('/banks/health', async (req, res) => {
  try {
    if (config.useMockData) {
      res.json(getMockBankStatus());
      return;
    }

    const banks = await fetchExternalBanks();
    const healthChecks = await Promise.all(
      banks.map(async (bank) => {
        const response = await fetch(`${bank.baseUrl}/health`);
        return normalizeBankHealth(bank, response);
      })
    );

    res.json(healthChecks);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('[refinance] failed to fetch banks health', error);
    res.status(500).json({ error: 'Failed to fetch banks health' });
  }
});

router.get('/suggestions', async (req, res) => {
  try {
    if (config.useMockData) {
      const mockLoans = getMockLoanDetails();
      const bankProducts = await fetchLocalLoanProducts();
      const enrichedMockLoans = enrichLoansWithOffers(mockLoans, bankProducts);

      res.json({
        data: enrichedMockLoans,
        meta: {
          total: enrichedMockLoans.length,
          source: 'mock',
          bank_products_considered: bankProducts.length,
        },
      });
      return;
    }

    const authHeader = ensureAuthToken(req);
    const client = bankApiClient(authHeader);

    const [agreementsResponse, localProducts, externalLoansRaw] = await Promise.all([
      client.get('/product-agreements'),
      fetchLocalLoanProducts(),
      fetchExternalLoans().catch((error) => {
        // eslint-disable-next-line no-console
        console.warn('[refinance] Failed to fetch external loans', error);
        return [];
      }),
    ]);

    const agreements = agreementsResponse.data?.data ?? [];
    const bankProducts = Array.isArray(localProducts) ? localProducts : [];

    const internalLoans = agreements
      .filter((agreement) => agreement.product_type === 'loan')
      .map((agreement) => ({
        ...agreement,
        source: agreement.source ?? 'internal',
      }));

    const externalLoans = Array.isArray(externalLoansRaw) ? externalLoansRaw : [];

    const combinedLoans = [...internalLoans, ...externalLoans];

    const enrichedLoans = enrichLoansWithOffers(combinedLoans, bankProducts);

    res.json({
      data: enrichedLoans,
      meta: {
        total: enrichedLoans.length,
        bank_products_considered: bankProducts.length,
        external_sources: externalLoans.length,
      },
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('[refinance] failed to build suggestions', error);
    if (error.status) {
      res.status(error.status).json({ error: error.message });
      return;
    }

    const formatted = handleAxiosError(error);
    // eslint-disable-next-line no-console
    console.error('[refinance] formatted axios error', formatted);
    const status = Number.isInteger(formatted.status) ? formatted.status : 500;
    res.status(status).json({ error: formatted.message, details: formatted.data });
  }
});

router.post('/applications', async (req, res) => {
  const forceReal =
    config.forceRealRefinanceApplications
    || req.query?.force_real === 'true'
    || req.query?.forceReal === 'true'
    || req.body?.force_real === true
    || req.body?.force_real === 'true'
    || req.headers['x-force-real'] === 'true';

  try {
    const {
      agreement_id: agreementId,
      desired_term_months: desiredTermMonths,
      comment,
      product_id: providedProductId,
      amount: providedAmount,
      offer_term_months: offerTermMonths,
    } = req.body ?? {};

    if (!agreementId) {
      res.status(400).json({ error: 'agreement_id is required' });
      return;
    }

    if (config.useMockData && !forceReal) {
      const amountValue = toNumber(providedAmount, 500000);
      res.status(201).json({
        status: 'mock-submitted',
        data: {
          agreement: {
            agreement_id: `agr-mock-${Date.now()}`,
            product_id: providedProductId ?? 'prod-mock-refinance',
            product_name: 'Моковый кредит на рефинансирование',
            product_type: 'loan',
            amount: amountValue,
            status: 'pending',
            start_date: new Date().toISOString(),
            end_date: null,
            account_number: null,
          },
        },
        meta: {
          agreement_id: agreementId,
          product_id: providedProductId ?? 'prod-mock-refinance',
          amount: amountValue,
          term_months: offerTermMonths ?? desiredTermMonths ?? DEFAULT_FALLBACK_TERM,
          comment: comment ?? null,
          mock: true,
        },
      });
      return;
    }

    const authHeader = ensureAuthToken(req);
    const client = bankApiClient(authHeader);

    const [agreementsResponse, localProducts, externalLoansRaw] = await Promise.all([
      client.get('/product-agreements'),
      fetchLocalLoanProducts(),
      fetchExternalLoans().catch((error) => {
        // eslint-disable-next-line no-console
        console.warn('[refinance] Failed to fetch external loans for application', error);
        return [];
      }),
    ]);

    const agreements = agreementsResponse.data?.data ?? [];
    const bankProducts = Array.isArray(localProducts) ? localProducts : [];

    const internalLoans = agreements
      .filter((agreement) => agreement.product_type === 'loan')
      .map((agreement) => ({
        ...agreement,
        source: agreement.source ?? 'internal',
      }));

    const externalLoans = Array.isArray(externalLoansRaw) ? externalLoansRaw : [];
    const combinedLoans = [...internalLoans, ...externalLoans];
    const enrichedLoans = enrichLoansWithOffers(combinedLoans, bankProducts);

    const sourceLoan = enrichedLoans.find(
      (loan) => loan.agreement_id === agreementId || loan.loan_id === agreementId
    );

    if (!sourceLoan) {
      res.status(404).json({ error: 'Loan agreement not found for refinance application' });
      return;
    }

    const loanSnapshot = { ...sourceLoan };

    const selectedOffer = loanSnapshot.refinance_offer || null;

    const targetProductId = providedProductId
      || selectedOffer?.product_id
      || bankProducts[0]?.productId
      || null;

    if (!targetProductId) {
      res.status(409).json({ error: 'No refinance offer available to create a product' });
      return;
    }

    const targetProduct = bankProducts.find((product) => product.productId === targetProductId);
    if (!targetProduct) {
      res.status(404).json({ error: `Product ${targetProductId} not found in bank catalogue` });
      return;
    }

    const candidateTermMonths = [
      toNumber(desiredTermMonths),
      toNumber(offerTermMonths),
      toNumber(selectedOffer?.product_term_months),
      toNumber(selectedOffer?.assumptions?.term_months),
      toNumber(loanSnapshot?.remaining_term_months),
      toNumber(targetProduct.termMonths),
    ].filter((value) => Number.isFinite(value) && value > 0);

    const resolvedTermMonths = candidateTermMonths.length
      ? Math.round(candidateTermMonths[0])
      : DEFAULT_FALLBACK_TERM;

    const candidateAmounts = [
      toNumber(providedAmount),
      toNumber(selectedOffer?.assumptions?.principal),
      toNumber(loanSnapshot?.amount),
      toNumber(targetProduct.minAmount),
    ].filter((value) => Number.isFinite(value) && value > 0);

    let resolvedAmount = candidateAmounts.length ? candidateAmounts[0] : null;

    if (!Number.isFinite(resolvedAmount) || resolvedAmount <= 0) {
      // eslint-disable-next-line no-console
      console.warn('[refinance] invalid resolved amount', {
        agreementId,
        candidateAmounts,
        providedAmount,
        sourceLoanAmount: loanSnapshot?.amount,
        selectedOffer,
      });
      res.status(400).json({
        error: 'Unable to determine refinance amount for product creation',
        details: {
          candidateAmounts,
          providedAmount,
          sourceLoanAmount: loanSnapshot?.amount ?? null,
          offer: selectedOffer,
        },
      });
      return;
    }

    if (Number.isFinite(targetProduct.minAmount) && resolvedAmount < targetProduct.minAmount) {
      resolvedAmount = Number(targetProduct.minAmount);
    }

    if (Number.isFinite(targetProduct.maxAmount) && resolvedAmount > targetProduct.maxAmount) {
      resolvedAmount = Number(targetProduct.maxAmount);
    }

    const createPayload = {
      product_id: targetProductId,
      amount: Number(resolvedAmount.toFixed(2)),
      term_months: resolvedTermMonths,
    };

    // eslint-disable-next-line no-console
    console.log('[refinance] creating product agreement', {
      agreementId,
      createPayload,
      sourceLoan: {
        agreement_id: loanSnapshot.agreement_id,
        amount: loanSnapshot.amount,
        offer: selectedOffer,
      },
    });

    const createResponse = await client.post('/product-agreements', createPayload);
    const createdAgreement = createResponse.data?.data ?? null;

    res.status(201).json({
      status: createResponse.data?.meta?.message ?? 'created',
      data: {
        agreement: createdAgreement,
      },
      meta: {
        agreement_id: agreementId,
        product_id: targetProductId,
        amount: createPayload.amount,
        term_months: createPayload.term_months,
        comment: comment ?? null,
        offer: selectedOffer,
        loan_snapshot: loanSnapshot,
      },
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('[refinance] failed to submit application', {
      error: error.message,
      status: error.status,
      details: error.details,
      stack: error.stack,
    });

    if (error.status) {
      res.status(error.status).json({ error: error.message, details: error.details });
      return;
    }

    const formatted = handleAxiosError(error);
    res.status(formatted.status).json({ error: formatted.message, details: formatted.data });
  }
});

router.get('/status', async (req, res) => {
  try {
    ensureAuthToken(req);

    if (config.useMockData) {
      res.json({
        data: {
          banks: getMockBankStatus(),
          last_checked: new Date().toISOString(),
          source: 'mock',
        },
      });
      return;
    }

    const banks = await Promise.all(
      config.externalBanks.map(async (bank) => {
        const healthUrl = `${bank.baseUrl.replace(/\/$/, '')}/health`;

        try {
          const response = await axios.get(healthUrl, {
            timeout: config.externalBankTimeoutMs,
            validateStatus: () => true,
          });

          const ok = response.status >= 200 && response.status < 300;
          return normalizeBankHealth(bank, {
            ok,
            status: response.status,
            message: ok ? null : response.statusText,
          });
        } catch (error) {
          const status = error?.response?.status;
          const message = error?.response?.statusText || error?.message || 'Unknown error';
          return normalizeBankHealth(bank, {
            ok: false,
            status,
            message,
          });
        }
      })
    );

    res.json({
      data: {
        banks,
        last_checked: new Date().toISOString(),
      },
    });
  } catch (error) {
    if (error.status) {
      res.status(error.status).json({ error: error.message });
      return;
    }

    const formatted = handleAxiosError(error);
    const status = Number.isInteger(formatted.status) ? formatted.status : 500;
    res.status(status).json({ error: formatted.message, details: formatted.data });
  }
});

export default router;
