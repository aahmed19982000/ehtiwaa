# WeasyPrint Arabic fonts (invoice PDFs)

## What was checked

The pre-launch QA pass flagged, as an untested assumption, that Arabic text
might render broken/disconnected in the WeasyPrint-generated invoice PDFs
(`apps/payments/services.generate_invoice`, template
`templates/payments/invoice_pdf.html`).

This was verified for real: a booking with an Arabic specialist name and
description was paid, `generate_invoice()` was run against the actual
template, and the resulting PDF was opened and visually inspected.

**Result: on this dev machine (macOS), the Arabic text rendered correctly**
— connected letterforms, correct RTL direction, correct number placement.
So the literal failure mode described in the QA report does not reproduce
here.

## The gap that's still real

The invoice template's CSS only declared `font-family: "Segoe UI", "DejaVu
Sans", sans-serif` — neither of which has real Arabic glyph coverage
("Segoe UI" doesn't exist outside Windows at all; "DejaVu Sans" has
essentially none). Checking what font actually got used:

```
$ fc-match "DejaVu Sans:lang=ar"
Arial.ttf: "Arial" "Regular"
```

fontconfig silently rejected "DejaVu Sans" for Arabic and substituted
**Arial** — a font that happens to ship with real Arabic coverage on macOS
specifically (via Apple's system font substitution), which is why the PDF
looked correct here. A minimal Linux container (the realistic production
target) has no equivalent automatic substitution and, unless an
Arabic-capable font is actually installed, WeasyPrint/Pango would fall back
to missing-glyph boxes or a font with no real Arabic shaping — i.e. exactly
the bug the QA report theorized, just not on this machine.

## Fix applied

`templates/payments/invoice_pdf.html` now declares Arabic-capable fonts
first:

```css
font-family: "Cairo", "Amiri", "Noto Naskh Arabic", "Segoe UI", "DejaVu Sans", sans-serif;
```

("Cairo" matches the brand's own web font, used everywhere else in
`templates/base.html`.)

## What production needs

WeasyPrint uses Pango/Cairo for text shaping and fontconfig for font
resolution — it does **not** fetch Google Fonts or any other web font at
render time, so one of the fonts above must be installed as a real system
font wherever invoices are generated (the app server, or the Celery worker
if invoice generation ever moves there).

On a Debian/Ubuntu-based image, install (in addition to the existing
`libpango-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`
that WeasyPrint itself needs — see WeasyPrint's own install docs, not
repeated here since this repo has no Dockerfile yet to attach it to):

```
apt-get install -y fonts-noto-core        # Noto Naskh Arabic + Latin, Google's own font, permissively licensed
```

(Alternative: `fonts-hosny-amiri` where available, or bundle the desired
`.ttf` file(s) directly in the repo and register them with WeasyPrint's
`font_config`/`FontConfiguration` instead of relying on a system package.)

Whichever route is used, re-run the same manual check after deploying:
create a paid order, call `generate_invoice()`, open the resulting PDF, and
confirm the Arabic renders connected and RTL — don't assume the fix worked
just because it works locally, for the same reason the original "looks
fine on my Mac" assumption wasn't good enough.
