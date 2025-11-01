-- OneBank - создание таблиц и тестовые данные

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
('cli-ob-001', 'individual', 'Иванов Иван Иванович', 'employee', 1985, 80000),
('cli-ob-002', 'individual', 'Петрова Мария Сергеевна', 'employee', 1990, 95000),
('cli-ob-003', 'individual', 'Сидоров Петр Алексеевич', 'pensioner', 1955, 25000),
('cli-ob-004', 'legal', 'ООО Рога и Копыта', 'small_business', NULL, 500000),
('cli-ob-005', 'individual', 'Козлов Алексей Дмитриевич', 'student', 2001, 15000);

-- Счета
INSERT INTO accounts (client_id, account_number, account_type, balance, currency, status) VALUES
(1, '40817810099910001001', 'checking', 125000.50, 'RUB', 'active'),
(1, '42301810099910001002', 'savings', 250000.00, 'RUB', 'active'),
(2, '40817810099910002001', 'checking', 185000.75, 'RUB', 'active'),
(3, '40817810099910003001', 'checking', 45000.00, 'RUB', 'active'),
(4, '40702810099910004001', 'checking', 1250000.00, 'RUB', 'active'),
(5, '40817810099910005001', 'checking', 8500.25, 'RUB', 'active');

-- Транзакции (последние)
INSERT INTO transactions (account_id, transaction_id, amount, direction, counterparty, description, transaction_date) VALUES
(1, 'tx-ob-001-001', 80000.00, 'credit', 'ООО Работодатель', 'Зачисление зарплаты', '2025-10-01 10:00:00'),
(1, 'tx-ob-001-002', -5000.00, 'debit', 'Продуктовый магазин', 'Покупка продуктов', '2025-10-02 14:30:00'),
(1, 'tx-ob-001-003', -2500.00, 'debit', 'АЗС', 'Заправка автомобиля', '2025-10-03 09:15:00'),
(2, 'tx-ob-002-001', 95000.00, 'credit', 'ООО Компания', 'Зарплата', '2025-10-01 10:00:00'),
(2, 'tx-ob-002-002', -12000.00, 'debit', 'Магазин электроники', 'Покупка ноутбука', '2025-10-05 16:00:00'),
(3, 'tx-ob-003-001', 25000.00, 'credit', 'ПФР', 'Пенсия', '2025-10-01 08:00:00'),
(4, 'tx-ob-004-001', 500000.00, 'credit', 'Клиент оплата', 'Поступление от продаж', '2025-09-30 12:00:00'),
(5, 'tx-ob-005-001', 15000.00, 'credit', 'Родители', 'Стипендия + помощь', '2025-10-01 09:00:00');

-- Настройки банка
INSERT INTO bank_settings (key, value) VALUES
('bank_code', 'onebank'),
('bank_name', 'Единый мультибанковский финансовый аналитический центр'),
('public_address', 'https://onebank.ru'),
('capital', '3500000.00')
ON CONFLICT (key) DO NOTHING;

-- Капитал банка
INSERT INTO bank_capital (bank_code, capital, initial_capital, total_deposits, total_loans) VALUES
('onebank', 3500000.00, 3500000.00, 0, 0)
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
('prod-ob-deposit-001', 'deposit', 'Накопительный депозит', 'Ставка 8.5% годовых', 8.5, 50000, 12),
('prod-ob-card-001', 'credit_card', 'Кредитная карта Premium', 'Ставка 15.9%, кэшбэк 5%', 15.9, 0, NULL),
('prod-ob-loan-001', 'loan', 'Потребительский кредит', 'Ставка 12.9% годовых', 12.9, 50000, 36);


-- История ключевой ставки ЦБ
CREATE TABLE IF NOT EXISTS key_rate_history (
    id SERIAL PRIMARY KEY,
    rate NUMERIC(5, 2) NOT NULL,
    effective_from TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Начальная ключевая ставка
INSERT INTO key_rate_history (rate, changed_by) VALUES (7.50, 'system');

-- Настройки системы
INSERT INTO bank_settings (key, value) VALUES 
('key_rate', '7.50'),
('auto_approve_consents', 'true')
ON CONFLICT (key) DO NOTHING;
