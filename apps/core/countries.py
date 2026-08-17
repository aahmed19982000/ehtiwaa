"""Small curated country list (code, Arabic name, dial code) shared by the
phone country-code select and the specialist application form's
nationality / country-of-residence selects. Egypt first (target market),
then the rest of the Arab world, then a handful of other common countries.

Not a dependency on django-countries: this project only needs a modest,
Arabic-labeled list, not the full ISO set with flags/translations.
"""

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

COUNTRIES = [
    ("EG", _("مصر"), "+20"),
    ("SA", _("السعودية"), "+966"),
    ("AE", _("الإمارات"), "+971"),
    ("KW", _("الكويت"), "+965"),
    ("QA", _("قطر"), "+974"),
    ("BH", _("البحرين"), "+973"),
    ("OM", _("عُمان"), "+968"),
    ("JO", _("الأردن"), "+962"),
    ("LB", _("لبنان"), "+961"),
    ("SY", _("سوريا"), "+963"),
    ("IQ", _("العراق"), "+964"),
    ("PS", _("فلسطين"), "+970"),
    ("YE", _("اليمن"), "+967"),
    ("LY", _("ليبيا"), "+218"),
    ("TN", _("تونس"), "+216"),
    ("DZ", _("الجزائر"), "+213"),
    ("MA", _("المغرب"), "+212"),
    ("SD", _("السودان"), "+249"),
    ("SO", _("الصومال"), "+252"),
    ("MR", _("موريتانيا"), "+222"),
    ("DJ", _("جيبوتي"), "+253"),
    ("KM", _("جزر القمر"), "+269"),
    ("US", _("الولايات المتحدة الأمريكية"), "+1"),
    ("GB", _("المملكة المتحدة"), "+44"),
    ("CA", _("كندا"), "+1"),
    ("FR", _("فرنسا"), "+33"),
    ("DE", _("ألمانيا"), "+49"),
    ("IT", _("إيطاليا"), "+39"),
    ("ES", _("إسبانيا"), "+34"),
    ("TR", _("تركيا"), "+90"),
    ("IN", _("الهند"), "+91"),
    ("PK", _("باكستان"), "+92"),
    ("CN", _("الصين"), "+86"),
    ("MY", _("ماليزيا"), "+60"),
    ("ID", _("إندونيسيا"), "+62"),
    ("AU", _("أستراليا"), "+61"),
]

COUNTRY_CHOICES = [(code, name) for code, name, _dial in COUNTRIES]
DIAL_CODE_CHOICES = [
    (dial, format_lazy("{} {}", name, dial)) for _code, name, dial in COUNTRIES
]
DEFAULT_DIAL_CODE = "+20"
