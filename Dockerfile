FROM python:3.11-slim

# ตั้งค่าพื้นฐานสำหรับ Python ใน Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# ติดตั้ง dependencies สำหรับเชื่อมต่อ Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Python Library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ด
COPY . .

# ให้สิทธิ์รันสำหรับ start.sh
RUN chmod +x start.sh

# สั่งรันผ่านสคริปต์เริ่มต้น
CMD ["sh", "start.sh"]