# Telegram-бот-помощник на Haystack + Docling + Pinecone

Telegram-бот с умным персональным ассистентом на **Haystack 3.x**. Агент сам
решает, когда искать в векторной базе Pinecone, когда изучать присланную ссылку
или **документ (PDF, DOCX, PPTX, XLSX и др.)**, когда запоминать личные факты о
пользователе, когда достать факт/фото собаки или погоду — а когда просто ответить.

Ключевые особенности этой версии:

- **модульная архитектура** (`app/` разбит по слоям: vectorstore, ingestion,
  generation, agent, bot);
- **два настоящих Haystack-пайплайна**: `ingestion_pipeline` (Docling →
  эмбеддер → Pinecone) и `generation_pipeline` (retriever → prompt → LLM);
- полноценная **обработка файлов через Docling** с сохранением структурного
  контента в **Pinecone** и **автоматическим резюме в одно предложение**;
- сохранён **весь функционал** прежней версии бота.

## Возможности

- **Обработка файлов** (PDF, DOCX, PPTX, XLSX, HTML, MD, CSV, изображения):
  файл скачивается, разбирается Docling на чанки, чанки с эмбеддингами и
  метаданными (`file_name`, `page_number`, `split_id`) сохраняются в Pinecone,
  после чего бот присылает краткое резюме **ровно одним предложением**.
- **`search_knowledge_base`** — семантический поиск по базе знаний (включая
  загруженные файлы), личной памяти пользователя и прошлым диалогам.
- **`process_url_and_save`** — парсинг URL (BeautifulSoup), разбиение на чанки и
  сохранение в Pinecone.
- **`get_random_cat_fact`** — случайный факт о котиках с catfact.ninja.
- **`get_random_dog_fact`** — случайный факт о собаках с dogapi.dog.
- **`get_random_dog_image`** — случайное фото собаки с dog.ceo: фото
  анализируется LLM (vision), бот определяет породу и рассказывает о ней.
- **`get_weather`** — погода по названию города через Open-Meteo (без ключа).
- **`save_user_memory`** — сохранение важных личных фактов с косинусным дедупом.
- **Контекст диалога в Pinecone**: бот сохраняет тексты сообщений пользователя
  (не свои ответы) с дедупом; каждый запрос учитывает этот контекст.
- История переписки по чатам, статусы («Думаю…/Читаю статью…»), понятные ошибки.

## Архитектура

```
Пользователь
   │
   ├── текст ─► bot.handlers.text
   │              ├─ сохранить текст в Pinecone (dialog_context, косинусный дедуп)
   │              └─ Haystack Agent (agent.runner)
   │                    ├─ контекст из памяти (user_memories + dialog_context)
   │                    └─ инструменты (agent.tools): поиск, URL, факты, фото, погода, память
   │
   └── файл ─► bot.handlers.documents
                  ├─ ответ «Файл получен…»
                  ├─ скачать файл (bot.files)
                  ├─ ingestion_pipeline: DoclingConverter → OpenAIDocumentEmbedder → PineconeWriter
                  ├─ ответ «Готово…»
                  └─ generation.one_sentence_summary → одно предложение-резюме
```

Два пайплайна Haystack лежат в основе:

- **`ingestion_pipeline`** (`app/ingestion/pipeline.py`):
  `DoclingConverter` (режим `DOC_CHUNKS`) → `OpenAIDocumentEmbedder` →
  `PineconeWriter` (custom-компонент, пишет в namespace `knowledge`).
- **`generation_pipeline`** (`app/generation/pipeline.py`):
  `OpenAITextEmbedder` → `PineconeEmbeddingRetriever` → `PromptBuilder` →
  `OpenAIChatGenerator`.

## Структура проекта

```
.
├── app/
│   ├── config.py                 # .env + Settings + get_settings()
│   ├── logging_setup.py          # configure_logging()
│   ├── constants.py              # лимиты, маркеры, User-Agent
│   ├── messages.py               # служебные тексты + is_service_text()
│   ├── llm.py                     # фабрики LLM/эмбеддеров (кэш)
│   ├── vectorstore/
│   │   ├── store.py              # VectorStore: клиент + сторы по namespace
│   │   ├── dedupe.py             # косинусное сходство + DedupePolicy
│   │   ├── search.py             # DocumentRepository: запись/поиск/память
│   │   └── writer.py             # PineconeWriter (сток ingestion-пайплайна)
│   ├── ingestion/
│   │   ├── converter.py          # фабрика DoclingConverter + прогрев
│   │   ├── metadata.py           # метаданные чанков (file_name, page_number)
│   │   ├── pipeline.py           # ingestion_pipeline
│   │   └── service.py            # IngestionService (файлы и тексты)
│   ├── generation/
│   │   ├── pipeline.py           # generation_pipeline
│   │   └── service.py            # answer() + one_sentence_summary()
│   ├── agent/
│   │   ├── prompt.py             # системный промпт
│   │   ├── runner.py             # Haystack Agent + история диалога
│   │   └── tools/                # инструменты (по модулю на инструмент)
│   └── bot/
│       ├── app.py                # create_bot()
│       ├── formatting.py         # имя пользователя, безопасная отправка
│       ├── files.py              # скачивание файлов из Telegram
│       └── handlers/             # commands / text / documents
├── main.py                       # запуск бота
├── cli.py                        # служебная CLI (проверка/очистка/прогрев)
├── requirements.txt
├── .env.example
└── .gitignore
```

## Настройка

### 1. Python

Нужен Python 3.11+ (проверено на 3.13).

