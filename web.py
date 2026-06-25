from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return PAGE_HOME, 200


@app.route("/b2b")
def b2b():
    return PAGE_B2B, 200


PAGE_HOME = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ExpatRentBot — AI-помощник по аренде в Европе</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;line-height:1.6}
.hero{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px 20px;background:linear-gradient(135deg,#0a0a0a 0%,#1a1a2e 50%,#16213e 100%)}
.hero h1{font-size:clamp(2rem,5vw,3.5rem);font-weight:800;margin-bottom:16px;background:linear-gradient(135deg,#00d2ff,#3a7bd5);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:clamp(1rem,2.5vw,1.3rem);color:#a0a0a0;max-width:600px;margin-bottom:32px}
.btn{display:inline-block;padding:16px 40px;border-radius:12px;text-decoration:none;font-weight:700;font-size:1.1rem;transition:all .3s}
.btn-primary{background:linear-gradient(135deg,#00d2ff,#3a7bd5);color:#fff}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,210,255,.3)}
.btn-secondary{background:transparent;border:2px solid #3a7bd5;color:#3a7bd5;margin-top:16px}
.btn-secondary:hover{background:#3a7bd5;color:#fff}
.features{padding:80px 20px;max-width:1000px;margin:0 auto}
.features h2{text-align:center;font-size:2rem;margin-bottom:48px;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:32px}
.card{background:#1a1a2e;border-radius:16px;padding:32px;border:1px solid #2a2a4a;transition:transform .3s}
.card:hover{transform:translateY(-4px)}
.card .icon{font-size:2.5rem;margin-bottom:16px}
.card h3{font-size:1.3rem;margin-bottom:12px;color:#fff}
.card p{color:#a0a0a0;font-size:.95rem}
.pricing{padding:80px 20px;background:#111;text-align:center}
.pricing h2{font-size:2rem;margin-bottom:48px;color:#fff}
.price-cards{display:flex;justify-content:center;gap:24px;flex-wrap:wrap;max-width:900px;margin:0 auto}
.price-card{background:#1a1a2e;border-radius:16px;padding:32px;width:260px;border:1px solid #2a2a4a}
.price-card.featured{border-color:#3a7bd5;position:relative}
.price-card.featured::before{content:"ХИТ";position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#3a7bd5;color:#fff;padding:4px 16px;border-radius:20px;font-size:.8rem;font-weight:700}
.price-card h3{font-size:1.2rem;margin-bottom:8px;color:#fff}
.price-card .price{font-size:2.5rem;font-weight:800;color:#00d2ff;margin-bottom:8px}
.price-card .period{color:#666;font-size:.9rem;margin-bottom:20px}
.price-card ul{list-style:none;text-align:left;margin-bottom:24px}
.price-card ul li{padding:8px 0;border-bottom:1px solid #2a2a4a;color:#a0a0a0}
.price-card ul li::before{content:"\\2713 ";color:#00d2ff}
.cta{padding:80px 20px;text-align:center;background:linear-gradient(135deg,#1a1a2e,#16213e)}
.cta h2{font-size:2rem;margin-bottom:16px;color:#fff}
.cta p{color:#a0a0a0;margin-bottom:32px;font-size:1.1rem}
footer{text-align:center;padding:32px;color:#444;font-size:.85rem}
</style>
</head>
<body>
<div class="hero">
<h1>AI-помощник по аренде<br>в Европе</h1>
<p>Анализирую объявления, нахожу скрытые платежи, проверяю документы и выявляю мошенников за секунды</p>
<a href="https://t.me/expat_rent_bot" class="btn btn-primary">Открыть бота в Telegram</a>
<a href="/b2b" class="btn btn-secondary">Для агентств →</a>
</div>
<div class="features">
<h2>Что я умею</h2>
<div class="grid">
<div class="card"><div class="icon">🔗</div><h3>Анализ ссылок</h3><p>Отправьте ссылку с ImmoScout24, Rightmove, Idealista — я сам открою и проанализирую</p></div>
<div class="card"><div class="icon">📸</div><h3>Распознавание фото</h3><p>Скиньте скриншот или фото объявления — я распознаю текст и проанализирую</p></div>
<div class="card"><div class="icon">🔍</div><h3>Скрытые платежи</h3><p>Нахожу Nebenkosten, Service Charge, залог и другие скрытые расходы</p></div>
<div class="card"><div class="icon">⚠️</div><h3>Проверка на мошенников</h3><p>Выявляю подозрительные объявления и типичные схемы обмана</p></div>
<div class="card"><div class="icon">📋</div><h3>Документы</h3><p>Говорю, какие документы нужны именно в этой стране</p></div>
<div class="card"><div class="icon">🌍</div><h3>5 языков</h3><p>Русский, украинский, английский, немецкий, польский — бот подстраивается под вас</p></div>
</div>
</div>
<div class="pricing">
<h2>Тарифы для частных лиц</h2>
<div class="price-cards">
<div class="price-card"><h3>Разовый</h3><div class="price">3€</div><div class="period">1 проверка</div><ul><li>Анализ 1 объявления</li><li>Перевод + разбор</li><li>Оценка рисков</li></ul><a href="https://t.me/expat_rent_bot" class="btn btn-secondary" style="width:100%;text-align:center">Попробовать</a></div>
<div class="price-card featured"><h3>Эконом</h3><div class="price">9€</div><div class="period">5 проверок</div><ul><li>Все функции</li><li>Экономия 40%</li><li>Идеально для поиска</li></ul><a href="https://t.me/expat_rent_bot" class="btn btn-primary" style="width:100%;text-align:center">Купить</a></div>
<div class="price-card"><h3>Профи</h3><div class="price">19€</div><div class="period">Безлимит / месяц</div><ul><li>Безлимитные проверки</li><li>Приоритетная обработка</li><li>Все будущие фичи</li></ul><a href="https://t.me/expat_rent_bot" class="btn btn-secondary" style="width:100%;text-align:center">Выбрать</a></div>
</div>
</div>
<div class="cta">
<h2>Начните искать жильё умнее</h2>
<p>3 бесплатные проверки — без регистрации и карт</p>
<a href="https://t.me/expat_rent_bot" class="btn btn-primary">Открыть бота</a>
</div>
<footer>© 2026 ExpatRentBot · AI-powered rental analysis for expats in Europe</footer>
</body>
</html>"""

PAGE_B2B = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>B2B — AI-помощник для агентств недвижимости | ExpatRentBot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;line-height:1.6}
.hero{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px 20px;background:linear-gradient(135deg,#0a0a0a 0%,#1a1a2e 50%,#16213e 100%)}
.hero h1{font-size:clamp(1.8rem,4vw,3rem);font-weight:800;margin-bottom:16px;background:linear-gradient(135deg,#f7971e,#ffd200);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:clamp(1rem,2.5vw,1.2rem);color:#a0a0a0;max-width:700px;margin-bottom:32px}
.btn{display:inline-block;padding:16px 40px;border-radius:12px;text-decoration:none;font-weight:700;font-size:1.1rem;transition:all .3s}
.btn-primary{background:linear-gradient(135deg,#f7971e,#ffd200);color:#0a0a0a}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(247,151,30,.3)}
.btn-secondary{background:transparent;border:2px solid #f7971e;color:#f7971e;margin-top:16px}
.btn-secondary:hover{background:#f7971e;color:#0a0a0a}
.section{padding:80px 20px;max-width:1000px;margin:0 auto}
.section h2{font-size:2rem;margin-bottom:48px;color:#fff;text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:32px}
.card{background:#1a1a2e;border-radius:16px;padding:32px;border:1px solid #2a2a4a;transition:transform .3s}
.card:hover{transform:translateY(-4px)}
.card .icon{font-size:2.5rem;margin-bottom:16px}
.card h3{font-size:1.3rem;margin-bottom:12px;color:#fff}
.card p{color:#a0a0a0;font-size:.95rem}
.stats{display:flex;justify-content:center;gap:48px;flex-wrap:wrap;margin-bottom:48px}
.stat{text-align:center}
.stat .number{font-size:3rem;font-weight:800;color:#ffd200}
.stat .label{color:#a0a0a0;font-size:.95rem}
.pricing{padding:80px 20px;background:#111;text-align:center}
.pricing h2{font-size:2rem;margin-bottom:16px;color:#fff}
.pricing .subtitle{color:#a0a0a0;margin-bottom:48px;font-size:1.1rem}
.price-cards{display:flex;justify-content:center;gap:24px;flex-wrap:wrap;max-width:800px;margin:0 auto}
.price-card{background:#1a1a2e;border-radius:16px;padding:32px;width:320px;border:1px solid #2a2a4a}
.price-card.featured{border-color:#f7971e;position:relative}
.price-card.featured::before{content:"РЕКОМЕНДУЕМ";position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#f7971e;color:#0a0a0a;padding:4px 16px;border-radius:20px;font-size:.8rem;font-weight:700}
.price-card h3{font-size:1.2rem;margin-bottom:8px;color:#fff}
.price-card .price{font-size:2.5rem;font-weight:800;color:#ffd200;margin-bottom:4px}
.price-card .period{color:#666;font-size:.9rem;margin-bottom:20px}
.price-card ul{list-style:none;text-align:left;margin-bottom:24px}
.price-card ul li{padding:8px 0;border-bottom:1px solid #2a2a4a;color:#a0a0a0}
.price-card ul li::before{content:"\\2713 ";color:#ffd200}
.cta{padding:80px 20px;text-align:center;background:linear-gradient(135deg,#1a1a2e,#16213e)}
.cta h2{font-size:2rem;margin-bottom:16px;color:#fff}
.cta p{color:#a0a0a0;margin-bottom:32px;font-size:1.1rem}
footer{text-align:center;padding:32px;color:#444;font-size:.85rem}
</style>
</head>
<body>
<div class="hero">
<h1>AI-помощник для риелторов<br>и агентств недвижимости в Европе</h1>
<p>Автоматический анализ 100+ объявлений в день. Поиск несоответствий в ценах, проверка документов арендаторов, выявление мошенников</p>
<a href="https://t.me/radik5f35" class="btn btn-primary">Свяжитесь со мной</a>
<a href="/" class="btn btn-secondary">← Назад к боту</a>
</div>
<div class="section">
<h2>Возможности для агентств</h2>
<div class="grid">
<div class="card"><div class="icon">⚡</div><h3>Массовый анализ</h3><p>Загружайте десятки объявлений — AI проверит каждое на соответствие рыночным ценам и выявит аномалии</p></div>
<div class="card"><div class="icon">🔎</div><h3>Проверка документов</h3><p>Автоматическая проверка Schufa, подтверждения дохода, трудового договора по стандартам страны</p></div>
<div class="card"><div class="icon">🛡️</div><h3>Антифрод</h3><p>Выявление поддельных объявлений, мошеннических ссылок и завышенных цен до заключения сделки</p></div>
<div class="card"><div class="icon">📊</div><h3>Аналитика рынка</h3><p>Сравнение цен по районам, тренды рынка, рекомендации по ценообразованию</p></div>
<div class="card"><div class="icon">🌍</div><h3>Мультиязычность</h3><p>Анализ объявлений на любом европейском языке с переводом на язык вашего агентства</p></div>
<div class="card"><div class="icon">🔌</div><h3>API для интеграции</h3><p>Интеграция с вашими CRM и системами через API (скоро)</p></div>
</div>
</div>
<div class="section">
<div class="stats">
<div class="stat"><div class="number">100+</div><div class="label">объявлений в день</div></div>
<div class="stat"><div class="number">5</div><div class="label">языков</div></div>
<div class="stat"><div class="number">24/7</div><div class="label">без перерывов</div></div>
<div class="stat"><div class="number">€0</div><div class="label">текстовые лимиты</div></div>
</div>
</div>
<div class="pricing">
<h2>Подписка для агентств</h2>
<p class="subtitle">Тестовый период — 2 недели бесплатно</p>
<div class="price-cards">
<div class="price-card"><h3>Старт</h3><div class="price">49€</div><div class="period">в месяц</div><ul><li>До 50 объявлений/день</li><li>Базовый анализ</li><li>EMAIL-поддержка</li><li>1 пользователь</li></ul><a href="https://t.me/radik5f35" class="btn btn-secondary" style="width:100%;text-align:center">Начать бесплатно</a></div>
<div class="price-card featured"><h3>Профи</h3><div class="price">99€</div><div class="period">в месяц</div><ul><li>Безлимит объявлений</li><li>Глубокий анализ + антифрод</li><li>Приоритетная поддержка</li><li>До 5 пользователей</li><li>API-доступ (скоро)</li></ul><a href="https://t.me/radik5f35" class="btn btn-primary" style="width:100%;text-align:center">Попробовать 2 недели</a></div>
</div>
</div>
<div class="cta">
<h2>Готовы автоматизировать проверку объявлений?</h2>
<p>Напишите нам — настроим тестовый доступ за 15 минут</p>
<a href="https://t.me/radik5f35" class="btn btn-primary">Написать в Telegram</a>
</div>
<footer>© 2026 ExpatRentBot · AI-powered rental analysis for agencies in Europe</footer>
</body>
</html>"""
