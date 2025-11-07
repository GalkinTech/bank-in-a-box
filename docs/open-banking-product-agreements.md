# Получение договоров клиента через Open Banking

Ниже собран пошаговый сценарий для команды `team018`, позволяющий выгрузить договоры клиента `team018-1` из банков VBank, ABank и SBank.

## Общие переменные окружения

```bash
export TEAM_CLIENT_ID=team018
export TEAM_CLIENT_SECRET=d78xBRvntBFr6FkxVHLRrfcWXte25QoM
export CLIENT_ID=team018-1
```

## VBank

```bash
# 1. Получаем командный токен
export TEAM_TOKEN_VBANK=$(curl -s -G "https://vbank.open.bankingapi.ru/auth/bank-token" \
  --data-urlencode "client_id=$TEAM_CLIENT_ID" \
  --data-urlencode "client_secret=$TEAM_CLIENT_SECRET" | jq -r '.access_token')

# 2. Запрашиваем consent (автоодобрение)
curl -s -X POST "https://vbank.open.bankingapi.ru/product-agreement-consents/request?client_id=$CLIENT_ID" \
  -H "Authorization: Bearer $TEAM_TOKEN_VBANK" \
  -H "Content-Type: application/json" \
  -d '{
        "requesting_bank": "team018",
        "client_id": "'"$CLIENT_ID"'",
        "read_product_agreements": true,
        "open_product_agreements": false,
        "close_product_agreements": false,
        "allowed_product_types": ["deposit","card","loan"],
        "reason": "Агрегатор команды team018"
      }' | jq

# 3. Сохраняем consent ID
export VBANK_PRODUCT_AGREEMENT_CONSENT_ID=pagc-1ba3070c51e5

# 4. Получаем договоры
curl -s "https://vbank.open.bankingapi.ru/product-agreements" \
  -H "Authorization: Bearer $TEAM_TOKEN_VBANK" \
  -H "x-requesting-bank: team018" \
  -H "x-product-agreement-consent-id: $VBANK_PRODUCT_AGREEMENT_CONSENT_ID" \
  -G --data-urlencode "client_id=$CLIENT_ID" | jq
```

Пример ответа (сокращённо):

```json
{
  "data": [
    {
      "agreement_id": "agr-2f189c66585e",
      "product_name": "Ипотека VBank 9.3%",
      "product_type": "loan",
      "amount": 1800000.0,
      "status": "active",
      "start_date": "2025-11-06T19:11:27.212166",
      "end_date": "2045-07-24T19:11:27.209950",
      "account_number": "455d5d7a74bb3be416"
    }
  ],
  "meta": { "total": 2 }
}
```

## ABank

```bash
# 1. Токен команды
export TEAM_TOKEN_ABANK=$(curl -s -G "https://abank.open.bankingapi.ru/auth/bank-token" \
  --data-urlencode "client_id=$TEAM_CLIENT_ID" \
  --data-urlencode "client_secret=$TEAM_CLIENT_SECRET" | jq -r '.access_token')

# 2. Запрашиваем consent (автоодобрение)
curl -s -X POST "https://abank.open.bankingapi.ru/product-agreement-consents/request?client_id=$CLIENT_ID" \
  -H "Authorization: Bearer $TEAM_TOKEN_ABANK" \
  -H "Content-Type: application/json" \
  -d '{
        "requesting_bank": "team018",
        "client_id": "'"$CLIENT_ID"'",
        "read_product_agreements": true,
        "open_product_agreements": false,
        "close_product_agreements": false,
        "allowed_product_types": ["deposit","card","loan"],
        "reason": "Агрегатор команды team018"
      }' | jq

# 3. Сохраняем consent ID
export ABANK_PRODUCT_AGREEMENT_CONSENT_ID=pagc-bec67e156704

# 4. Получаем договоры
curl -s "https://abank.open.bankingapi.ru/product-agreements" \
  -H "Authorization: Bearer $TEAM_TOKEN_ABANK" \
  -H "x-requesting-bank: team018" \
  -H "x-product-agreement-consent-id: $ABANK_PRODUCT_AGREEMENT_CONSENT_ID" \
  -G --data-urlencode "client_id=$CLIENT_ID" | jq
```

Ответ (сокращённо):

```json
{
  "data": [
    {
      "agreement_id": "agr-7813df17497b",
      "product_name": "Экспресс кредит 14.2%",
      "product_type": "loan",
      "amount": 420000.0,
      "status": "active",
      "start_date": "2025-11-06T19:10:56.486107",
      "end_date": "2029-10-16T19:10:56.480296",
      "account_number": "455dc2b060e5942402"
    }
  ],
  "meta": { "total": 1 }
}
```

