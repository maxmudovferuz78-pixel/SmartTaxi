# SmartTaxi — Premium Frontend (v2)

Qora-oltin (jet black + amber gold) uslubidagi premium taxi platforma dizayni.

## O'rnatish

1. Bu papkani (`smarttaxi2` ichidagi hammasini) loyihangizdagi `smarttaxi` papkaga **almashtirib** ko'chiring (eski fayllar ustidan yozadi).

2. `__init__.py` borligini tekshiring (Django app sifatida tanish uchun majburiy).

3. `static/js/api/client.js` da backend URL ni tekshiring:
```js
const API_BASE = 'http://localhost:8000';
```

4. `settings.py`:
```python
TEMPLATES = [{ 'DIRS': [BASE_DIR / 'smarttaxi' / 'templates'], 'APP_DIRS': True, ... }]
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'smarttaxi' / 'static']
```

5. Asosiy `urls.py`:
```python
path('', include('smarttaxi.urls')),
```

6. Docker bo'lsa:
```bash
docker-compose restart
```

## URL lar
- `/auth/login/` — Kirish
- `/driver/`, `/driver/orders/`, `/driver/wallet/`, `/driver/profile/`
- `/passenger/`, `/passenger/orders/`, `/passenger/profile/`
- `/admin-panel/`, `/admin-panel/drivers/`, `/admin-panel/orders/`, `/admin-panel/tariffs/`

## Dizayn
- Fon: Jet black (#080810)
- Asosiy rang: Amber gold (#F5A623)
- Shrift: Syne (sarlavhalar) + Inter (matn)
- Animatsiyalar: pulse (online indikator), road-lines (login fon), modal/toast transitions
