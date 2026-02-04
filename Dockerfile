# Основа: Python 3.11 (подходит для Streamlit и Playwright)
FROM python:3.11-slim

# Установка системных зависимостей (включая xauth, xvfb, X11)
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
    # Очистка кэша (убирает ошибку "read-only file system")
    rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Установка Playwright Chromium (без интерактивного ввода)
RUN python -m playwright install chromium

# Копирование всего кода проекта
COPY . .

# Запуск через Xvfb (виртуальный экран) + headless режим Streamlit
CMD ["sh", "-c", "xvfb-run -a -s \"-screen 0 1920x1080x24\" streamlit run main.py --server.port=8080 --server.headless"]
