FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://rclone.org/install.sh | bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make backup script executable if it exists
RUN if [ -f "/app/nightly_backup.sh" ]; then chmod +x /app/nightly_backup.sh; fi

CMD ["python", "main.py"]