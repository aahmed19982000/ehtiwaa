# إعداد الدفع بالبطاقة (Paymob)

صفحة الدفع (`payments:checkout`) بتدعم بطاقات فيزا/ماستركارد فعليًا عن طريق Paymob، لكن الخيار بيفضل معطّل تلقائيًا (والدفع بيقتصر على التحويل البنكي) لحد ما تضيف بيانات حساب Paymob بتاعك في `.env`. مفيش حاجة وهمية هنا — الكود بيكلم Paymob API الحقيقي، بس محتاج حساب تاجر حقيقي عشان يشتغل.

## 1. إنشاء حساب Paymob

سجّل بنفسك على [accept.paymob.com](https://accept.paymob.com) (أو [paymob.com/egypt](https://paymob.com/egypt)) — الخطوة دي لازم تتعمل من حسابك انت شخصيًا، مينفعش حد تاني يعملها بدالك. هيديك Paymob بيئة **Test Mode** تقدر تجرب بيها فورًا من غير ما توثّق بيانات تجارية، وبعدين تفعّل **Live Mode** بعد رفع مستندات الـ KYC لو عايز تستقبل مدفوعات حقيقية.

## 2. الحصول على القيم الأربعة المطلوبة

| القيمة | مكانها في لوحة Paymob |
|---|---|
| `PAYMOB_API_KEY` | Settings → Account Info → API Key |
| `PAYMOB_INTEGRATION_ID` | Payment Integrations → أنشئ تكامل جديد نوعه "Online Card" → الرقم اللي بيظهر جنب اسم التكامل |
| `PAYMOB_IFRAME_ID` | Developers → iFrames → أنشئ iFrame جديد واربطه بتكامل الـ Online Card اللي عملته فوق |
| `PAYMOB_HMAC_SECRET` | Payment Integrations → افتح تكامل الـ Online Card → HMAC Secret |

## 3. إعداد الـ Webhook

من نفس صفحة تكامل الـ Online Card، حط رابط الـ **Transaction Processed Callback** (وده هو اللي بيستقبله `PaymobWebhookView` في المشروع):

```
https://<دومين-موقعك>/payments/webhooks/paymob/
```

محليًا وأنت بتجرب، الرابط ده مش هيوصله Paymob (السيرفر بتاعك مش متاح من بره جهازك) — تقدر تستخدم أداة زي [ngrok](https://ngrok.com) عشان تعمل تحويل مؤقت من رابط عام لجهازك، أو تجرب على بيئة staging متاحة فعليًا من الإنترنت.

## 4. إضافة القيم لملف `.env`

```
PAYMOB_API_KEY=...
PAYMOB_INTEGRATION_ID=...
PAYMOB_IFRAME_ID=...
PAYMOB_HMAC_SECRET=...
```

أعد تشغيل السيرفر بعد الحفظ. خيار "بطاقة ائتمان (فيزا / ماستركارد)" في صفحة الدفع هيتفعّل تلقائيًا (`paymob.is_configured()` بيتحقق من الأربع قيم دول مع بعض).

## ملاحظات

- في **Test Mode**، Paymob بتوفر أرقام بطاقات تجريبية (test cards) في توثيقهم عشان تجرب التدفق كامل من غير فلوس حقيقية.
- لو أي قيمة من الأربعة فاضية، الكود بيرجع تلقائيًا لعرض التحويل البنكي بس — مفيش أي كسر في صفحة الدفع.
- الـ HMAC secret ده اللي بيتحقق بيه `apps/payments/paymob.py::verify_webhook_signature` إن أي طلب واصل على الـ webhook فعلاً جاي من Paymob مش من حد بيحاول يزوّر نجاح دفعة.
