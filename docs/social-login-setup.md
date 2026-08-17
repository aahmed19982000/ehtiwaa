# إعداد تسجيل الدخول عبر Google و Auth0

الأزرار الاجتماعية في صفحتي "مرحبًا بك" و"تسجيل الدخول" لا تظهر إلا بعد ضبط بيانات الاعتماد التالية في `.env` (محليًا) أو متغيرات البيئة الفعلية (staging/production). بدون ذلك، تُخفى الأزرار تلقائيًا بدلاً من ظهورها معطّلة.

## Google

1. أنشئ مشروعًا على [Google Cloud Console](https://console.cloud.google.com/) (أو استخدم مشروعًا قائمًا).
2. من "APIs & Services" → "Credentials"، أنشئ "OAuth 2.0 Client ID" من نوع "Web application".
3. أضف الـ Authorized redirect URI التالي (حسب البيئة):
   - محليًا: `http://localhost:8000/accounts/social/google/login/callback/`
   - staging/production: `https://<domain>/accounts/social/google/login/callback/`
4. انسخ الـ Client ID والـ Client Secret إلى `.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

## Auth0

1. أنشئ حسابًا/Tenant على [auth0.com](https://auth0.com) إذا لم يكن لديك واحد.
2. من لوحة تحكم Auth0، أنشئ تطبيقًا (Application) من نوع "Regular Web Application".
3. أضف الـ Allowed Callback URL التالي (حسب البيئة):
   - محليًا: `http://localhost:8000/accounts/social/auth0/login/callback/`
   - staging/production: `https://<domain>/accounts/social/auth0/login/callback/`
4. انسخ الـ Domain والـ Client ID والـ Client Secret إلى `.env`:
   ```
   AUTH0_DOMAIN=your-tenant.us.auth0.com
   AUTH0_CLIENT_ID=...
   AUTH0_CLIENT_SECRET=...
   ```
5. من تبويب "Advanced" في إعدادات التطبيق → "Grant Types"، فعّل "Password" — صفحة التسجيل الخاصة بنا (`accounts:signup`) تنشئ الحساب مباشرة عبر Auth0 Authentication API (`dbconnections/signup`) ثم تسجّل الدخول عبر Resource Owner Password Grant بدلاً من التوجيه لصفحة Auth0 المستضافة، وهذا الـ grant type غير مفعّل افتراضيًا.
6. (اختياري) اسم الـ Database connection الافتراضي هو `Username-Password-Authentication`؛ إن كان مختلفًا في الـ tenant عندك، اضبطه عبر `.env`:
   ```
   AUTH0_DB_CONNECTION=...
   ```

## ملاحظات

- زر الدخول بجوجل وصفحة تسجيل الدخول (`accounts:login`) يوجّهان لصفحة Auth0 المستضافة (Universal Login). صفحة التسجيل (`accounts:signup`) هي فورم مخصص بتصميمنا، لكنها تُنشئ الحساب داخل نفس الـ Auth0 tenant عبر الـ API مباشرة — كلاهما يستخدم نفس الـ Database connection، لذا يمكن لأي مستخدم تسجيل الدخول من صفحة `accounts:login` بعد إنشاء حسابه من `accounts:signup`.
- عند أول تسجيل دخول عبر مزود اجتماعي (أو إنشاء حساب من فورمنا)، يُنشأ حساب `accounts.User` تلقائيًا (أو يُربط بحساب محلي موجود بنفس البريد الإلكتروني) عبر `apps.accounts.adapters.EhtiwaaSocialAccountAdapter`.
- لا تُدفع بيانات الاعتماد الفعلية إلى Git — `.env` مستبعد عبر `.gitignore`، ويُستخدم `.env.example` كمرجع فقط.
