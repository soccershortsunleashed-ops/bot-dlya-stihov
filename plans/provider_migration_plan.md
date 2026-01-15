# Технический план: Миграция конфигурации провайдеров по типам этапов (StageType)

Этот план описывает переход от глобальной конфигурации провайдеров к конфигурации, привязанной к конкретным типам этапов (`POEM`, `VOICE`, `SONG`, `CLIP`).

## 1. Изменения в базе данных

### 1.1. Модель `ProviderConfig`
Необходимо обновить модель [`ProviderConfig`](app/infra/db/models.py:93) (или создать новую миграцию для изменения текущей), чтобы она хранила настройки для каждого `StageType`.

**Структура таблицы `provider_configs`:**
- `stage_type`: `String` (на базе `StageType`) — **UNIQUE**, Primary Key.
- `provider_kind`: `String` (на базе `ProviderKind`) — выбранный провайдер.
- `api_key_encrypted`: `String` — зашифрованный API-ключ.
- `model`: `String` — идентификатор выбранной модели.
- `models_cache`: `JSON` — список строк (доступные модели от провайдера).
- `models_cache_updated_at`: `DateTime` — время последнего обновления кэша.
- `status`: `String` (`active`, `invalid`, `error`) — статус конфигурации.
- `updated_at`: `DateTime` — время последнего изменения конфига.

### 1.2. Таблица `api_keys`
- Сохраняется для ведения истории всех когда-либо введенных ключей.
- При сохранении нового ключа в `provider_configs`, он также должен добавляться в `api_keys` с пометкой провайдера.

## 2. Шифрование API-ключей

- **Библиотека:** `cryptography.fernet`.
- **Ключ шифрования:** Генерируется на основе [`ADMIN_SECRET_KEY`](app/infra/config/settings.py:42).
- **Место реализации:** `app/infra/utils/crypto.py`.
- **Методы:** `encrypt_key(plain_text: str) -> str`, `decrypt_key(encrypted_text: str) -> str`.

## 3. Матрица разрешенных провайдеров

В коде (например, в `app/domain/constants.py`) определяется маппинг:
- `StageType.POEM` -> `[ProviderKind.YANDEX_GPT, ProviderKind.GEMINI, ProviderKind.OPENAI]`
- `StageType.VOICE` -> `[ProviderKind.SPEECHKIT]`
- `StageType.SONG` -> `[ProviderKind.SUNO]`
- `StageType.CLIP` -> `[ProviderKind.PIKA]`

## 4. Обновление AI Провайдеров

В базовый класс провайдеров [`BaseAIProvider`](app/infra/ai/base.py) (если он есть) или в каждый конкретный провайдер добавить:
- Метод `list_models() -> List[str]`:
    - Для Gemini: использование `genai.list_models()`.
    - Для YandexGPT: статический список или запрос к API (если доступно).
    - Для OpenAI: запрос к `/v1/models`.

## 5. Логика работы с кэшем моделей

### 5.1. Автоматическое обновление (Celery Beat)
- Задача `sync_provider_models_task` запускается каждые 24 часа.
- Итерирует по всем записям в `provider_configs`.
- Если ключ есть, вызывает `list_models()` у соответствующего провайдера.
- Обновляет `models_cache` и `models_cache_updated_at`.

### 5.2. Обработка исчезновения моделей
- Если текущая выбранная `model` отсутствует в новом `models_cache`:
    1. Автоматически установить `model = models_cache[0]`.
    2. Изменить `status` на `active` (или `warning`).
    3. Залогировать событие для уведомления администратора.

### 5.3. Обновление при сохранении
- При вызове `POST /admin/providers/update` после сохранения ключа немедленно вызывается обновление кэша для этого `StageType`.

## 6. Интеграция в существующий код

### 6.1. Репозиторий `ConfigRepo`
Добавить метод `get_active_config(stage_type: StageType)`:
1. Ищет запись в `provider_configs` по `stage_type`.
2. Дешифрует API-ключ.
3. Возвращает объект/словарь с `provider_kind`, `api_key` и `model`.
4. Если записи нет — возвращает `fallback` из `settings.py`.

### 6.2. Celery Tasks
В файле [`app/infra/queue/tasks.py`](app/infra/queue/tasks.py) заменить получение провайдеров:
```python
# Было:
provider = GeminiProvider(api_key=settings.GEMINI_API_KEY.get_secret_value())

# Стало:
cfg = await config_repo.get_active_config(StageType.POEM)
provider = ProviderFactory.create(cfg.provider_kind, api_key=cfg.api_key)
# ... использование cfg.model при генерации ...
```

## 7. Изменения в UI (Админка)

1.  **Маршрут GET `/admin/providers`**:
    - Передает в шаблон список конфигов для всех 4 `StageType`.
2.  **Шаблон `providers.html`**:
    - Разделение на 4 секции (карточки или табы).
    - Каждая секция — отдельная форма.
    - `select` для выбора модели заполняется из `models_cache` соответствующего конфига.
3.  **Маршрут POST `/admin/providers/update`**:
    - Принимает `stage_type`, `provider_kind`, `api_key` (опционально), `model`.
    - Выполняет шифрование и обновление БД.

## 8. План миграции данных
1. Создать новую таблицу/поля.
2. Скрипт миграции: перенести текущие значения из `settings.py` (если они заданы в `.env`) в базу данных как начальные значения для соответствующих `StageType`.