## SBank

```bash
# 1. Токен команды
export TEAM_TOKEN_SBANK=$(curl -s -G "https://sbank.open.bankingapi.ru/auth/bank-token" \
  --data-urlencode "client_id=$TEAM_CLIENT_ID" \
  --data-urlencode "client_secret=$TEAM_CLIENT_SECRET" | jq -r '.access_token')

# 2. Запрос consent (требуется подпись клиента)
curl -s -X POST "https://sbank.open.bankingapi.ru/product-agreement-consents/request?client_id=$CLIENT_ID" \
  -H "Authorization: Bearer $TEAM_TOKEN_SBANK" \
  -H "Content-Type: application/json" \
  -d '{
        "requesting_bank": "team018",
        "client_id": "'"$CLIENT_ID"'",
        "read_product_agreements": true,
        "open_product_agreements": false,
        "close_product_agreements": false,
        "allowed_product_types": ["deposit","card","loan"],
        "reason": "Агрегатор команды team018"
      }' | jq

# 3. Подписываем запрос от имени клиента
export SBANK_CLIENT_TOKEN=<JWT_клиента_из_.env>
export REQUEST_ID=pagcr-8e8a8b860ece  # значение из шага 2

curl -s -X POST "https://sbank.open.bankingapi.ru/product-agreement-consents/sign" \
  -H "Authorization: Bearer $SBANK_CLIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "request_id": "'"$REQUEST_ID"'",
        "action": "approve",
        "signature": "password"
      }' | jq

# 4. Сохраняем consent ID
export SBANK_PRODUCT_AGREEMENT_CONSENT_ID=pagc-00293a4eafc4

# 5. Получаем договоры
curl -s "https://sbank.open.bankingapi.ru/product-agreements" \
  -H "Authorization: Bearer $TEAM_TOKEN_SBANK" \
  -H "x-requesting-bank: team018" \
  -H "x-product-agreement-consent-id: $SBANK_PRODUCT_AGREEMENT_CONSENT_ID" \
  -G --data-urlencode "client_id=$CLIENT_ID" | jq
```

Пример ответа:

```json
{
  "data": [
    {
      "agreement_id": "agr-f38d911ad4d9",
      "product_name": "Автокредит Smart 11.9%",
      "product_type": "loan",
      "amount": 380000.0,
      "status": "active",
      "start_date": "2025-11-06T19:11:17.849777",
      "end_date": "2028-04-24T19:11:17.847578",
      "account_number": "45560441e630fef44a"
    }
  ],
  "meta": { "total": 2 }
}
```

## Что важно сохранить

* `TEAM_TOKEN_*` — токены каждого банка (валидны 24 часа).
* `VBANK_PRODUCT_AGREEMENT_CONSENT_ID`, `ABANK_PRODUCT_AGREEMENT_CONSENT_ID`, `SBANK_PRODUCT_AGREEMENT_CONSENT_ID` — согласия на выдачу договоров.
* Для SBank требуется клиентский JWT (`SBANK_CLIENT_TOKEN`) и ручное подтверждение согласия.

Эти значения уже добавлены в `OptiFi/.env`. Документ пригодится для замены моковых данных в микросервисе `microservices/credit-analytics-backend/` и автоматизации интеграции с Open Banking.

## Получение счетов и балансов клиентов других банков

Ниже приведён пошаговый сценарий для команды `team018`, позволяющий выгружать **счета** и **балансы** клиента `team018-1` из банков VBank, ABank и SBank. Во всех командах используйте переменные окружения из `.env` (см. раздел «Общие переменные окружения» выше).

> Все команды выполняются в одном терминале (`zsh`). Если команда зависит от результата предыдущей, мы сохраняем данные в переменные окружения через `export`.

### 1. Общие переменные

```bash
export TEAM_CLIENT_ID=team018
export TEAM_CLIENT_SECRET=d78xBRvntBFr6FkxVHLRrfcWXte25QoM
export EXTERNAL_CLIENT_ID=team018-1
# Клиентский JWT для подписания согласий SBank
export SBANK_CLIENT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZWFtMDE4LTEiLCJ0eXBlIjoiY2xpZW50IiwiYmFuayI6InNlbGYiLCJleHAiOjE3NjI1ODcxNzJ9.m_ZW4jNL-23TQETUTQZ9HGSn2rVFPB48mYXh2hjWp1Y
```

### 2. VBank — счета и балансы

