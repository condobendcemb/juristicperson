pms_saas/
├── app.py              # จุดรวมร่างและการตั้งค่าหลัก
├── database.py         # ตั้งค่า SQLAlchemy
├── models.py           # โครงสร้างตาราง (Rooms, Water, Invoices)
├── routes/
│   ├── auth.py         # ระบบ Login/Signup
│   ├── building.py     # จัดการห้องและลูกบ้าน
│   └── billing.py      # บันทึกค่าน้ำและออกใบแจ้งหนี้
└── templates/
│   ├── base.html       # Layout หลัก (รวม HTMX/Tailwind)
│   ├── dashboard.html  # หน้าแรกของนิติฯ
│   └── billing/
│       └── water_form.html  # เศษ HTML สำหรับ HTMX (Partial)
│── requirements.txt
│── Dockerfile
└── docker-compose.yml    





#  Run
ขั้นตอนการ Restart ระบบ
หลังจากแก้โค้ดเสร็จแล้ว (Hot Reload อาจจะไม่ทำงานในเคสที่แอปตายสนิทแบบนี้) ให้ทำตามนี้ครับ:
#
หยุดระบบเดิม:
docker-compose down
#
รันใหม่:
docker-compose up -d
#
docker exec -it juristicperson-web env | findstr DATABASE_URL
#
เช็คสถานะอีกครั้ง:
docker ps