#!/bin/sh
echo "Initializing Database..."
# สร้างตารางถ้ายังไม่มี (เชื่อมกับ Supabase ตาม DATABASE_URL)
python3 init_db.py

echo "Starting Application on Port: ${PORT:-5000}"
# รันแอปด้วย gunicorn และใช้พอร์ตตามที่ Render กำหนด ($PORT)
gunicorn app:app --bind 0.0.0.0:${PORT:-5000}