```bash
# 2.1 Токен банка (валиден 24 часа)
export TEAM_TOKEN_VBANK=$(curl -sS -X POST "https://vbank.open.bankingapi.ru/auth/bank-token" \
  --data-urlencode "client_id=$TEAM_CLIENT_ID" \
  --data-urlencode "client_secret=$TEAM_CLIENT_SECRET" \
  | jq -r '.access_token')

# 2.2 Согласие на доступ к счетам
export VBANK_ACCOUNT_CONSENT_ID=$(curl -sS -X POST "https://vbank.open.bankingapi.ru/account-consents/request" \
  -H "Authorization: Bearer $TEAM_TOKEN_VBANK" \
  -H "Content-Type: application/json" \
  -d '{
        "requesting_bank": "'$TEAM_CLIENT_ID'",
        "client_id": "'$EXTERNAL_CLIENT_ID'",
        "permissions": ["ReadAccountsDetail","ReadBalances"],
        "reason": "Агрегатор OptiFi"
      }' | jq -r '.consent_id')

# 2.3 Список счетов клиента
VBANK_ACCOUNTS=$(curl -sS -X GET "https://vbank.open.bankingapi.ru/accounts" \
  -G --data-urlencode "client_id=$EXTERNAL_CLIENT_ID" \
  -H "Authorization: Bearer $TEAM_TOKEN_VBANK" \
  -H "X-Requesting-Bank: $TEAM_CLIENT_ID" \
  -H "X-Consent-Id: $VBANK_ACCOUNT_CONSENT_ID" \
  -H "Accept: application/json")
echo "$VBANK_ACCOUNTS" | jq

# 2.4 Балансы по каждому счету
for ACCOUNT_ID in $(echo "$VBANK_ACCOUNTS" | jq -r '.data.account[].accountId'); do
  curl -sS -X GET "https://vbank.open.bankingapi.ru/accounts/$ACCOUNT_ID/balances" \
    -G --data-urlencode "client_id=$EXTERNAL_CLIENT_ID" \
    -H "Authorization: Bearer $TEAM_TOKEN_VBANK" \
    -H "X-Requesting-Bank: $TEAM_CLIENT_ID" \
    -H "X-Consent-Id: $VBANK_ACCOUNT_CONSENT_ID" \
    -H "Accept: application/json" | jq
  echo
done
```

### 3. ABank — счета и балансы

```bash
# 3.1 Токен банка
export TEAM_TOKEN_ABANK=$(curl -sS -X POST "https://abank.open.bankingapi.ru/auth/bank-token" \
  --data-urlencode "client_id=$TEAM_CLIENT_ID" \
  --data-urlencode "client_secret=$TEAM_CLIENT_SECRET" \
  | jq -r '.access_token')

# 3.2 Согласие (автоодобрение)
export ABANK_ACCOUNT_CONSENT_ID=$(curl -sS -X POST "https://abank.open.bankingapi.ru/account-consents/request" \
  -H "Authorization: Bearer $TEAM_TOKEN_ABANK" \
  -H "Content-Type: application/json" \
  -d '{
        "requesting_bank": "'$TEAM_CLIENT_ID'",
        "client_id": "'$EXTERNAL_CLIENT_ID'",
        "permissions": ["ReadAccountsDetail","ReadBalances"],
        "reason": "Агрегатор OptiFi"
      }' | jq -r '.consent_id')

# 3.3 Список счетов
ABANK_ACCOUNTS=$(curl -sS -X GET "https://abank.open.bankingapi.ru/accounts" \
  -G --data-urlencode "client_id=$EXTERNAL_CLIENT_ID" \
  -H "Authorization: Bearer $TEAM_TOKEN_ABANK" \
  -H "X-Requesting-Bank: $TEAM_CLIENT_ID" \
  -H "X-Consent-Id: $ABANK_ACCOUNT_CONSENT_ID" \
  -H "Accept: application/json")
echo "$ABANK_ACCOUNTS" | jq

# 3.4 Балансы
for ACCOUNT_ID in $(echo "$ABANK_ACCOUNTS" | jq -r '.data.account[].accountId'); do
  curl -sS -X GET "https://abank.open.bankingapi.ru/accounts/$ACCOUNT_ID/balances" \
    -G --data-urlencode "client_id=$EXTERNAL_CLIENT_ID" \
    -H "Authorization: Bearer $TEAM_TOKEN_ABANK" \
    -H "X-Requesting-Bank: $TEAM_CLIENT_ID" \
    -H "X-Consent-Id: $ABANK_ACCOUNT_CONSENT_ID" \
    -H "Accept: application/json" | jq
  echo
done
```

