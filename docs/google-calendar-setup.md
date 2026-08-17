# إعداد Google Calendar (رابط Google Meet للحجوزات)

عند إنشاء أي حجز، بيحاول التطبيق ينشئ حدث في Google Calendar مع رابط Google Meet تلقائي، ويحطه في إيميل التأكيد وصفحة تفاصيل الحجز. لو الإعداد ده مش موجود، الحجز بيكمّل عادي من غير رابط — مفيش أي كسر في التدفق.

## ليه مش Service Account؟

جرّبنا الأول Service Account عادي (الطريقة المعتادة للتكاملات الخلفية)، لكن Google بترفض توليد رابط Meet تلقائي لحسابات الخدمة العادية (بره Google Workspace) بخطأ `"Invalid conference type value"`. الحل: نستخدم حساب Google حقيقي عن طريق OAuth بدل حساب خدمة.

## الإعداد (مرة واحدة فقط)

1. روح [console.cloud.google.com](https://console.cloud.google.com)، افتح/أنشئ مشروع.
2. من **APIs & Services → Library**، فعّل **Google Calendar API**.
3. من **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - النوع: **Desktop app**.
   - أعطه أي اسم.
4. حمّل ملف الـ JSON بتاع الـ OAuth client ده (زرار التحميل جنب الـ client في الجدول).
5. من الطرفية (على جهازك، مش على السيرفر — لازم يفتح متصفح تسجّل بيه دخولك):
   ```bash
   python manage.py google_calendar_authorize /path/to/client_secret_....json
   ```
6. هيفتح صفحة Google في المتصفح — سجّل دخول بالحساب اللي عايز الحجوزات تتضاف في الكالندر بتاعه (ده هو نفس الحساب اللي هيستضيف روابط Meet)، ووافق على الصلاحية.
7. الأمر هيحدّث `.env` تلقائيًا بـ `GOOGLE_CALENDAR_CLIENT_ID` و`GOOGLE_CALENDAR_CLIENT_SECRET` و`GOOGLE_CALENDAR_REFRESH_TOKEN`. أعد تشغيل السيرفر بعدها.

## ملاحظات

- `GOOGLE_CALENDAR_ID` اختياري — لو سبته فاضي، الأحداث بتتضاف في الكالندر الافتراضي (`primary`) بتاع الحساب اللي وافقت بيه.
- الأمر ده منفصل تمامًا عن إعدادات تسجيل الدخول بجوجل (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` الخاصة بـ Auth0) — ده OAuth client مستقل بصلاحية `calendar.events` بس.
- لو الحساب سحب صلاحية التطبيق (من [myaccount.google.com/permissions](https://myaccount.google.com/permissions))، شغّل الأمر تاني عشان تاخد refresh token جديد.
