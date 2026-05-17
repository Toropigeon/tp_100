# TP-100 Diagnostics Analyzer

Приложение анализирует CSV-диагностику котла ТП-100, строит графики на backend, классифицирует параметры пороговым методом и генерирует текстовый отчет через mock-LLM или удаленную бесплатную LLM через OpenRouter.

## Структура

- `backend/` - FastAPI API, обработка CSV, графики, RAG и генерация отчета.
- `frontend/` - Flutter-клиент для загрузки CSV, просмотра графиков и отчета.
- `docker-compose.yml` - сборка backend.

## Быстрый запуск backend

```bash
cp .env.example .env
docker compose up --build
```

API будет доступен на `http://localhost:8000`.

## Flutter

```bash
cd frontend
flutter pub get
flutter run
```

Для Android-эмулятора backend URL по умолчанию `http://10.0.2.2:8000`, для desktop/web можно поменять `apiBaseUrl` в `frontend/lib/main.dart` на `http://localhost:8000`.

## CSV

CSV должен содержать числовые колонки диагностических параметров. Колонка времени может называться `timestamp`, `time`, `datetime`, `date`, `время` или `дата`.

Пример находится в `backend/sample_data/tp100_sample.csv`.
