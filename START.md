# Быстрый запуск

## 1. Получи токен Replicate
https://replicate.com/account → API tokens → создай токен

## 2. Настрой .env
```bash
cp .env.example .env
# Вставь REPLICATE_API_TOKEN=r8_твой_токен
```

## 3. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

## 4. Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 5. Docker (опционально)
```bash
cp .env.example .env     # заполни токен
docker-compose up --build
# backend → :8000
# frontend → :5173
```

## Стоимость на Replicate (примерно)
| Модель | Время | Цена |
|--------|-------|------|
| InstantID + SDXL | ~15 сек | ~$0.025 |
| CodeFormer | ~3 сек | ~$0.003 |
| Real-ESRGAN | ~2 сек | ~$0.002 |
| **Итого за 1 стиль (2 фото)** | ~20 сек | **~$0.06** |
| **За 5 стилей (10 фото)** | ~2 мин | **~$0.30** |
