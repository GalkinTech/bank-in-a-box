import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const envPath = path.join(__dirname, '../../.env');
dotenv.config({ path: envPath, override: false });

const requiredEnv = ['BANK_API_BASE_URL'];

requiredEnv.forEach((key) => {
  if (!process.env[key]) {
    // eslint-disable-next-line no-console
    console.warn(`Environment variable ${key} is not set. Using default fallback.`);
  }
});

export const config = {
  port: Number(process.env.PORT ?? 8100),
  bankApiBaseUrl: process.env.BANK_API_BASE_URL ?? 'http://localhost:8080',
  bankApiTimeoutMs: Number(process.env.BANK_API_TIMEOUT_MS ?? 10000),
  useMockData: process.env.USE_MOCK_DATA === 'true',
};
