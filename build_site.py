#!/usr/bin/env python3
"""Build the static Asbestos Lab Index from archived official sources.

Never invent a laboratory, contractor, phone number, or license.
"""
from __future__ import annotations

import csv
import html as htmlmod
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"

UPDATED = "30 August 2026"
UPDATED_ISO = "2026-08-30"
UPDATED_PT = "30 August 2026 (US/Pacific)"

NVLAP_SEARCH = "https://www-s.nist.gov/niws/index.cfm?event=directory.search"
NVLAP_LAP = "https://www.nist.gov/nvlap/asbestos-fiber-analysis-lap"
FL_CSV_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/lic59asb.csv"
FL_LAYOUT_URL = "https://www2.myfloridalicense.com/asbestos-contractors-and-consultants/public-records/"
FL_README_URL = "https://www2.myfloridalicense.com/sto/documents/readme.pdf"
FL_CODES_URL = "https://www2.myfloridalicense.com/about-us/understanding-dbpr-codes/"
CA_LIST_URL = "https://www.dir.ca.gov/databases/doshacru/acrulist.asp"
CA_SEARCH_URL = "https://www.dir.ca.gov/Databases/doshacru/acrusearch.html"
CA_DETAIL_BASE = "https://www.dir.ca.gov/databases/doshacru/"
NY_BUREAU_URL = "https://dol.ny.gov/asbestos-control-bureau"
NY_LISTING_URL = (
    "https://biservices.labor.ny.gov/Reports/bi/"
    "?perspective=classicviewer"
    "&pathRef=.public_folders%2FWPS%20Reports%2FActive%20Asbestos%20Contractors"
    "&id=iEB741D9038A149129DCA85571AE53C50"
    "&ui_appbar=false&ui_navbar=false"
)
EPA_HOME_URL = (
    "https://www.epa.gov/asbestos/how-do-i-know-if-i-have-asbestos-my-home"
    "-floor-tile-ceiling-tile-shingles-siding-etc"
)
EPA_PROTECT_URL = "https://www.epa.gov/asbestos/protect-your-family-exposures-asbestos"
EPA_PRO_URL = "https://www.epa.gov/asbestos/asbestos-professionals"

OCCUPATION = {
    "AX": "Asbestos Consultant",
    "CJC": "Asbestos Contractor",
    "ZA": "Asbestos Business",
    "AF": "Asbestos Consultant (AF)",
    "DD": "Asbestos Consultant (Doctoral Degree)",
    "EA": "Asbestos Consultant (Engineer)",
    "IA": "Asbestos Consultant (Industrial Hygiene)",
    "FO": "Financial Responsible Officer",
    "CRS1": "Asbestos Basic Initial Training Course",
    "CRS2": "Asbestos Refresher Training Course",
    "PVDR": "Asbestos Course Provider",
}
PRIMARY_STATUS = {"C": "Current", "P": "Probation", "S": "Suspended"}
SECONDARY_STATUS = {"A": "Active", "I": "Inactive"}

KITS = [
    {
        "asin": "B01N1ZF8C5",
        "url": "https://www.amazon.com/dp/B01N1ZF8C5?tag=radontestinde-20",
        "title": "Asbestos Test Kit 1 PK (5 Bus. Days) Return Ground Shipping Included",
        "brand": "SLGi / Schneider Laboratories Global, Inc.",
        "title_source": "Amazon product page title, fetched 30 August 2026",
    },
    {
        "asin": "B08T257C5Q",
        "url": "https://www.amazon.com/dp/B08T257C5Q?tag=radontestinde-20",
        "title": "Asbestos & Lead Combo Test Kit (Same Day) Schneider Labs | (Overnight Return Shipping)",
        "brand": "SLGi / Schneider Laboratories Global, Inc.",
        "title_source": "Amazon product page title, fetched 30 August 2026",
    },
    {
        "asin": "B00IJGXO96",
        "url": "https://www.amazon.com/dp/B00IJGXO96?tag=radontestinde-20",
        "title": "Asbestos, Lead, and Mold Combo Test Kit (1 Bus. Day) Schneider Labs",
        "brand": "SLGi / Schneider Laboratories Global, Inc.",
        "title_source": "Amazon.com listing title from search index 30 August 2026 (direct page fetch returned not-found from one provider)",
    },
]


def esc(s: str | None) -> str:
    return htmlmod.escape(s or "", quote=True)


