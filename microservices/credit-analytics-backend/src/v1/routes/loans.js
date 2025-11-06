import { Router } from 'express';
import { bankApiClient, handleAxiosError } from '../../lib/bankApiClient.js';
import { config } from '../../config/env.js';
import { getMockLoanDetails } from '../../lib/mockData.js';

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

    const [agreementsResponse, accountsResponse] = await Promise.all([
      client.get('/product-agreements'),
      client.get('/accounts'),
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

    const loanAgreements = agreements.filter((agreement) => agreement.product_type === 'loan');

    const detailedLoans = await Promise.all(
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

    res.json({ data: detailedLoans, meta: { total: detailedLoans.length } });
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
