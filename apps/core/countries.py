"""Small curated country list (code, Arabic name, dial code) shared by the
phone country-code select and the specialist application form's
nationality / country-of-residence selects. Egypt first (target market),
then the rest of the Arab world, then a handful of other common countries.

Not a dependency on django-countries: this project only needs a modest,
Arabic-labeled list, not the full ISO set with flags/translations.
"""

COUNTRIES = [
    ("EG", "مصر", "+20"),
    ("SA", "السعودية", "+966"),
    ("AE", "الإمارات", "+971"),
    ("KW", "الكويت", "+965"),
    ("QA", "قطر", "+974"),
    ("BH", "البحرين", "+973"),
    ("OM", "عُمان", "+968"),
    ("JO", "الأردن", "+962"),
    ("LB", "لبنان", "+961"),
    ("SY", "سوريا", "+963"),
    ("IQ", "العراق", "+964"),
    ("PS", "فلسطين", "+970"),
    ("YE", "اليمن", "+967"),
    ("LY", "ليبيا", "+218"),
    ("TN", "تونس", "+216"),
    ("DZ", "الجزائر", "+213"),
    ("MA", "المغرب", "+212"),
    ("SD", "السودان", "+249"),
    ("SO", "الصومال", "+252"),
    ("MR", "موريتانيا", "+222"),
    ("DJ", "جيبوتي", "+253"),
    ("KM", "جزر القمر", "+269"),
    ("US", "الولايات المتحدة الأمريكية", "+1"),
    ("GB", "المملكة المتحدة", "+44"),
    ("CA", "كندا", "+1"),
    ("FR", "فرنسا", "+33"),
    ("DE", "ألمانيا", "+49"),
    ("IT", "إيطاليا", "+39"),
    ("ES", "إسبانيا", "+34"),
    ("TR", "تركيا", "+90"),
    ("IN", "الهند", "+91"),
    ("PK", "باكستان", "+92"),
    ("CN", "الصين", "+86"),
    ("MY", "ماليزيا", "+60"),
    ("ID", "إندونيسيا", "+62"),
    ("AU", "أستراليا", "+61"),
]

COUNTRY_CHOICES = [(code, name) for code, name, _dial in COUNTRIES]
DIAL_CODE_CHOICES = [(dial, f"{name} {dial}") for _code, name, dial in COUNTRIES]
DEFAULT_DIAL_CODE = "+20"
