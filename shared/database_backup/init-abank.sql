-- ABank - создание таблиц и тестовые данные

-- Создание таблиц (те же что в vbank)
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    person_id VARCHAR(100) UNIQUE,
    client_type VARCHAR(20),
    full_name VARCHAR(255) NOT NULL,
    segment VARCHAR(50),
    birth_year INTEGER,
    monthly_income NUMERIC(15, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_type VARCHAR(50),
    balance NUMERIC(15, 2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'RUB',
    status VARCHAR(20) DEFAULT 'active',
    opened_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    direction VARCHAR(10),
    counterparty VARCHAR(255),
    description TEXT,
    transaction_date TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bank_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id SERIAL PRIMARY KEY,
    token_type VARCHAR(20),
    subject_id VARCHAR(100),
    token_hash VARCHAR(255),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    payment_id VARCHAR(100) UNIQUE NOT NULL,
    account_id INTEGER REFERENCES accounts(id),
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    destination_account VARCHAR(255),
    destination_bank VARCHAR(100),
    description TEXT,
    status VARCHAR(50) DEFAULT 'AcceptedSettlementInProcess',
    creation_date_time TIMESTAMP DEFAULT NOW(),
    status_update_date_time TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interbank_transfers (
    id SERIAL PRIMARY KEY,
    transfer_id VARCHAR(100) UNIQUE NOT NULL,
    payment_id VARCHAR(100) REFERENCES payments(payment_id),
    from_bank VARCHAR(100) NOT NULL,
    to_bank VARCHAR(100) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_capital (
    id SERIAL PRIMARY KEY,
    bank_code VARCHAR(100) UNIQUE NOT NULL,
    capital NUMERIC(15, 2) NOT NULL,
    initial_capital NUMERIC(15, 2) NOT NULL,
    total_deposits NUMERIC(15, 2) DEFAULT 0,
    total_loans NUMERIC(15, 2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Клиенты
INSERT INTO clients (person_id, client_type, full_name, segment, birth_year, monthly_income) VALUES
('cli-ab-001', 'individual', 'Смирнова Анна Викторовна', 'employee', 1988, 120000),
('cli-ab-002', 'individual', 'Волков Дмитрий Павлович', 'employee', 1982, 150000),
('cli-ab-003', 'individual', 'Новикова Елена Андреевна', 'entrepreneur', 1975, 200000),
('cli-ab-004', 'legal', 'ООО Инновации', 'startup', NULL, 800000),
('cli-ab-005', 'individual', 'Морозов Сергей Игоревич', 'employee', 1995, 65000);

-- Счета
INSERT INTO accounts (client_id, account_number, account_type, balance, currency, status) VALUES
(1, '40817810099920001001', 'checking', 320000.00, 'RUB', 'active'),
(2, '40817810099920002001', 'checking', 450000.50, 'RUB', 'active'),
(2, '42301810099920002002', 'savings', 800000.00, 'RUB', 'active'),
(3, '40817810099920003001', 'checking', 550000.75, 'RUB', 'active'),
(4, '40702810099920004001', 'checking', 2100000.00, 'RUB', 'active'),
(5, '40817810099920005001', 'checking', 95000.30, 'RUB', 'active');

-- Транзакции
INSERT INTO transactions (account_id, transaction_id, amount, direction, counterparty, description, transaction_date) VALUES
(1, 'tx-ab-001-001', 120000.00, 'credit', 'ООО Работодатель', 'Зарплата', '2025-10-01 10:00:00'),
(1, 'tx-ab-001-002', -15000.00, 'debit', 'Ресторан', 'Ужин', '2025-10-03 20:00:00'),
(2, 'tx-ab-002-001', 150000.00, 'credit', 'ООО Компания', 'Зарплата', '2025-10-01 10:00:00'),
(2, 'tx-ab-002-002', -25000.00, 'debit', 'Туристическое агентство', 'Путевка', '2025-10-04 11:00:00'),
(3, 'tx-ab-003-001', 200000.00, 'credit', 'Клиенты', 'Доход от бизнеса', '2025-09-30 18:00:00'),
(4, 'tx-ab-004-001', 1500000.00, 'credit', 'Инвестор', 'Раунд инвестиций', '2025-09-15 14:00:00'),
(5, 'tx-ab-005-001', 65000.00, 'credit', 'ООО Работодатель', 'Зарплата', '2025-10-01 10:00:00');

-- Настройки банка
INSERT INTO bank_settings (key, value) VALUES
('bank_code', 'abank'),
('bank_name', 'Awesome Bank'),
('public_address', 'http://localhost:8002'),
('capital', '3500000.00')
ON CONFLICT (key) DO NOTHING;

-- Капитал банка
INSERT INTO bank_capital (bank_code, capital, initial_capital, total_deposits, total_loans) VALUES
('abank', 3500000.00, 3500000.00, 0, 0)
ON CONFLICT (bank_code) DO NOTHING;



-- Продукты банка
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(100) UNIQUE NOT NULL,
    product_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    interest_rate NUMERIC(5, 2),
    min_amount NUMERIC(15, 2),
    max_amount NUMERIC(15, 2),
    term_months INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO products (product_id, product_type, name, description, interest_rate, min_amount, term_months) VALUES
('prod-ab-deposit-001', 'deposit', 'Выгодный депозит', 'Ставка 9.0% годовых', 9.0, 100000, 12),
('prod-ab-card-001', 'card', 'Кредитная карта Gold', 'Ставка 16.5%, кэшбэк 3%', 16.5, 0, NULL),
('prod-ab-loan-001', 'loan', 'Кредит наличными', 'Ставка 13.5% годовых', 13.5, 100000, 24);


-- Договоры с продуктами
CREATE TABLE IF NOT EXISTS product_agreements (
    id SERIAL PRIMARY KEY,
    agreement_id VARCHAR(100) UNIQUE NOT NULL,
    client_id INTEGER REFERENCES clients(id),
    product_id INTEGER REFERENCES products(id),
    account_id INTEGER REFERENCES accounts(id),
    amount NUMERIC(15, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    start_date TIMESTAMP DEFAULT NOW(),
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);


-- История ключевой ставки ЦБ
CREATE TABLE IF NOT EXISTS key_rate_history (
    id SERIAL PRIMARY KEY,
    rate NUMERIC(5, 2) NOT NULL,
    effective_from TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO key_rate_history (rate, changed_by) VALUES (7.50, 'system');

-- Обновление настроек
INSERT INTO bank_settings (key, value) VALUES 
('key_rate', '7.50'),
('auto_approve_consents', 'true')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
