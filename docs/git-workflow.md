# استراتيجية Git والفروع (Git Branching Strategy)

## الفروع الأساسية

- **`master`** — الفرع القابل للنشر دائمًا (production). لا يُدفع إليه مباشرة.
- **`develop`** — فرع التكامل (staging)، تُدمج فيه كل الميزات المكتملة قبل الانتقال إلى `master`.
- **`feature/<وصف-مختصر>`** — لكل ميزة جديدة، يُفرَّع من `develop`. مثال: `feature/bookings-model`.
- **`fix/<وصف-مختصر>`** — لإصلاح خلل غير عاجل، يُفرَّع من `develop`.
- **`hotfix/<وصف-مختصر>`** — لإصلاح عاجل في الإنتاج، يُفرَّع من `master` ثم يُدمج في كل من `master` و`develop`.

## تدفق الطلبات (Pull Requests)

1. كل فرع `feature/*` أو `fix/*` يُفتح له Pull Request باتجاه `develop` (أو `master` في حالة `hotfix/*`).
2. يجب أن تنجح CI (`.github/workflows/ci.yml`) قبل الدمج.
3. مراجعة واحدة على الأقل مطلوبة قبل الدمج.
4. يُفضَّل استخدام **Squash Merge** للحفاظ على تاريخ خطي وواضح.

## رسائل الـ Commit

نتبع نمط [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(bookings): إضافة نموذج Booking
fix(accounts): تصحيح تفرد البريد الإلكتروني
chore(ci): إضافة حاوية خدمة PostgreSQL
docs: إضافة دليل Git workflow
```

النطاق (scope) عادة اسم التطبيق (`accounts`, `bookings`, ...) أو المنطقة (`ci`, `settings`, `templates`).

## الإصدارات (Releases)

عند استقرار مرحلة كاملة على `develop`، تُدمج في `master` ويُوسم الإصدار بعلامة `vX.Y.Z`.
