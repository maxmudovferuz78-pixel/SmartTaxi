# SmartTaxi Frontend

Tailwind CSS + Vanilla JS yordamida yozilgan SmartTaxi frontend loyihasi.

---

## 📁 Papka strukturasi

```
smarttaxi/
├── templates/
│   ├── shared/
│   │   └── base.html            # Asosiy layout (barcha sahifalar shu faylni extend qiladi)
│   ├── auth/
│   │   └── login.html           # OTP login sahifasi
│   ├── driver/
│   │   ├── dashboard.html       # Haydovchi bosh sahifasi
│   │   ├── orders.html          # Haydovchi buyurtmalari
│   │   ├── wallet.html          # Hamyon va tranzaksiyalar
│   │   └── profile.html         # Profil va mashina tahrirlash
│   ├── passenger/
│   │   ├── dashboard.html       # Yo'lovchi bosh sahifasi (buyurtma berish)
│   │   ├── orders.html          # Buyurtmalar tarixi
│   │   └── profile.html         # Profil tahrirlash
│   └── admin/
│       ├── dashboard.html       # Admin statistika
│       ├── drivers.html         # Haydovchilar boshqaruvi
│       ├── orders.html          # Buyurtmalar + haydovchi biriktirish
│       └── tariffs.html         # Tarif boshqaruvi
├── static/
│   ├── css/
│   │   └── main.css             # Global stillar
│   └── js/
│       └── api/
│           ├── client.js        # HTTP client, token refresh, toast
│           ├── auth.js          # Auth API (/api/auth/)
│           ├── drivers.js       # Drivers API (/api/drivers/)
│           ├── orders.js        # Orders + Tariffs API
│           └── wallet.js        # Wallet API
├── views.py                     # Django views (template render)
└── urls.py                      # URL yo'nalishlari
```

---

## ⚙️ Django ga ulash

### 1. settings.py

```python
# INSTALLED_APPS ga frontend ilovangizni qo'shing (agar alohida app bo'lsa)
INSTALLED_APPS = [
    ...
    'frontend',   # yoki loyiha nomingiz
]

# Templates yo'lini sozlang
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # ← shu qator
        'APP_DIRS': True,
        ...
    },
]

# Static fayllar
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']   # ← shu qator
```

### 2. urls.py (asosiy)

```python
# your_project/urls.py
from django.urls import path, include

urlpatterns = [
    path('',     include('frontend.urls')),   # frontend URL lar
    path('api/', include('your_api.urls')),   # backend API
    # path('django-admin/', admin.site.urls), # agar kerak bo'lsa
]
```

### 3. CORS sozlash (frontend ↔ backend)

```bash
pip install django-cors-headers
```

```python
# settings.py
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # ← eng yuqorida bo'lishi kerak
    ...
]

CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# yoki development uchun:
CORS_ALLOW_ALL_ORIGINS = True   # Faqat dev muhitda!
```

---

## 🔗 API Base URL ni o'zgartirish

`static/js/api/client.js` faylining 1-satrida:

```js
const API_BASE = 'http://localhost:8000';  // ← o'zingizning URL
```

Production uchun:

```js
const API_BASE = 'https://api.smarttaxi.uz';
```

---

## 🔐 Autentifikatsiya oqimi

```
1. /auth/login/   → Telefon kiriting
2. OTP yuboriladi → 6 xonali kod kiriting
3. Token olinadi  → localStorage ga saqlanadi
4. /api/auth/me/  → Role aniqlanadi
5. Role bo'yicha yo'naltirish:
   - admin/operator → /admin-panel/
   - driver         → /driver/
   - client         → /passenger/
```

---

## 🚀 Ishga tushirish

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Paketlar
pip install django djangorestframework django-cors-headers

# Migrate va run
python manage.py migrate
python manage.py runserver
```

Brauzerda: `http://localhost:8000/auth/login/`

---

## 📱 Sahifalar va URL lar

| Sahifa               | URL                      | Kim uchun          |
|---------------------|--------------------------|--------------------|
| Login               | `/auth/login/`           | Barchasi           |
| Driver Dashboard    | `/driver/`               | Haydovchi          |
| Driver Orders       | `/driver/orders/`        | Haydovchi          |
| Driver Wallet       | `/driver/wallet/`        | Haydovchi          |
| Driver Profile      | `/driver/profile/`       | Haydovchi          |
| Passenger Dashboard | `/passenger/`            | Yo'lovchi          |
| Passenger Orders    | `/passenger/orders/`     | Yo'lovchi          |
| Passenger Profile   | `/passenger/profile/`    | Yo'lovchi          |
| Admin Dashboard     | `/admin-panel/`          | Admin / Operator   |
| Admin Drivers       | `/admin-panel/drivers/`  | Admin / Operator   |
| Admin Orders        | `/admin-panel/orders/`   | Admin / Operator   |
| Admin Tariffs       | `/admin-panel/tariffs/`  | Faqat Admin        |

---

## ⚠️ Muhim eslatmalar

- **Tokenlar** `localStorage` da saqlanadi (`access_token`, `refresh_token`, `user_role`)
- **Token muddati tugasa** — avtomatik refresh qilinadi, muvaffaqiyatsiz bo'lsa login sahifasiga yo'naltiriladi
- **Route guard** — har bir sahifada `requireAuth(['role'])` tekshiruvi bor
- **Buyurtma polling** — yo'lovchi buyurtma bergandan keyin har 5 soniyada status tekshiriladi
- **Toast xabarlari** — API xatolari ekranda ko'rsatiladi
