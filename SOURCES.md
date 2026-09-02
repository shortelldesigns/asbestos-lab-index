# Sources fetched for Asbestos Lab Index v1

Retrieve date: **30 August 2026** (US/Pacific; fetch ran 30 August 2026 UTC).

## Succeeded

| Source | URL | Document / page date | Notes |
| --- | --- | --- | --- |
| NIST NVLAP directory search form | https://www-s.nist.gov/niws/index.cfm?event=directory.search | Retrieved 30 August 2026 | curl GET HTTP 200. HTML search UI. Program **Asbestos Fiber Analysis** is `<option value="2">`. Country **United States** is `countryId=1`. Form POSTs to `event=directory.results`. Archived at `data/sources/nist-nvlap-directory-search-form.html`. **No lab rows** — see Failures. |
| NIST Asbestos Fiber Analysis LAP | https://www.nist.gov/nvlap/asbestos-fiber-analysis-lap | Updated 17 July 2026 | WebFetch. PLM and/or TEM; AHERA requires NVLAP for labs analyzing samples from public or private K–12 schools; RTI proficiency testing. |
| EPA Protect Your Family from Exposures to Asbestos | https://www.epa.gov/asbestos/protect-your-family-exposures-asbestos | Last updated 25 June 2026 | WebFetch. Identification, leave/repair/remove, inspector vs contractor, conflict of interest, single-family federal vs state rules. |
| EPA Learn About Asbestos | https://www.epa.gov/asbestos/learn-about-asbestos | Last updated 13 July 2026 | WebFetch. What asbestos is; where it may be found (attic/vermiculite, vinyl tile, roofing, textured paint, pipe wrap, furnaces, brakes); exposure when disturbed; lung cancer, mesothelioma, asbestosis. |
| KDHE Licensed Asbestos Contractors PDF | https://www.kdhe.ks.gov/DocumentCenter/View/470/Kansas-Licensed-Asbestos-Abatement-Contractors-PDF | Header: **Updated 08/2026** | curl HTTP 200, 121303 bytes. `pdftotext -layout`, 3 pages, 77 contractors. Name, address, city, state, phone. No license numbers in the text layer. Archived at `data/sources/kdhe-licensed-asbestos-contractors-08-2026.pdf`. |
| KDHE About Asbestos | https://www.kdhe.ks.gov/235/About-Asbestos | Retrieved 30 August 2026 | WebFetch. Bureau of Air program; homeowners doing work on their own residence are not covered under Kansas or federal regulations but are strongly encouraged to visit EPA; program phone 785-296-6024; licensed companies and certified workers required for abatement; 10 working-day notification. |
| PA L&I Asbestos Occupations | https://www.pa.gov/agencies/dli/programs-services/labor-management-relations/bureau-of-occupational-and-industrial-safety/asbestos-occupations | Retrieved 30 August 2026 | WebFetch. Certification process; lists “should be updated daily (Monday through Friday)”; CAL phone 717-772-3396. |
| PA L&I Certified Asbestos Abatement Companies | https://www.pa.gov/content/dam/copapwp-pagov/en/dli/documents/individuals/labor-management-relations/bois/documents/asbcontr.htm | **Revised Date: 8/27/2026** | curl HTTP 200, 55667 bytes. HTML table, 299 data rows. Archived at `data/sources/pa-dli-certified-asbestos-abatement-companies-2026-08-27.htm`. |
| Philadelphia asbestos documents index | https://www.phila.gov/documents/asbestos-documents-and-forms/ | Retrieved 30 August 2026 | WebFetch. Links 2026–2027 licensed laboratories PDF (released 29 July 2026) and 2025–2026 licensed abatement contractors PDF. |
| Philadelphia 2026–2027 licensed asbestos laboratories PDF | https://www.phila.gov/media/20260729134450/health-licensed-asbestos-laboratories-2026-2027.pdf | License year 2026–2027; index says released 29 July 2026 | curl HTTP 200, 201689 bytes. Archived at `data/sources/phila-licensed-asbestos-laboratories-2026-2027.pdf`. Text layer mixes laboratory firms and named individual analysts; **not tabulated** as NVLAP labs. Linked from `nvlap.html` as a city license list. |

## Failed or incomplete

| Attempt | URL | What happened | What we did instead |
| --- | --- | --- | --- |
| NIST NVLAP directory search results | POST `https://www-s.nist.gov/niws/index.cfm?event=directory.results` with `programId=2`, `countryId=1`, session `csrfToken` | HTTP 200 application error page (“An Unexpected Error Occurred”) — no lab table | Honest NVLAP explainer linking the official search. **Zero lab rows transcribed.** |
| NIST NVLAP lab detail pages | GET `event=directory.detail&labid=…` without a live CSRF token (labids 111, 196, 224, 226, 325, 658, 721, 766, 901, 1463) | Application error page | Did not copy search-engine snippets of old detail pages into the directory. Confirm labs in the live search. |
| Philadelphia laboratories PDF as an NVLAP table | Same PDF as above | `pdftotext` mixes company licenses (EMSL, Criterion, Eurofins, AmeriSci, …) with individual analyst rows; columns (methods, phones) wrap | Linked the official PDF. Did not invent which rows are laboratories vs. people. |
| Kansas contractor license numbers | Same KDHE PDF | Not present in the PDF text layer | Field `license` = `unknown` on every Kansas JSON row. |

## Not used as lab or contractor sources

- Third-party directories and lab marketing sites (including InspectAPedia’s how-to on the NVLAP search).
- Search-engine snippets of NVLAP detail pages (CSRF-gated; expiration dates in snippets were not re-verified live).
- Files that appeared in the workspace (`data/sources/ca-acrulist.html`, `data/sources/lic59asb.csv`) without a fetch log in this build — not transcribed.
