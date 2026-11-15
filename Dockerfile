FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    HOST=0.0.0.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code only - generated catalog and caches are mounted/excluded.
COPY app.py build.py fetch.py epg.py playlist.py ./
COPY templates ./templates
COPY sources.json ./
COPY seeds ./seeds

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/output /app/cache \
    && chown -R app:app /app
USER app

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/sources').status==200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]