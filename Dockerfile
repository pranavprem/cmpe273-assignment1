FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]
# The 2017 image defaulted to this application repo, which has no config files.
# The assignment's sample config repo is the useful default; pass another URL
# as the docker run argument to override it.
CMD ["https://github.com/sithu/assignment1-config-example"]
