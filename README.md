# Asbestos Lab Index

Static first version of a U.S. directory: NVLAP-accredited asbestos analysis labs, then public state asbestos-contractor lists.

**Homepage line:** Find an NVLAP-accredited lab that can analyze asbestos — then a licensed contractor if the report says to remove it.

**Byline:** Stephen Shortell / Asbestos Lab Index

**Published:** 30 August 2026 (US/Pacific)

Open `index.html` in a browser. All links are relative; no build step is required. Intended GitHub Pages URL (not published by this build): <https://shortelldesigns.github.io/asbestos-lab-index/>

## Rules (do not break these)

- Never invent a laboratory, contractor, phone number, accreditation, or license.
- If a field is not on the official source, write `unknown` or omit it and link the official tool.
- Do not rank abatement companies. Do not add “best asbestos company” copy.
- Analyze first; hire a licensed contractor only after the report (and an inspector who is not the removal firm) says to repair or remove.
- Call (`tel:`) links only when the official list already printed a phone. No click-to-call tracking.
- Every contractor record in `data/*.json` must include a `source_url`.
- No live affiliate links on this version.

## How to add a nightly page

This is a file-based site. A “nightly page” is a new or refreshed HTML file plus, if listings changed, an updated JSON file.

1. **Pick the official source.** For labs: NIST NVLAP directory, program **Asbestos Fiber Analysis**:  
   <https://www-s.nist.gov/niws/index.cfm?event=directory.search>  
   For contractors: a state labor, health, or environmental PDF or HTML roster (not a business directory).

2. **Fetch and archive.** Download the source to `data/sources/` with `curl`. For PDFs run `pdftotext -layout`. Record the URL, HTTP status, document date, and retrieve date in `SOURCES.md`.

3. **Transcribe, do not enrich.** Copy name, city, state, phone, lab code, license/cert number, and expiration only as they appear. Do not fill gaps from Google or a company’s marketing site. Mark missing fields `unknown`.

4. **Write JSON first.** Add or replace `data/contractors-xx.json` or `data/nvlap-labs.json` with one object per row, each with `source_url` and `source_document_date`. Keep a top-level `meta` block describing limitations (for example “directory requires JavaScript” or “license number not printed”).

5. **Generate the HTML page.** Follow `contractors/kansas.html` (PDF roster) or `nvlap.html` (honest page when the official tool cannot be scraped). Use `css/site.css`. Add the state to `states.html` and the homepage only when the table has real, sourced rows — or when the honest limitation is the whole story (NVLAP search).

6. **Cite dates.** Use the document’s own date plus the retrieve date. Site “last updated” is the calendar day you publish, in US/Pacific.

7. **Do not rank.** Keep the issuing agency’s order. Collapse duplicate certification numbers only when the official list printed two expiration dates for the same number, and say so.

8. **Log failures.** If a fetch fails, say so in `SOURCES.md` and on the page. Do not substitute a stale unofficial list.

## Layout

```
index.html                      homepage
states.html                     KS + PA contractors live; NVLAP national; others coming soon
nvlap.html                      honest NVLAP search explainer (0 rows this version)
when-to-test.html               EPA leave / repair / remove + NIST lab role
about.html                      methodology + commission disclosure
contractors/kansas.html         77 KDHE-licensed contractors
contractors/pennsylvania.html   284 unique L&I certification numbers
css/site.css
data/nvlap-labs.json
data/contractors-ks.json
data/contractors-pa.json
data/sources/                   archived official files
SOURCES.md
RESULT.md
.nojekyll
```

## Local check

```
cd asbestos-lab-index
python3 -m http.server 8080
# open http://127.0.0.1:8080/
```

Or double-click `index.html`. Relative links work either way.
