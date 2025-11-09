import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const envPath = path.join(__dirname, '../../.env');
dotenv.config({ path: envPath, override: true });

const requiredEnv = ['BANK_API_BASE_URL'];

requiredEnv.forEach((key) => {
  if (!process.env[key]) {
    // eslint-disable-next-line no-console
    console.warn(`Environment variable ${key} is not set. Using default fallback.`);
  }
});

const parseNumber = (value, fallback) => {
  if (value == null) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const buildExternalBankConfig = () => {
  const bankEntries = [
    {
      code: 'vbank',
      displayName: 'Virtual Bank',
      baseUrl: process.env.VBANK_API_BASE,
      consentId: process.env.VBANK_PRODUCT_AGREEMENT_CONSENT_ID,
      accountConsentId: process.env.VBANK_ACCOUNT_CONSENT_ID,
      token: process.env.VBANK_CLIENT_TOKEN,
    },
    {
      code: 'abank',
      displayName: 'Awesome Bank',
      baseUrl: process.env.ABANK_API_BASE,
      consentId: process.env.ABANK_PRODUCT_AGREEMENT_CONSENT_ID,
      accountConsentId: process.env.ABANK_ACCOUNT_CONSENT_ID,
      token: process.env.ABANK_CLIENT_TOKEN,
    },
    {
      code: 'sbank',
      displayName: 'Smart Bank',
      baseUrl: process.env.SBANK_API_BASE,
      consentId: process.env.SBANK_PRODUCT_AGREEMENT_CONSENT_ID,
      accountConsentId: process.env.SBANK_ACCOUNT_CONSENT_ID,
      token: process.env.SBANK_CLIENT_TOKEN,
    },
  ];

  return bankEntries
    .filter((bank) => bank.baseUrl && bank.consentId)
    .map((bank) => ({
      ...bank,
      baseUrl: bank.baseUrl.trim(),
      consentId: bank.consentId.trim(),
      accountConsentId: bank.accountConsentId?.trim() ?? null,
    }));
};

export const config = {
  port: Number(process.env.PORT ?? 8100),
  bankApiBaseUrl: process.env.BANK_API_BASE_URL ?? 'http://localhost:8080',
  bankApiTimeoutMs: Number(process.env.BANK_API_TIMEOUT_MS ?? 10000),
  useMockData: process.env.USE_MOCK_DATA === 'true',
  useMockExternalBanks: process.env.USE_MOCK_EXTERNAL_BANKS === 'true',
  forceRealRefinanceApplications: process.env.FORCE_REAL_REFINANCE === 'true',
  teamClientId: process.env.TEAM_CLIENT_ID ?? null,
  teamClientSecret: process.env.TEAM_CLIENT_SECRET ?? null,
  externalClientId: process.env.EXTERNAL_CLIENT_ID ?? null,
  externalBankTimeoutMs: parseNumber(process.env.EXTERNAL_BANK_TIMEOUT_MS, Number(process.env.BANK_API_TIMEOUT_MS ?? 10000)),
  externalBanks: buildExternalBankConfig(),
  localProductCatalogBaseUrl: process.env.LOCAL_PRODUCT_CATALOG_BASE_URL ?? 'http://localhost:8080',
};