### 4. SBank — счета и балансы

У SBank согласие **подписывается клиентом**. Необходим `SBANK_CLIENT_TOKEN` (см. Общие переменные).

```bash
# 4.1 Токен банка
export TEAM_TOKEN_SBANK=$(curl -sS -X POST "https://sbank.open.bankingapi.ru/auth/bank-token" \
  --data-urlencode "client_id=$TEAM_CLIENT_ID" \
  --data-urlencode "client_secret=$TEAM_CLIENT_SECRET" \
  | jq -r '.access_token')

# 4.2 Запрос согласия (возвращает request_id, consent_id может отсутствовать)
SBANK_CONSENT_RESPONSE=$(curl -sS -X POST "https://sbank.open.bankingapi.ru/account-consents/request" \
  -H "Authorization: Bearer $TEAM_TOKEN_SBANK" \
  -H "Content-Type: application/json" \
  -d '{
        "requesting_bank": "'$TEAM_CLIENT_ID'",
        "client_id": "'$EXTERNAL_CLIENT_ID'",
        "permissions": ["ReadAccountsDetail","ReadBalances"],
        "reason": "Агрегатор OptiFi"
      }')
export SBANK_CONSENT_REQUEST_ID=$(echo "$SBANK_CONSENT_RESPONSE" | jq -r '.request_id')

# 4.3 Подписать согласие от имени клиента
SBANK_SIGN_RESPONSE=$(curl -sS -X POST "https://sbank.open.bankingapi.ru/account-consents/sign" \
  -H "Authorization: Bearer $SBANK_CLIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "request_id": "'$SBANK_CONSENT_REQUEST_ID'",
        "action": "approve",
        "signature": "password"
      }')

# 4.4 Если consent_id не пришёл напрямую, запросите статус
if [ "$(echo "$SBANK_SIGN_RESPONSE" | jq -r '.consent_id // empty')" ]; then
  export SBANK_ACCOUNT_CONSENT_ID=$(echo "$SBANK_SIGN_RESPONSE" | jq -r '.consent_id')
else
  curl -sS "https://sbank.open.bankingapi.ru/account-consents/$SBANK_CONSENT_REQUEST_ID" \
    -o /tmp/sbank_consent_status.json
  export SBANK_ACCOUNT_CONSENT_ID=$(jq -r '.data.consentId' /tmp/sbank_consent_status.json)
fi
echo "SBank consent_id = $SBANK_ACCOUNT_CONSENT_ID"

# 4.5 Список счетов
SBANK_ACCOUNTS=$(curl -sS -X GET "https://sbank.open.bankingapi.ru/accounts" \
  -G --data-urlencode "client_id=$EXTERNAL_CLIENT_ID" \
  -H "Authorization: Bearer $TEAM_TOKEN_SBANK" \
  -H "X-Requesting-Bank: $TEAM_CLIENT_ID" \
  -H "X-Consent-Id: $SBANK_ACCOUNT_CONSENT_ID" \
  -H "Accept: application/json")
echo "$SBANK_ACCOUNTS" | jq

# 4.6 Балансы
for ACCOUNT_ID in $(echo "$SBANK_ACCOUNTS" | jq -r '.data.account[].accountId'); do
  curl -sS -X GET "https://sbank.open.bankingapi.ru/accounts/$ACCOUNT_ID/balances" \
    -G --data-urlencode "client_id=$EXTERNAL_CLIENT_ID" \
    -H "Authorization: Bearer $TEAM_TOKEN_SBANK" \
    -H "X-Requesting-Bank: $TEAM_CLIENT_ID" \
    -H "X-Consent-Id: $SBANK_ACCOUNT_CONSENT_ID" \
    -H "Accept: application/json" | jq
  echo
done
```

### 5. Полезные заметки

* __Переменные окружения__ сохраняются в рамках текущей сессии терминала. При новом запуске терминала повторите шаг 1.
* __Срок действия токенов__ — 24 часа. При ответе `401 Unauthorized` перезапросите токен у соответствующего банка.
* __Сообщение `CONSENT_REQUIRED`__ означает, что `X-Consent-Id` пустой/устарел. Запросите новое согласие и подставьте свежий `consent_id`.
* __Клиентский JWT__ (`SBANK_CLIENT_TOKEN`) хранится в `.env` и используется только для подписания согласий в SBank.
* Все JSON-ответы удобно форматировать через `jq`, чтобы быстрее проверять содержимое.
