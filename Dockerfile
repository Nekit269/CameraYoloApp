FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN pip install poetry

WORKDIR /CameraYoloApp
# Копируем файлы зависимостей и ставим зависимости
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi

COPY . .

# Делаем entrypoint.sh исполняемым
RUN chmod +x /CameraYoloApp/entrypoint.sh
ENTRYPOINT ["/CameraYoloApp/entrypoint.sh"]

# Запуск сервера через run.py
CMD ["poetry", "run", "python", "run.py"]