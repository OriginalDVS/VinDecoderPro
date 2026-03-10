# 🚗 VIN Decoder Pro — Streamlit Edition

Декодер VIN-номеров с поиском по 4 источникам (Autodoc, Exist/Elcats, Armtek, Part-kom).
Автоматически определяет двигатель и ищет запчасти для G4NA/G4KE/G4KJ/G4KH.

## Деплой на Streamlit Cloud

1. Загрузите этот проект на GitHub
2. Зайдите на [share.streamlit.io](https://share.streamlit.io)
3. Подключите репозиторий
4. Укажите `app.py` как главный файл
5. Нажмите **Deploy**

Файл `packages.txt` автоматически установит Chromium и ChromeDriver на сервере Streamlit Cloud.

## Структура

```
app.py                  — Основное приложение
requirements.txt        — Python-зависимости
packages.txt            — Системные пакеты (Chromium)
.streamlit/config.toml  — Тема и настройки
```

## Локальный запуск

```bash
pip install -r requirements.txt
# Убедитесь что chromium/chromedriver установлены
streamlit run app.py
```

## Как работает

1. Вводите VIN (17 символов)
2. Приложение параллельно скрейпит 4 сайта для определения авто и двигателя
3. Если двигатель = G4NA/G4KE/G4KJ/G4KH — автоматически ищет запчасти
4. Коды запчастей можно скопировать
