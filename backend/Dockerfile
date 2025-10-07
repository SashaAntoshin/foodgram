FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY data/ingredients.csv /app/data/ingredients.csv
RUN python manage.py load_ingredients

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi"]