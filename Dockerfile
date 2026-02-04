# Основа: Python 3.11
FROM python:3.11-slim

# Установка системных зависимостей (включая xauth, xvfb)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        xauth \
        xvfb \
        libnss3 \
        libnspr4 \
        libgbm1 \
        libasound2 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libx11-xcb1 \
        libxss1 \
        libxtst6 \
        lsb-release \
        xdg-utils \
        && \
    rm -rf /var/lib/apt/lists/*

# Установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка Playwright Chromium
RUN python -m playwright install chromium

# Копирование кода
COPY . .

# Запуск через Xvfb (виртуальный экран)
CMD ["sh", "-c", "xvfb-run -a -s \"-screen 0 1920x1080x24\" streamlit run main.py --server.port=8080"]
