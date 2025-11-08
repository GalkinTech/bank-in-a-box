import { Router } from 'express';
import { bankApiClient, handleAxiosError } from '../../lib/bankApiClient.js';
import { config } from '../../config/env.js';
import { getMockLoanDetails } from '../../lib/mockData.js';
import { fetchExternalLoans } from '../../lib/externalLoansService.js';

const router = Router();

const ensureAuthToken = (req) => {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    const error = new Error('Authorization header is required');
    error.status = 401;
    throw error;
  }
  return authHeader;
};

router.get('/active', async (req, res, next) => {
  try {
    if (config.useMockData) {
      const detailedLoans = getMockLoanDetails();
      res.json({ data: detailedLoans, meta: { total: detailedLoans.length, source: 'mock' } });
      return;
    }

    const authHeader = ensureAuthToken(req);
    const client = bankApiClient(authHeader);

    const agreementsPromise = client.get('/product-agreements').catch((error) => {
      // eslint-disable-next-line no-console
      console.warn('[loans] Failed to fetch internal product agreements', handleAxiosError(error));
      return { data: { data: [] } };
    });

    const accountsPromise = client.get('/accounts').catch((error) => {
      // eslint-disable-next-line no-console
      console.warn('[loans] Failed to fetch internal accounts', handleAxiosError(error));
      return { data: { data: { account: [] } } };
    });

    const externalLoansPromise = fetchExternalLoans().catch((error) => {
      // eslint-disable-next-line no-console
      console.warn('[loans] Failed to fetch external loans', error);
      return [];
    });

    const [agreementsResponse, accountsResponse, externalLoans] = await Promise.all([
      agreementsPromise,
      accountsPromise,
      externalLoansPromise,
    ]);

    const agreements = agreementsResponse.data?.data ?? [];
    const accountEntries = accountsResponse.data?.data?.account ?? [];

    const accountIdByNumber = accountEntries.reduce((acc, item) => {
      const accountNumber = item?.account?.[0]?.identification;
      const accountId = item?.accountId;
      if (accountNumber && accountId) {
        acc[accountNumber] = accountId;
      }
      return acc;
    }, {});

    const loanAgreements = agreements
      .filter((agreement) => agreement.product_type === 'loan')
      .map((agreement) => ({ ...agreement, source: 'internal' }));

    const enrichedInternalLoans = await Promise.all(
      loanAgreements.map(async (agreement) => {
        const accountNumber = agreement.account_number;
        const accountId = accountNumber ? accountIdByNumber[accountNumber] : undefined;

        if (!accountId) {
          return {
            ...agreement,
            account_id: accountId ?? null,
            balance: null,
            balance_error: accountNumber
              ? {
                  status: 404,
                  message: 'Account ID not found for provided account number',
                }
              : null,
          };
        }

        try {
          const balanceResponse = await client.get(`/accounts/${accountId}/balances`);
          return {
            ...agreement,
            account_id: accountId,
            balance: balanceResponse.data?.data?.balance ?? [],
          };
        } catch (balanceError) {
          return {
            ...agreement,
            account_id: accountId,
            balance: null,
            balance_error: handleAxiosError(balanceError),
          };
        }
      })
    );

    const combinedLoans = [...enrichedInternalLoans, ...externalLoans];

    res.json({
      data: combinedLoans,
      meta: {
        total: combinedLoans.length,
        external_sources: Array.isArray(externalLoans) ? externalLoans.length : 0,
      },
    });
  } catch (error) {
    if (error.status) {
      res.status(error.status).json({ error: error.message });
      return;
    }

    const formatted = handleAxiosError(error);
    res.status(formatted.status).json({ error: formatted.message, details: formatted.data });
  }
});

export default router;