def tel_href(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits in {"", "0"}:
        return None
    if len(digits) == 11 and digits.startswith("1"):
        return f"tel:+{digits}"
    if len(digits) == 10:
        return f"tel:+1{digits}"
    return None


class AcruTable(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_tr = False
        self.in_cell = False
        self.rows: list[list[dict]] = []
        self.cur: list[dict] | None = None
        self.cell: list[str] = []
        self.cell_href: str | None = None
        self.updated: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.in_table = True
        if tag == "tr" and self.in_table:
            self.in_tr = True
            self.cur = []
        if tag in {"td", "th"} and self.in_tr:
            self.in_cell = True
            self.cell = []
            self.cell_href = None
        if tag == "a" and self.in_cell and a.get("href"):
            self.cell_href = a["href"]
        if tag == "br" and self.in_cell:
            self.cell.append("\n")

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            text = htmlmod.unescape(re.sub(r"\s+", " ", " ".join(self.cell)).strip())
            assert self.cur is not None
            self.cur.append({"text": text, "href": self.cell_href})
            self.in_cell = False
        if tag == "tr" and self.in_tr:
            if self.cur:
                self.rows.append(self.cur)
            self.in_tr = False
        if tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)
        if "last updated on" in data.lower():
            m = re.search(r"last updated on\s+([0-9/]+)", data, re.I)
            if m:
                self.updated = m.group(1)


def parse_florida(path: Path) -> list[dict]:
    records = []
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.reader(f):
            if len(row) < 21:
                continue
            occ = row[1].strip()
            rec = {
                "name": row[2].strip(),
                "dba": row[3].strip(),
                "city": row[8].strip(),
                "state": row[9].strip(),
                "zip": row[10].strip(),
                "license_number": row[12].strip(),
                "license": row[20].strip() or (occ + row[12].strip()),
                "occupation_code": occ,
                "occupation": OCCUPATION.get(occ, occ),
                "primary_status_code": row[13].strip(),
                "primary_status": PRIMARY_STATUS.get(row[13].strip(), row[13].strip()),
                "secondary_status_code": row[14].strip(),
                "secondary_status": SECONDARY_STATUS.get(row[14].strip(), "") if row[14].strip() else "",
                "original_date": row[15].strip(),
                "effective_date": row[16].strip(),
                "expiration": row[17].strip(),
                "phone": None,
                "source_url": FL_CSV_URL,
            }
            records.append(rec)
    records.sort(key=lambda r: (r["occupation_code"], r["name"], r["license"]))
    return records


def parse_california(path: Path) -> tuple[list[dict], str | None]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = AcruTable()
    parser.feed(raw)
    records = []
    for row in parser.rows:
        if len(row) != 7:
            continue
        if row[0]["text"].lower().startswith("reg"):
            continue
        name = row[2]["text"].replace("\n", " ").strip()
        loc = row[4]["text"].strip()
        phone_raw = row[6]["text"].strip()
        phone = None if phone_raw in {"", "-", "—", "n/a", "N/A"} else phone_raw
        href = row[0]["href"] or ""
        detail = CA_DETAIL_BASE + href.lstrip("/") if href else CA_LIST_URL
        records.append(
            {
                "reg_number": row[0]["text"].strip(),
                "cslb": row[1]["text"].strip(),
                "name": name,
                "restrictions": row[3]["text"].strip(),
                "location": loc,
                "expires": row[5]["text"].strip(),
                "phone": phone,
                "detail_url": detail,
                "source_url": CA_LIST_URL,
            }
        )
    return records, parser.updated


NAV = [
    ("index.html", "Home"),
    ("nvlap.html", "NVLAP labs"),
    ("florida.html", "Florida"),
    ("california.html", "California"),
    ("ny.html", "New York"),
    ("states.html", "States"),
    ("when-to-test.html", "When to test"),
    ("kits.html", "Kits"),
    ("about.html", "About"),
]


def header(current: str, title: str, description: str, wide: bool = False) -> str:
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        items.append(f'        <li><a href="{href}"{cur}>{esc(label)}</a></li>')
    wide_cls = ' class="wide"' if wide else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="stylesheet" href="css/site.css">
</head>
<body>
  <a class="skip" href="#content">Skip to content</a>
  <header class="site">
    <div class="brand">
      <h1><a href="index.html">Asbestos Lab Index</a></h1>
    </div>
    <nav class="primary" aria-label="Primary">
      <ul>
{chr(10).join(items)}
      </ul>
    </nav>
  </header>
  <main id="content"{wide_cls}>
"""


def footer(extra: str = "") -> str:
    return f"""  </main>
  <footer class="site">
    <div class="inner">
      <p>Shortell Designs. Last updated {UPDATED_PT}.</p>
      <p><a href="about.html">Methodology</a> · <a href="states.html">States</a></p>
{extra}      <div class="disclaimer">
        <p>This site is not a government agency and does not accredit laboratories or license contractors. Rows are transcribed from the official sources cited on each page. Licenses, accreditation, and phone numbers change. Confirm with the laboratory or licensing program before you hire anyone or ship a sample.</p>
        <p>This site is educational, not medical, legal, or engineering advice. A mail-in kit is not a substitute for an NVLAP-accredited laboratory you choose yourself, and it is not a licensed abatement contractor.</p>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def status_label(rec: dict) -> str:
    parts = [rec["primary_status"]] if rec["primary_status"] else []
    if rec["secondary_status"]:
        parts.append(rec["secondary_status"])
    return " / ".join(parts) if parts else "Current"


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fl_table(rows: list[dict], caption: str) -> str:
    body = []
    for rec in rows:
        dba = rec["dba"] or "—"
        body.append(
            "        <tr>\n"
            f'          <td data-label="Name">{esc(rec["name"])}</td>\n'
            f'          <td data-label="DBA">{esc(dba)}</td>\n'
            f'          <td data-label="City">{esc(rec["city"])}</td>\n'
            f'          <td data-label="State">{esc(rec["state"])}</td>\n'
            f'          <td data-label="License">{esc(rec["license"])}</td>\n'
            f'          <td data-label="Type">{esc(rec["occupation"])}</td>\n'
            f'          <td data-label="Status">{esc(status_label(rec))}</td>\n'
            "        </tr>"
        )
    return f"""    <div class="table-wrap">
      <table class="roster-table">
        <caption>{esc(caption)}</caption>
        <thead>
          <tr>
            <th>Name</th>
            <th>Doing business as</th>
            <th>City</th>
            <th>State</th>
            <th>License</th>
            <th>Type</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(body)}
        </tbody>
      </table>
    </div>
"""


def ca_table(rows: list[dict], caption: str) -> str:
    body = []
    for rec in rows:
        href = tel_href(rec.get("phone"))
        if rec.get("phone") and href:
            phone_html = f'<a href="{esc(href)}">{esc(rec["phone"])}</a>'
        elif rec.get("phone"):
            phone_html = esc(rec["phone"])
        else:
            phone_html = "—"
        restrictions = rec["restrictions"] or "—"
        name = rec["name"]
        if rec.get("detail_url"):
            name_html = f'<a href="{esc(rec["detail_url"])}">{esc(name)}</a>'
        else:
            name_html = esc(name)
        body.append(
            "        <tr>\n"
            f'          <td data-label="Name">{name_html}</td>\n'
            f'          <td data-label="Location">{esc(rec["location"])}</td>\n'
            f'          <td data-label="Reg #">{esc(rec["reg_number"])}</td>\n'
            f'          <td data-label="CSLB #">{esc(rec["cslb"])}</td>\n'
            f'          <td data-label="Phone">{phone_html}</td>\n'
            f'          <td data-label="Expires">{esc(rec["expires"])}</td>\n'
            f'          <td data-label="Restrictions">{esc(restrictions)}</td>\n'
            "        </tr>"
        )
    return f"""    <div class="table-wrap">
      <table class="roster-table">
        <caption>{esc(caption)}</caption>
        <thead>
          <tr>
            <th>Name</th>
            <th>Location</th>
            <th>Reg #</th>
            <th>CSLB #</th>
            <th>Phone</th>
            <th>Expires</th>
            <th>Restrictions</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(body)}
        </tbody>
      </table>
    </div>
"""


def main() -> dict:
    fl_path = SOURCES / "lic59asb.csv"
    ca_path = SOURCES / "acrulist.html"
    fl = parse_florida(fl_path)
    ca, ca_updated = parse_california(ca_path)
    ca_phones = sum(1 for r in ca if r.get("phone"))

    fl_by_occ: dict[str, int] = {}
    for r in fl:
        fl_by_occ[r["occupation_code"]] = fl_by_occ.get(r["occupation_code"], 0) + 1

    write_json(
        DATA / "florida.json",
        {
            "source_url": FL_CSV_URL,
            "layout_url": FL_LAYOUT_URL,
            "occupation_source_url": FL_README_URL,
            "status_source_url": FL_CODES_URL,
            "retrieved": UPDATED_ISO,
            "phone_field": "none — the DBPR asbestos licensee extract has no telephone column",
            "count": len(fl),
            "records": fl,
        },
    )
    write_json(
        DATA / "california.json",
        {
            "source_url": CA_LIST_URL,
            "search_url": CA_SEARCH_URL,
            "source_document_date": ca_updated,
            "retrieved": UPDATED_ISO,
            "count": len(ca),
            "records": ca,
        },
    )
    write_json(
        DATA / "nvlap.json",
        {
            "source_url": NVLAP_SEARCH,
            "program_page": NVLAP_LAP,
            "retrieved": UPDATED_ISO,
            "count": 0,
            "records": [],
            "note": (
                "NVLAP Directory search is an interactive Touchstone form. "
                "GET returns the form only. POST to directory.results with programId=2 "
                "(Asbestos Fiber Analysis) returned an application error (HTTP 200 error page). "
                "Zero laboratories transcribed. Do not invent lab names."
            ),
        },
    )
    write_json(
        DATA / "new-york.json",
        {
            "source_url": NY_BUREAU_URL,
            "listing_url": NY_LISTING_URL,
            "retrieved": UPDATED_ISO,
            "count": 0,
            "records": [],
            "note": (
                "NY DOL Asbestos Control Bureau points to an interactive Cognos report "
                "(Active Asbestos Contractors). Fetch of that report failed with a TLS unexpected EOF. "
                "Zero contractors transcribed."
            ),
        },
    )
    write_json(
        DATA / "kits.json",
        {
            "associate_tag": "radontestinde-20",
            "payee": "Stephen Shortell",
            "retrieved": UPDATED_ISO,
            "records": KITS,
        },
    )

    # --- pages ---
    (ROOT / "index.html").write_text(
        header(
            "index.html",
            "Find an NVLAP-accredited asbestos lab | Asbestos Lab Index",
            "Find an NVLAP-accredited lab that can analyze asbestos — then a licensed contractor if the report says to remove it. No invented labs.",
        )
        + f"""    <h1 class="page">Find an NVLAP-accredited lab that can analyze asbestos — then a licensed contractor if the report says to remove it.</h1>
    <p class="lede">Start with a laboratory NIST lists under Asbestos Fiber Analysis. If the report says the material must come out, hire a contractor your state actually licenses. This site transcribes official lists. It does not invent laboratories or phone numbers.</p>
    <p class="meta">Last updated {UPDATED_PT}. Florida and California contractor/consultant rows are live from official extracts. The NVLAP directory could not be scraped — use NIST’s search.</p>

    <div class="cards two cta-cards">
      <div class="card">
        <h3><a href="nvlap.html">NVLAP labs — official search</a></h3>
        <p>NIST’s National Voluntary Laboratory Accreditation Program is the federal list of labs accredited for asbestos fiber analysis. We could not download the directory as a table, so this site lists <strong>zero</strong> lab names of our own.</p>
        <a class="btn" href="nvlap.html">Open the NVLAP page</a>
      </div>
      <div class="card">
        <h3><a href="florida.html">Florida — {len(fl)} licenses from DBPR</a></h3>
        <p>Every row is from Florida’s asbestos licensee extract. Name, city, license, and type as published. The file has no phone column, so there are no tel: links on that table.</p>
        <a class="btn secondary" href="florida.html">Open Florida licenses</a>
      </div>
      <div class="card">
        <h3><a href="california.html">California — {len(ca)} Cal/OSHA registrants</a></h3>
        <p>Transcribed from Cal/OSHA’s Asbestos Registrants’ Database (updated {esc(ca_updated or "see source")}). Phones are shown only when they appear on that list.</p>
        <a class="btn secondary" href="california.html">Open California registrants</a>
      </div>
    </div>
    <p><a href="states.html">All states</a> · <a href="ny.html">New York official listing</a> (rows not transcribed) · <a href="when-to-test.html">When EPA says to test</a>.</p>

    <div class="flow">
      <article>
        <span class="step">1. Analyze</span>
        <h2>Use an NVLAP-accredited lab</h2>
        <p>EPA points schools to NVLAP and recommends NVLAP (or another accreditation body) for other buildings. <a href="nvlap.html">Search the official directory</a>.</p>
      </article>
      <article>
        <span class="step">2. Read the report</span>
        <h2>Leave intact material alone</h2>
        <p>EPA says not to test undamaged material you will not disturb. A kit is not a licensed inspector. <a href="when-to-test.html">When to test, with citations</a>.</p>
      </article>
      <article>
        <span class="step">3. Remove only if needed</span>
        <h2>Hire a licensed contractor</h2>
        <p>If the report says to remove it, use a state-licensed asbestos contractor — not the same firm that only sold you a kit. <a href="florida.html">Florida</a> · <a href="california.html">California</a>.</p>
      </article>
    </div>

    <h2>Mail-in kits</h2>
    <p>Disclosed Schneider / SLGi kit links live on the <a href="kits.html">kits page</a> only. A kit is not an NVLAP laboratory listing and not a licensed abatement contractor. Kit links are not placed on roster tables.</p>

    <div class="callout">
      <h2>What this site will not do</h2>
      <p>We do not invent laboratories, contractors, phone numbers, or certifications. If a field is not on the official source, it is omitted. We do not run click-to-call tracking or Exclusive Live Calls. Official sources are linked on every page.</p>
    </div>
"""
        + footer(),
        encoding="utf-8",
    )

    (ROOT / "nvlap.html").write_text(
        header(
            "nvlap.html",
            "NVLAP asbestos fiber analysis labs | Asbestos Lab Index",
            "Use NIST’s official NVLAP directory to find laboratories accredited for asbestos fiber analysis. This site lists zero invented labs.",
        )
        + f"""    <h1 class="page">NVLAP-accredited asbestos fiber analysis laboratories</h1>
    <p class="lede">The official list is NIST’s National Voluntary Laboratory Accreditation Program directory. This page lists <strong>zero</strong> laboratory names because the search form could not be downloaded as a table.</p>
    <p class="meta">Attempted {UPDATED_PT}. Program to select in the directory: Asbestos Fiber Analysis.</p>

    <div class="callout">
      <h2>Use the official search</h2>
      <p>On the NVLAP directory, choose <strong>Asbestos Fiber Analysis</strong> under Program, then search. That is the live accreditation list.</p>
      <p><a class="btn" href="{esc(NVLAP_SEARCH)}">Open the NVLAP directory search</a></p>
    </div>

    <h2>Why NVLAP</h2>
    <p>AHERA required NIST to accredit laboratories that analyze air and bulk samples for asbestos. EPA states that asbestos samples collected in schools for AHERA-related purposes must be analyzed only by a NVLAP-accredited laboratory, and EPA also recommends NVLAP or another accreditation body for samples from non-school buildings. Source: <a href="{esc(EPA_PRO_URL)}">EPA, Asbestos Professionals</a> (page last updated 25 March 2026).</p>
    <p>Program description: <a href="{esc(NVLAP_LAP)}">NIST, Asbestos Fiber Analysis LAP</a>.</p>

    <h2>What we tried</h2>
    <ul>
      <li>GET of the search page returned the form, not a lab table.</li>
      <li>POST to <code>directory.results</code> with programId 2 (Asbestos Fiber Analysis) returned an application error page.</li>
      <li>We did not copy lab names from third-party websites or from old printed NVLAP directories.</li>
    </ul>
    <p>JSON for this fetch (empty records array): <a href="data/nvlap.json">data/nvlap.json</a>.</p>
"""
        + footer(),
        encoding="utf-8",
    )

    contractor_codes = {"CJC"}
    business_codes = {"ZA"}
    consultant_codes = {"AX", "AF", "DD", "EA", "IA"}
    other_people = {"FO"}
    training = {"CRS1", "CRS2", "PVDR"}
    fl_contractors = [r for r in fl if r["occupation_code"] in contractor_codes]
    fl_business = [r for r in fl if r["occupation_code"] in business_codes]
    fl_consult = [r for r in fl if r["occupation_code"] in consultant_codes]
    fl_fo = [r for r in fl if r["occupation_code"] in other_people]
    fl_train = [r for r in fl if r["occupation_code"] in training]
    leftover = [
        r
        for r in fl
        if r["occupation_code"]
        not in contractor_codes | business_codes | consultant_codes | other_people | training
    ]

    occ_list = "".join(
        f"<li><code>{esc(code)}</code> — {esc(OCCUPATION.get(code, code))}: {n}</li>"
        for code, n in sorted(fl_by_occ.items(), key=lambda kv: (-kv[1], kv[0]))
    )

    leftover_html = fl_table(leftover, f"Other occupation codes in the extract ({len(leftover)})") if leftover else ""

    (ROOT / "florida.html").write_text(
        header(
            "florida.html",
            f"Florida asbestos licenses — {len(fl)} rows | Asbestos Lab Index",
            "Florida DBPR asbestos contractors, consultants, and related licenses transcribed from the official lic59asb.csv extract. No invented names or phones.",
            wide=True,
        )
        + f"""    <h1 class="page">Florida asbestos licenses</h1>
    <p class="lede">{len(fl)} rows transcribed from the Florida Department of Business and Professional Regulation asbestos licensee extract. Name, city, license, and type as published. The extract has no telephone field, so this table has no tel: links.</p>
    <p class="meta">Source file: <a href="{esc(FL_CSV_URL)}">lic59asb.csv</a>. Column layout: <a href="{esc(FL_LAYOUT_URL)}">DBPR asbestos public records</a>. Occupation codes: <a href="{esc(FL_README_URL)}">DBPR readme.pdf</a>. Status codes: <a href="{esc(FL_CODES_URL)}">Understanding DBPR Codes</a>. Retrieved {UPDATED_PT}. DBPR states this download includes active, inactive, and voluntarily inactive licensees; null and void, delinquent, and involuntarily inactive records are omitted at the source.</p>

    <div class="callout compact">
      <h2>How to read this table</h2>
      <p>Primary status <strong>C</strong> is Current. Secondary <strong>A</strong> is Active and <strong>I</strong> is Inactive. A blank secondary status is shown as Current only — we do not fill it in. Doing-business-as is blank on many personal licenses. Out-of-state cities appear when Florida licensed that person or firm. Training-course and financial-responsible-officer rows are not abatement contractors; they are still in the official file, so they are listed in later sections.</p>
    </div>

    <h2>Counts by occupation code</h2>
    <ul>
{occ_list}    </ul>
    <p>Machine-readable copy: <a href="data/florida.json">data/florida.json</a>. Each record includes <code>source_url</code>.</p>

    <h2>Asbestos contractors ({len(fl_contractors)})</h2>
    <p>Occupation code CJC — Asbestos Contractor.</p>
{fl_table(fl_contractors, f"Florida asbestos contractors (CJC), {len(fl_contractors)} rows")}
    <h2>Asbestos businesses ({len(fl_business)})</h2>
    <p>Occupation code ZA — Asbestos Business. A business qualified by a contractor or consultant.</p>
{fl_table(fl_business, f"Florida asbestos businesses (ZA), {len(fl_business)} rows")}
    <h2>Asbestos consultants ({len(fl_consult)})</h2>
    <p>Occupation codes AX, AF, DD, EA, IA — consultant classes from the DBPR readme.</p>
{fl_table(fl_consult, f"Florida asbestos consultants, {len(fl_consult)} rows")}
    <h2>Financial responsible officers ({len(fl_fo)})</h2>
    <p>Occupation code FO. These are not listed here as abatement contractors.</p>
{fl_table(fl_fo, f"Florida financial responsible officers (FO), {len(fl_fo)} rows")}
    <h2>Training courses and providers ({len(fl_train)})</h2>
    <p>Occupation codes CRS1, CRS2, and PVDR. These are courses and providers, not removal contractors.</p>
{fl_table(fl_train, f"Florida asbestos training rows, {len(fl_train)} rows")}
{leftover_html}"""
        + footer(),
        encoding="utf-8",
    )

    (ROOT / "california.html").write_text(
        header(
            "california.html",
            f"California Cal/OSHA asbestos registrants — {len(ca)} | Asbestos Lab Index",
            "Cal/OSHA Asbestos Registrants’ Database transcribed from the official full list. Phones only when present on that list.",
            wide=True,
        )
        + f"""    <h1 class="page">California Cal/OSHA asbestos registrants</h1>
    <p class="lede">{len(ca)} employers transcribed from Cal/OSHA’s Asbestos Registrants’ Database. Names, locations, registration numbers, CSLB numbers, expiration dates, and phones are copied from that table. Tel: links appear only when a phone number is on the source.</p>
    <p class="meta">Source: <a href="{esc(CA_LIST_URL)}">acrulist.asp</a> (Cal/OSHA states last updated {esc(ca_updated or "see source")}). Search form: <a href="{esc(CA_SEARCH_URL)}">acrusearch.html</a>. Retrieved {UPDATED_PT}. {ca_phones} rows include a phone number on the list; the rest have no usable number in the source (blank or a dash).</p>

    <div class="callout compact">
      <h2>What this list is</h2>
      <p>Cal/OSHA says this is a list of asbestos contractors and other employers registered with the Asbestos Contractors’ Registration Unit. Listing does not assure that a contractor license is current and active; Cal/OSHA tells you to check CSLB. Some rows are public agencies marked EXEMPT on the CSLB field. Restrictions that say “See Detail” are not invented here — follow the registrant’s detail link.</p>
    </div>
    <p>Machine-readable copy: <a href="data/california.json">data/california.json</a>. Each record includes <code>source_url</code>. Names link to Cal/OSHA’s own detail page when the list provided a registration link.</p>
{ca_table(ca, f"Cal/OSHA asbestos registrants, {len(ca)} rows")}
"""
        + footer(),
        encoding="utf-8",
    )

    (ROOT / "ny.html").write_text(
        header(
            "ny.html",
            "New York licensed asbestos contractors | Asbestos Lab Index",
            "New York State Department of Labor Asbestos Control Bureau. Official contractor listing could not be downloaded as a table. Zero invented contractors.",
        )
        + f"""    <h1 class="page">New York asbestos contractors</h1>
    <p class="lede">The New York State Department of Labor Asbestos Control Bureau licenses asbestos contractors under Industrial Code Rule 56. This page lists <strong>zero</strong> contractor names because the official listing is an interactive report that we could not download as rows.</p>
    <p class="meta">Attempted {UPDATED_PT}.</p>

    <div class="callout">
      <h2>Use the official listing</h2>
      <p>Start at the bureau page, then open Asbestos Contractors Listing (Active Asbestos Contractors report).</p>
      <p><a class="btn" href="{esc(NY_BUREAU_URL)}">NY DOL Asbestos Control Bureau</a></p>
      <p><a href="{esc(NY_LISTING_URL)}">Active Asbestos Contractors report</a> (Cognos). Fetch of that URL failed here with a TLS error. We did not substitute a third-party directory.</p>
    </div>

    <h2>What the bureau page does say</h2>
    <p>Industrial Code Rule 56 requires licensing of contractors, certification of persons on asbestos projects, notifications for large projects, surveys before work, and specified abatement methods. For general questions DOL publishes <a href="mailto:labor.sm.dosh@labor.ny.gov">labor.sm.dosh@labor.ny.gov</a> and <a href="mailto:labor.sm.AskDOL.asbestos.mold@labor.ny.gov">labor.sm.AskDOL.asbestos.mold@labor.ny.gov</a> on that page. District office phone numbers on the bureau page belong to DOL offices, not to private contractors, so they are not copied into a contractor roster.</p>
    <p>JSON (empty records): <a href="data/new-york.json">data/new-york.json</a>.</p>
"""
        + footer(),
        encoding="utf-8",
    )

    kit_articles = []
    for k in KITS:
        kit_articles.append(
            f"""      <article>
        <h2>{esc(k["title"])} <span class="paid">(paid link)</span></h2>
        <p>Listed brand on Amazon: {esc(k["brand"])}. ASIN {esc(k["asin"])}. Title source: {esc(k["title_source"])}. We do not invent kit specifications here.</p>
        <p><a href="{esc(k["url"])}">Amazon product page for {esc(k["asin"])} (paid link)</a></p>
      </article>"""
        )

    kits_extra = f"""      <div class="assoc">
        <p><strong>Amazon Associates disclosure.</strong> As an Amazon Associate I earn from qualifying purchases. Paid links on this page use associate tag <code>radontestinde-20</code>. Payee: Stephen Shortell.</p>
      </div>
"""

    (ROOT / "kits.html").write_text(
        header(
            "kits.html",
            "Schneider asbestos test kits (paid links) | Asbestos Lab Index",
            "Disclosed Amazon Associates links to Schneider / SLGi asbestos test kits. A kit is not an NVLAP lab and not a licensed abatement contractor.",
        )
        + f"""    <h1 class="page">Mail-in asbestos kits</h1>
    <p class="lede">These are Schneider Laboratories Global (SLGi) kits sold on Amazon. Each link is a <strong>paid link</strong>. A kit is not a NVLAP laboratory listing and not a licensed abatement contractor.</p>
    <p class="meta">Associate tag <code>radontestinde-20</code>. Payee Stephen Shortell. Titles taken from Amazon listings retrieved {UPDATED_PT}. We do not invent specifications.</p>

    <div class="callout">
      <h2>Read this before you buy a kit</h2>
      <p>EPA says the only way to be sure a material contains asbestos is to have it tested by a qualified laboratory, and that samples should be taken by a properly trained and accredited asbestos professional. EPA does not recommend taking samples yourself. A mail-in kit does not make you that professional, does not put a lab on the NVLAP directory, and does not license anyone to remove asbestos. If a report says to remove material, hire a contractor your state licenses. Sources: <a href="when-to-test.html">When to test</a>.</p>
    </div>

    <div class="kit-list">
{chr(10).join(kit_articles)}
    </div>

    <p>Kit links are not placed on NVLAP, Florida, California, or New York roster tables.</p>
"""
        + footer(kits_extra),
        encoding="utf-8",
    )

    (ROOT / "when-to-test.html").write_text(
        header(
            "when-to-test.html",
            "When to test for asbestos in the home (EPA) | Asbestos Lab Index",
            "EPA guidance on when to test suspect asbestos in a home, when to leave it alone, and when to hire a licensed contractor.",
        )
        + f"""    <h1 class="page">When to test asbestos in the home</h1>
    <p class="lede">EPA’s rule of thumb: if the material is in good condition and you will not disturb it, leave it alone. Test when it is damaged, or before a renovation that would disturb it — using a qualified laboratory, with samples taken by a trained professional.</p>
    <p class="meta">Citations retrieved {UPDATED_PT}.</p>

    <h2>What EPA says</h2>
    <p>From <a href="{esc(EPA_HOME_URL)}">How do I know if I have asbestos in my home</a> (EPA, last updated 2 April 2026):</p>
    <blockquote>
      <p>The only way to be sure whether a material contains asbestos is to have it tested by a qualified laboratory. EPA only recommends testing suspect materials if they are damaged (fraying, crumbling) or if you are planning a renovation that would disturb the suspect material. Samples should be taken by a properly trained and accredited asbestos professional (inspector).</p>
    </blockquote>

    <p>From <a href="{esc(EPA_PROTECT_URL)}">Protect Your Family from Exposures to Asbestos</a> (EPA, last updated 25 June 2026):</p>
    <ul>
      <li>You generally cannot tell whether a material contains asbestos by looking at it, unless it is labeled. If in doubt, treat it as asbestos and leave it alone.</li>
      <li>If building materials are not damaged and will not be disturbed, EPA says you do not need to have the home tested. Material in good condition that will not be disturbed should be left alone.</li>
      <li>A trained and accredited professional should take samples. Taking samples yourself is not recommended; done incorrectly, sampling can be more hazardous than leaving the material alone.</li>
      <li>Do not dust, sweep, or vacuum debris that may contain asbestos. Do not saw, sand, scrape, or drill holes in suspect material.</li>
      <li>Repair or removal of more than slightly damaged material should be done by a trained and accredited asbestos professional. Improper removal can increase exposure.</li>
    </ul>

    <h2>Inspector versus contractor</h2>
    <p>EPA describes two main kinds of accredited professionals: inspectors (assess, sample, advise) and contractors (repair or remove). EPA says to avoid a conflict of interest: the professional hired to assess should not be connected with the firm that does the removal.</p>
    <p>Federal law does not require training and accreditation for work in detached single-family homes, but some states and localities do. EPA still tells homeowners to hire trained, accredited workers. State agencies have the listings. This site transcribes some of those lists: <a href="florida.html">Florida</a>, <a href="california.html">California</a>, <a href="ny.html">New York official listing</a>.</p>

    <h2>Where the laboratory fits</h2>
    <p>EPA’s asbestos-professionals page (last updated 25 March 2026) points to NIST NVLAP for labs that analyze bulk and air samples. School AHERA samples must go to a NVLAP-accredited lab. For other buildings EPA recommends NVLAP or another accreditation body. <a href="nvlap.html">NVLAP search</a>.</p>
    <p>A consumer mail-in kit is not that accreditation list and is not a removal license. See <a href="kits.html">kits (paid links)</a>.</p>

    <div class="cite">
      <h2>Sources</h2>
      <ol>
        <li><a href="{esc(EPA_HOME_URL)}">EPA, How do I know if I have asbestos in my home</a> — last updated 2 April 2026.</li>
        <li><a href="{esc(EPA_PROTECT_URL)}">EPA, Protect Your Family from Exposures to Asbestos</a> — last updated 25 June 2026.</li>
        <li><a href="{esc(EPA_PRO_URL)}">EPA, Asbestos Professionals</a> — last updated 25 March 2026.</li>
      </ol>
    </div>
"""
        + footer(),
        encoding="utf-8",
    )

    (ROOT / "about.html").write_text(
        header(
            "about.html",
            "About Asbestos Lab Index | Shortell Designs",
            "Asbestos Lab Index is a static directory by Shortell Designs. Official lists only. No invented labs or phones.",
        )
        + f"""    <h1 class="page">About Asbestos Lab Index</h1>
    <p class="lede">A static U.S. directory by Shortell Designs. Find an NVLAP-accredited lab that can analyze asbestos, then a licensed contractor if the report says to remove it. We do not invent records.</p>
    <p class="meta">First version {UPDATED_PT}.</p>

    <h2>What we are</h2>
    <p>Asbestos Lab Index is not a government website, not a laboratory, and not an abatement contractor. It transcribes official federal and state lists and cites EPA on when to test.</p>

    <h2>Methodology</h2>
    <ul>
      <li>Every roster row comes from an official file or table named on that page. Each JSON record has a <code>source_url</code>.</li>
      <li>If a field is missing on the source — including telephone numbers on Florida’s DBPR extract — we omit it. We do not fill gaps from Google, Yelp, or company websites.</li>
      <li>NVLAP and New York listings that could not be downloaded as tables are linked, with zero invented names.</li>
      <li>Amazon kit links appear only on the kits page, marked (paid link). They are not placed on roster tables.</li>
      <li>No Exclusive Live Calls, no click-to-call tracking pixels, no invented click-to-call numbers.</li>
    </ul>
    <p>See <a href="README.md">README.md</a> and <a href="SOURCES.md">SOURCES.md</a>.</p>

    <h2>Commission disclosure</h2>
    <p>Amazon Associates paid links may appear on <a href="kits.html">kits.html</a>. Tag <code>radontestinde-20</code>. Payee: Stephen Shortell. Laboratory and contractor listings are not advertisements.</p>

    <h2>Byline</h2>
    <p>Shortell Designs.</p>
"""
        + footer(),
        encoding="utf-8",
    )

    (ROOT / "states.html").write_text(
        header(
            "states.html",
            "State asbestos directories | Asbestos Lab Index",
            "Florida and California live from official extracts. NVLAP is national. New York official listing linked. Other states when an official list can be transcribed.",
        )
        + f"""    <h1 class="page">State directory</h1>
    <p class="lede">Live pages are built from official lists. If we cannot download rows, we link the official search and list no names of our own.</p>
    <p class="meta">Last updated {UPDATED}.</p>

    <ul class="state-list">
      <li><span><a href="nvlap.html"><strong>United States — NVLAP labs</strong></a> — official NIST search; 0 labs transcribed here</span> <span class="badge">Search</span></li>
      <li><span><a href="florida.html"><strong>Florida</strong></a> — {len(fl)} licenses from DBPR lic59asb.csv (no phones in the file)</span> <span class="badge">Live</span></li>
      <li><span><a href="california.html"><strong>California</strong></a> — {len(ca)} Cal/OSHA asbestos registrants</span> <span class="badge">Live</span></li>
      <li><span><a href="ny.html"><strong>New York</strong></a> — DOL Asbestos Control Bureau listing; 0 contractors transcribed (interactive report)</span> <span class="badge soon">Official link</span></li>
      <li><span>Other states</span> <span class="badge soon">Coming soon</span></li>
    </ul>

    <h2>How other states will be added</h2>
    <p>We will not publish a contractor or lab table until we can transcribe a current official list, or honestly say that we could not. EPA’s asbestos professionals page points to NVLAP for laboratories and to state agencies for accredited people.</p>
"""
        + footer(),
        encoding="utf-8",
    )

    return {
        "florida": len(fl),
        "florida_by_occ": fl_by_occ,
        "california": len(ca),
        "california_phones": ca_phones,
        "ca_updated": ca_updated,
        "nvlap": 0,
        "new_york": 0,
        "kits": len(KITS),
    }


if __name__ == "__main__":
    stats = main()
    print(json.dumps(stats, indent=2))
