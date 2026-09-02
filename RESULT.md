# Asbestos Lab Index v1 — result

**Homepage:** `/workspace/asbestos-lab-index/index.html`

**Published (files only):** 30 August 2026 (US/Pacific)

This build does **not** publish to GitHub. Intended Pages URL: <https://shortelldesigns.github.io/asbestos-lab-index/>

## Pages

| File | Role |
| --- | --- |
| `index.html` | Homepage: value prop, analyze → read report → hire-if-needed flow, live links, footer disclaimer |
| `nvlap.html` | Honest NVLAP page: how to search NIST; **0 lab rows** because the directory did not return a table without JS |
| `when-to-test.html` | EPA leave / repair / remove + inspector vs contractor + NIST lab role, with dates |
| `contractors/kansas.html` | 77 real contractors from KDHE August 2026 PDF |
| `contractors/pennsylvania.html` | 284 unique L&I certification numbers from the 27 August 2026 HTML list |
| `about.html` | Methodology + “we may earn a commission” (no live affiliate or click-to-call tracking) |
| `states.html` | NVLAP national + KS and PA live; other states coming soon |
| `css/site.css` | Navy / forest / cream, mobile-first, conversion-pass classes rebranded |
| `data/nvlap-labs.json` | `labs: []` plus fetch-status meta |
| `data/contractors-ks.json` | 77 sourced records |
| `data/contractors-pa.json` | 284 sourced records |
| `README.md` | How to add a nightly page |
| `SOURCES.md` | Fetches, dates, failures |
| `.nojekyll` | Empty; GitHub Pages |

## Real counts

- **NVLAP Asbestos Fiber Analysis labs: 0 rows transcribed.** The official directory is a CSRF/JS search form. GET of the form succeeded. POST of results and GET of detail pages failed with an application error. We did not invent laboratories, lab codes, or phones from search snippets.
- **Kansas licensed asbestos contractors: 77.** All from KDHE *Licensed Asbestos Contractors*, header **Updated 08/2026**. Name, address, city, state, phone as printed. License number **unknown** (not on the PDF). One row prints North Little Rock / **AK** as on the PDF; not corrected. `tel:` links only because the PDF printed phones. Order is the PDF order, not a ranking.
- **Pennsylvania certified asbestos abatement companies: 284 unique certification numbers** (299 table rows on the official HTML; 15 duplicate cert numbers collapsed to the later expiration date). Source: L&I *Certified Asbestos Abatement Companies*, **Revised Date: 8/27/2026**. Cert #, name, phone, address, city, state, ZIP, expiration as printed. Not ranked.

## Fetch failures

- NIST NVLAP `directory.results` POST: application error. No lab table.
- NIST NVLAP `directory.detail` GET without a valid CSRF token: application error. No detail rows used.
- Philadelphia licensed-laboratories PDF: downloaded; not tabulated (firm vs. individual analyst mix in the text layer). Linked as a city license list, not as NVLAP.

No laboratory, contractor, phone number, accreditation, or license was invented.