### 2. Виртуальное окружение

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Внимание:** `docling` тянет `torch` и `transformers` — установка тяжёлая
> (несколько ГБ). Модели разметки/таблиц Docling докачиваются в кэш Hugging Face
> при первом разборе файла (либо заранее — командой `python cli.py --warm-docling`).

### 3. Переменные окружения

`.env` не хранится в git (см. `.gitignore`). Скопируйте `.env.example` в `.env`
и заполните значения:

```bash
copy .env.example .env     # Windows
cp .env.example .env       # macOS/Linux
```

| Переменная            | Обязательна | Описание                                                      |
|-----------------------|-------------|---------------------------------------------------------------|
| `TELEGRAM_TOKEN`      | да          | токен бота от [@BotFather](https://t.me/BotFather)            |
| `PINECONE_API_KEY`    | да          | ключ Pinecone (Console → API Keys)                            |
| `PINECONE_INDEX_NAME` | да          | имя индекса (создаётся автоматически, если нет)               |
| `OPENAI_API_KEY`      | да          | ключ OpenAI-совместимого провайдера (например, ProxyAPI)      |
| `OPENAI_BASE_URL`     | нет         | базовый URL API провайдера                                    |
| `OPENAI_MODEL`        | нет         | модель чата; для ProxyAPI — с префиксом `openai/gpt-4o-mini`  |
| `EMBEDDING_MODEL`     | нет         | модель эмбеддингов (`openai/text-embedding-3-small`)          |
| `EMBEDDING_DIM`       | нет         | размерность эмбеддингов (`1536`)                              |
| `MAX_FILE_SIZE_MB`    | нет         | лимит размера файла, МБ (`20`)                                |
| `SUMMARY_MAX_SENTENCES` | нет       | предложений в резюме (`1`)                                     |
| `DOCLING_EXPORT_TYPE` | нет         | `doc_chunks` (по умолчанию) или `markdown`                    |
| `COSINE_SIMILARITY_THRESHOLD` | нет | порог дедупа (`0.75`)                                        |
| `DUPLICATE_ACTION`    | нет         | действие при дубликате: `update` или `skip`                   |
| `DEDUPE_ENABLED`      | нет         | общий выключатель дедупа (`true`)                             |

> **ProxyAPI:** имена моделей указываются С префиксом провайдера
> (`openai/gpt-4o-mini`, `openai/text-embedding-3-small`) — код передаёт их в API
> как есть.

### 4. Проверка подключения и обслуживание

```bash
python cli.py                  # подключение + статистика индекса
python cli.py --warm-docling   # прогреть Docling и скачать модели заранее
python cli.py --reset-memory   # очистить namespace личной памяти
python cli.py --reset-dialog   # очистить namespace контекста диалогов
python cli.py --delete-index   # удалить индекс Pinecone целиком
```

### 5. Запуск бота

```bash
python main.py
```

## Использование

- `/start` — приветствие и справка;
- `/help` — справка по возможностям;
- `/reset` — очистить историю диалога;
- **прислать файл** — бот разберёт его, сохранит в базу и пришлёт резюме;
- «Изучи эту статью и запомни: `<URL>`» — распарсит страницу и сохранит её;
- «Что ты знаешь о …?» — поиск по базе знаний, памяти и прошлым диалогам;
- «Я живу в Питере» — факт сохранится в память пользователя;
- «Расскажи факт о котиках» / «Расскажи факт о собаке» — случайные факты;
- «Покажи фото собаки» — фото + определение породы;
- «Какая погода в Москве?» — текущая погода.

### Обработка файла: пошагово

1. Пользователь присылает документ.
2. Бот отвечает: «📥 Файл получен. Запускаю анализ и сохранение…».
3. Файл скачивается в память; при превышении `MAX_FILE_SIZE_MB` — понятная ошибка.
4. `IngestionService.ingest_bytes` гонит файл через `ingestion_pipeline`.
5. Чанки сохраняются в Pinecone (namespace `knowledge`) с метаданными
   `file_name`, `page_number`, `split_id`, `source_type="file"`, `uploaded_by`.
6. Бот отвечает: «✅ Готово. Я изучил этот файл, теперь можем его обсудить.» и
   присылает резюме **ровно одним предложением**.

Дальше содержимое файла доступно агентy через `search_knowledge_base`.

## Умная память (косинусное сходство)

Перед записью в долговременную память (личные факты, сообщения пользователя)
считается косинусное сходство между текущим текстом и уже сохранёнными:

- `similarity < COSINE_SIMILARITY_THRESHOLD` — новая информация → `created`;
- `similarity >= COSINE_SIMILARITY_THRESHOLD` — дубликат → `DUPLICATE_ACTION`
  (`update` — перезапись слота, `skip` — пропуск).

Порог и действие задаются переменными окружения (`COSINE_SIMILARITY_THRESHOLD`,
`DUPLICATE_ACTION`, `DEDUPE_ENABLED`) или значениями по умолчанию в
`app/config.py`.

## Примечания

- История переписки хранится в памяти процесса (сбрасывается при рестарте);
  личные факты и контекст диалогов — в Pinecone и переживают рестарт.
- В Pinecone попадают тексты сообщений пользователя (`dialog_context`), изученные
  статьи и **загруженные файлы** (`knowledge`), личные факты (`user_memories`).
  Служебные ответы бота и статусы не сохраняются (`is_service_text`).
- Telegram `getFile` отдаёт файлы размером примерно до 20 МБ; для больших файлов
  нужен собственный Bot API server — бот сообщит об ограничении.
- Все инструменты перехватывают сетевые и БД-ошибки и возвращают понятный текст.
- Бесплатные API: catfact.ninja, dogapi.dog, dog.ceo, Open-Meteo — ключей не требуют.
