FROM python:3.11-slim

# ตั้งค่าพื้นฐานสำหรับ Python ใน Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# ติดตั้ง dependencies สำหรับเชื่อมต่อ Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Python Library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ด
COPY . .

# สั่งรันด้วย Flask Run เพื่อรองรับ Hot Reload ในโหมด Debug
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]