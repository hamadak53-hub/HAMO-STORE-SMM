# HAMO STORE SMM

متجر عربي مستقل لخدمات السوشيال ميديا.

## الملفات الأساسية
- `index.html` و`style.css` و`script.js`: واجهة العملاء.
- `main.py`: API الحسابات والخدمات والطلبات ولوحة الإدارة.
- `admin.html` و`admin.css` و`admin.js`: لوحة تحكم الإدارة.
- `render.yaml`: إعداد نشر Render Blueprint.
- `requirements.txt`: مكتبات Python.

## تشغيل محلي
```bash
pip install -r requirements.txt
```
على Windows PowerShell:
```powershell
$env:SECRET_KEY="ضع-قيمة-عشوائية-طويلة"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="كلمة-مرور-قوية"
uvicorn main:app --reload
```
افتح `http://127.0.0.1:8000`، ولوحة الإدارة من `/admin`.

## النشر على Render
استخدم Blueprint من ملف `render.yaml` أو أنشئ Web Service:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

اضبط المتغيرات السرية:
- `SECRET_KEY`: مفتاح عشوائي طويل وسري.
- `ADMIN_USERNAME`: اسم دخول الإدارة الذي تختاره.
- `ADMIN_PASSWORD`: كلمة مرور قوية تختارها.
- `DATABASE_URL`: رابط PostgreSQL دائم (موصى به للإنتاج).
- `COOKIE_SECURE=true` عند استخدام HTTPS.

لا تضع كلمات المرور أو مفاتيح المورد داخل ملفات GitHub.

## الموجود حاليًا
- إنشاء حساب عميل وتسجيل الدخول.
- إضافة خدمات وتحديد سعر كل 1000 وحدة والحد الأدنى والأقصى.
- إرسال طلب خدمة بعد تسجيل الدخول.
- متابعة حالة الطلب من لوحة الإدارة وتحديثها.
- إخفاء الخدمات بدل حذفها.

## ملاحظات مهمة
- الأسعار التي تدخلها هي **سعر كل 1000 وحدة بالجنيه المصري**؛ قيمة الطلب تُحسب تلقائيًا حسب الكمية.
- الطلبات تُنشأ بحالة انتظار الدفع. تأكيد الدفع والتنفيذ يتمان يدويًا في المرحلة الأولى.
- لا يوجد ربط مورد أو دفع إلكتروني حتى الآن.
- استخدم PostgreSQL في Render؛ قاعدة SQLite المحلية ليست مناسبة لاستضافة مؤقتة قد تمسح الملفات عند إعادة النشر.
