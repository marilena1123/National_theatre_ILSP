FROM python:3.10-buster

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
COPY ./unicode.so /app/unicode.so
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./nt_chat /app/nt_chat
COPY ./templates /app/templates
COPY ./static /app/static
COPY ./.env.production /app/.env
COPY ./minimal_nt.db /app/minimal_nt.db

ENV PYTHONPATH=/app
CMD ["python", "nt_chat/app.py"]
