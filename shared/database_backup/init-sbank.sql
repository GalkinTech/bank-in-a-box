-- SBank - создание таблиц и тестовые данные

-- Создание таблиц
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
('cli-sb-001', 'individual', 'Лебедев Андрей Николаевич', 'employee', 1983, 70000),
('cli-sb-002', 'individual', 'Кузнецова Ольга Петровна', 'employee', 1992, 55000),
('cli-sb-003', 'individual', 'Павлов Максим Викторович', 'student', 2002, 10000),
('cli-sb-004', 'legal', 'ИП Васильев А.А.', 'individual_entrepreneur', NULL, 150000),
('cli-sb-005', 'individual', 'Соколова Екатерина Ивановна', 'pensioner', 1960, 20000);

-- Счета
INSERT INTO accounts (client_id, account_number, account_type, balance, currency, status) VALUES
(1, '40817810099930001001', 'checking', 95000.00, 'RUB', 'active'),
(2, '40817810099930002001', 'checking', 72000.50, 'RUB', 'active'),
(3, '40817810099930003001', 'checking', 12500.00, 'RUB', 'active'),
(4, '40802810099930004001', 'checking', 380000.75, 'RUB', 'active'),
(5, '40817810099930005001', 'checking', 35000.00, 'RUB', 'active');

-- Транзакции
INSERT INTO transactions (account_id, transaction_id, amount, direction, counterparty, description, transaction_date) VALUES
(1, 'tx-sb-001-001', 70000.00, 'credit', 'ООО Работодатель', 'Зарплата', '2025-10-01 10:00:00'),
(1, 'tx-sb-001-002', -8000.00, 'debit', 'Супермаркет', 'Продукты', '2025-10-02 18:00:00'),
(2, 'tx-sb-002-001', 55000.00, 'credit', 'ООО Компания', 'Зарплата', '2025-10-01 10:00:00'),
(3, 'tx-sb-003-001', 10000.00, 'credit', 'Родители', 'Помощь', '2025-10-01 12:00:00'),
(4, 'tx-sb-004-001', 150000.00, 'credit', 'Клиенты', 'Услуги', '2025-09-28 15:00:00'),
(5, 'tx-sb-005-001', 20000.00, 'credit', 'ПФР', 'Пенсия', '2025-10-01 08:00:00');

-- Настройки банка
INSERT INTO bank_settings (key, value) VALUES
('bank_code', 'sbank'),
('bank_name', 'Smart Bank'),
('public_address', 'http://localhost:8003'),
('capital', '3000000.00')
ON CONFLICT (key) DO NOTHING;

-- Капитал банка
INSERT INTO bank_capital (bank_code, capital, initial_capital, total_deposits, total_loans) VALUES
('sbank', 3000000.00, 3000000.00, 0, 0)
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
('prod-sb-deposit-001', 'deposit', 'Умный депозит', 'Ставка 8.0% годовых', 8.0, 30000, 6),
('prod-sb-card-001', 'card', 'Дебетовая карта Smart', 'Кэшбэк 2%, без комиссий', 0.0, 0, NULL),
('prod-sb-loan-001', 'loan', 'Экспресс кредит', 'Ставка 14.0% годовых', 14.0, 30000, 18);


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
