FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p recipes/management/commands
RUN touch recipes/management/__init__.py recipes/management/commands/__init__.py

# Копируем или создаем команду
COPY recipes/management/commands/load_ingredients.py /app/recipes/management/commands/load_ingredients.py

RUN python manage.py load_ingredients || echo "Команда load_ingredients пока недоступна"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi"]