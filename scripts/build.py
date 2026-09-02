#!/usr/bin/env python3
"""Build Asbestos Lab Index static pages from archived official sources."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from html import escape, unescape
from pathlib import Path

ROOT = Path("/workspace/asbestos-lab-index")
DATA = ROOT / "data"
SOURCES = DATA / "sources"
RETRIEVED = "30 August 2026"
RETRIEVED_ISO = "2026-08-30"

NVLAP_SEARCH = "https://www-s.nist.gov/niws/index.cfm?event=directory.search"
NVLAP_PROGRAM = "https://www.nist.gov/nvlap/asbestos-fiber-analysis-lap"
FL_CSV_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/lic59asb.csv"
FL_LAYOUT = "https://www2.myfloridalicense.com/asbestos-contractors-and-consultants/public-records/"
FL_CODES = "https://www2.myfloridalicense.com/about-us/understanding-dbpr-codes/"
FL_VERIFY = "https://www.myfloridalicense.com/wl11.asp?mode=0&SID="
CA_LIST = "https://www.dir.ca.gov/databases/doshacru/acrulist.asp"
CA_SEARCH = "https://www.dir.ca.gov/Databases/doshacru/acrusearch.html"
NY_ACB = "https://dol.ny.gov/asbestos-control-bureau"
NY_OLD_LIST = "https://labor.ny.gov/workerprotection/safetyhealth/active-asbestos-contractor-list.shtm"
NY_DOH_SAMPLE = "https://www.health.ny.gov/environmental/indoors/asbestos/sampling.htm"
EPA_HOME = "https://www.epa.gov/asbestos/protect-your-family-exposures-asbestos"

OCC_LABEL = {
    "AX": "Asbestos Consultant",
    "AF": "Asbestos Consultant (AF)",
    "DD": "Asbestos Consultant (Doctoral Degree)",
    "EA": "Asbestos Consultant (Engineer)",
    "IA": "Asbestos Consultant (Industrial Hygiene)",
    "CJC": "Asbestos Contractor",
    "ZA": "Asbestos Business",
    "FO": "Financial Responsible Officer",
    "PVDR": "Asbestos Course Provider",
    "CRS1": "Asbestos Basic Initial Training Course",
    "CRS2": "Asbestos Refresher Training Course",
}
CONSULTANT_OCC = {"AX", "AF", "DD", "EA", "IA"}
COUNTY = {
    "11": "Alachua", "12": "Baker", "13": "Bay", "14": "Bradford", "15": "Brevard",
    "16": "Broward", "17": "Calhoun", "18": "Charlotte", "19": "Citrus", "20": "Clay",
    "21": "Collier", "22": "Columbia", "23": "Dade", "24": "DeSoto", "25": "Dixie",
    "26": "Duval", "27": "Escambia", "28": "Flagler", "29": "Franklin", "30": "Gadsden",
    "31": "Gilchrist", "32": "Glades", "33": "Gulf", "34": "Hamilton", "35": "Hardee",
    "36": "Hendry", "37": "Hernando", "38": "Highlands", "39": "Hillsborough", "40": "Holmes",
    "41": "Indian River", "42": "Jackson", "43": "Jefferson", "44": "Lafayette", "45": "Lake",
    "46": "Lee", "47": "Leon", "48": "Levy", "49": "Liberty", "50": "Madison",
    "51": "Manatee", "52": "Marion", "53": "Martin", "54": "Monroe", "55": "Nassau",
    "56": "Okaloosa", "57": "Okeechobee", "58": "Orange", "59": "Osceola", "60": "Palm Beach",
    "61": "Pasco", "62": "Pinellas", "63": "Polk", "64": "Putnam", "65": "St. Johns",
    "66": "St. Lucie", "67": "Santa Rosa", "68": "Sarasota", "69": "Seminole", "70": "Sumter",
    "71": "Suwannee", "72": "Taylor", "73": "Union", "74": "Volusia", "75": "Wakulla",
    "76": "Walton", "77": "Washington", "78": "Unknown", "99": "Unknown",
}
PRIMARY_STATUS = {"C": "Current", "P": "Probation", "S": "Suspended"}
SECONDARY_STATUS = {"A": "Active", "I": "Inactive", "": "unknown"}

NAV = [
    ("index.html", "Home"),
    ("nvlap.html", "NVLAP labs"),
    ("florida.html", "Florida"),
    ("california.html", "California"),
    ("new-york.html", "New York"),
    ("when-to-test.html", "When to test"),
    ("states.html", "States"),
    ("about.html", "About"),
]


def county_name(code: str) -> str:
    code = (code or "").strip()
    if code in COUNTY:
        return COUNTY[code]
    try:
        n = int(code)
    except ValueError:
        return "unknown"
    if 701 <= n <= 799 or n == 79:
        return "Out of State"
    if 801 <= n <= 899 or n == 80:
        return "Foreign"
    return "unknown"


def tel_href(phone: str | None) -> str | None:
    if not phone:
        return None
    raw = phone.strip()
    if raw in {"", "-", "—", "unknown", "n/a", "N/A"}:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        return f"tel:+{digits}"
    if len(digits) == 10:
        return f"tel:+1{digits}"
    return None


def phone_cell(phone: str | None, label: str = "Phone") -> str:
    if not phone or str(phone).strip() in {"", "-", "—"}:
        return f'<td class="phone unknown" data-label="{escape(label)}">unknown</td>'
    href = tel_href(phone)
    shown = escape(str(phone).strip())
    if href:
        return f'<td class="phone" data-label="{escape(label)}"><a href="{href}">{shown}</a></td>'
    return f'<td class="phone" data-label="{escape(label)}">{shown}</td>'


def dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def header(current: str) -> str:
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        items.append(f'        <li><a href="{href}"{cur}>{escape(label)}</a></li>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{title}}</title>
  <meta name="description" content="{{description}}">
  <link rel="stylesheet" href="css/site.css">
</head>
<body>
  <a class="skip" href="#content">Skip to content</a>
  <header class="site">
    <div class="brand">
      <h1><a href="index.html">Asbestos Lab Index</a></h1>
      <p class="tag">Analyze first, abate second. No rankings.</p>
    </div>
    <nav class="primary" aria-label="Primary">
      <ul>
{chr(10).join(items)}
      </ul>
    </nav>
  </header>
"""


FOOTER = """  <footer class="site">
    <div class="inner">
      <p>Stephen Shortell</p>
    </div>
  </footer>
  <script>
  (function () {
    document.querySelectorAll("[data-filter]").forEach(function (input) {
      input.addEventListener("input", function () {
        var q = this.value.toLowerCase();
        var table = document.getElementById(this.getAttribute("data-filter"));
        if (!table) return;
        table.querySelectorAll("tbody tr").forEach(function (tr) {
          tr.hidden = q && tr.textContent.toLowerCase().indexOf(q) === -1;
        });
      });
    });
  })();
  </script>
</body>
</html>
"""


def page(path: str, title: str, description: str, current: str, body: str, wide: bool = False) -> None:
    head = header(current).replace("{title}", escape(title)).replace("{description}", escape(description))
    main_class = ' class="wide"' if wide else ""
    html = head + f'  <main id="content"{main_class}>\n' + body + "  </main>\n" + FOOTER
    (ROOT / path).write_text(html, encoding="utf-8")


def parse_nvlap() -> list[dict]:
    html = (SOURCES / "nvlap-directory-results.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'id="tblSearchResults"[\s\S]*?</table>', html)
    if not m:
        raise SystemExit("NVLAP results table not found")
    rows = re.findall(
        r"<tr>\s*<td><a href=\"([^\"]+)\">([^<]+)</a></td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>",
        m.group(0),
    )
    records = []
    for href, code, name, city, state, country in rows:
        records.append(
            {
                "nvlap_lab_code": unescape(code).strip(),
                "name": unescape(name).strip(),
                "city": unescape(city).strip() or "unknown",
                "state": unescape(state).strip() or "unknown",
                "country": unescape(country).strip() or "unknown",
                "phone": "unknown",
                "program": "Asbestos Fiber Analysis",
                "source_url": NVLAP_SEARCH,
            }
        )
    records.sort(key=lambda r: (r["country"], r["state"], r["city"], r["name"]))
    return records


def parse_florida() -> tuple[list[dict], list[dict], Counter, int]:
    path = SOURCES / "lic59asb.csv"
    rows = list(csv.reader(path.open(encoding="utf-8-sig", newline="")))
    occ_counts = Counter(r[1] for r in rows)
    contractors = []
    consultants = []
    for r in rows:
        occ = r[1].strip()
        rec = {
            "name": r[2].strip() or "unknown",
            "doing_business_as": r[3].strip() or "unknown",
            "city": r[8].strip() or "unknown",
            "state": r[9].strip() or "unknown",
            "zip": r[10].strip() or "unknown",
            "county": county_name(r[11]),
            "license": (r[20].strip() or r[12].strip() or "unknown"),
            "occupation_code": occ,
            "occupation": OCC_LABEL.get(occ, occ),
            "primary_status": PRIMARY_STATUS.get(r[13].strip(), r[13].strip() or "unknown"),
            "secondary_status": SECONDARY_STATUS.get(r[14].strip(), r[14].strip() or "unknown"),
            "expiration": r[17].strip() or "unknown",
            "phone": "unknown",
            "source_url": FL_CSV_URL,
        }
        if occ == "CJC":
            contractors.append(rec)
        elif occ in CONSULTANT_OCC:
            consultants.append(rec)
    contractors.sort(key=lambda r: (r["state"], r["city"], r["name"]))
    consultants.sort(key=lambda r: (r["state"], r["city"], r["name"]))
    return contractors, consultants, occ_counts, len(rows)


def parse_california() -> tuple[list[dict], str]:
    html = (SOURCES / "ca-acrulist.html").read_text(encoding="utf-8", errors="replace")
    updated = "unknown"
    m = re.search(r"last updated on ([^<]+)", html, re.I)
    if m:
        updated = m.group(1).strip().rstrip("-").strip()
    records = []
    parts = re.split(r"<tr[^>]*>", html, flags=re.I)
    for p in parts:
        if "acrudetails" not in p.lower():
            continue
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", p, flags=re.I)
        if len(cells) < 7:
            continue

        def clean(x: str) -> str:
            x = re.sub(r"<br\s*/?>", " ", x, flags=re.I)
            x = re.sub(r"<[^>]+>", "", x)
            x = unescape(x).replace("\xa0", " ")
            return " ".join(x.split())

        cleaned = [clean(c) for c in cells]
        loc = cleaned[4]
        city, state = loc, "unknown"
        ms = re.search(r"^(.*)\s+([A-Z]{2})$", loc)
        if ms:
            city, state = ms.group(1).strip() or "unknown", ms.group(2)
        phone = cleaned[6] if cleaned[6] not in {"", "-"} else "unknown"
        records.append(
            {
                "name": cleaned[2] or "unknown",
                "registration_number": cleaned[0] or "unknown",
                "cslb_number": cleaned[1] or "unknown",
                "restrictions": cleaned[3] or "unknown",
                "city": city,
                "state": state,
                "expires": cleaned[5] or "unknown",
                "phone": phone,
                "source_url": CA_LIST,
            }
        )
    records.sort(key=lambda r: (r["state"], r["city"], r["name"]))
    return records, updated


def ny_offices() -> list[dict]:
    # Transcribed from https://dol.ny.gov/asbestos-control-bureau retrieved 30 August 2026.
    rows = [
        {
            "name": "Albany District, Asbestos Control Bureau",
            "counties": "Albany, Clinton, Columbia, Dutchess, Essex, Fulton, Greene, Montgomery, Orange, Putnam, Rockland, Rensselaer, Saratoga, Schenectady, Schoharie, Sullivan, Ulster, Warren, Washington",
            "address": "State Office Campus, Room 166, Albany, NY 12226",
            "city": "Albany",
            "phone": "(518) 457-2072",
            "source_url": NY_ACB,
        },
        {
            "name": "Buffalo District, Asbestos Control Bureau",
            "counties": "Cattaraugus, Chautauqua, Erie, Genesee, Livingston, Monroe, Niagara, Ontario, Orleans, Wayne, Wyoming, Yates",
            "address": "295 Main St. Suite 905, Buffalo, NY 14203",
            "city": "Buffalo",
            "phone": "(716) 847-7126",
            "source_url": NY_ACB,
        },
        {
            "name": "New York City District, Asbestos Control Bureau",
            "counties": "Bronx, Kings, Nassau, New York, Queens, Richmond, Suffolk, Westchester",
            "address": "PO Box 15047, Albany, NY 12212",
            "city": "Albany",
            "phone": "(212) 775-3532",
            "source_url": NY_ACB,
        },
        {
            "name": "Syracuse District, Asbestos Control Bureau",
            "counties": "Allegany, Broome, Cayuga, Chemung, Chenango, Cortland, Delaware, Franklin, Hamilton, Herkimer, Jefferson, Lewis, Madison, Oneida, Onondaga, Oswego, Otsego, St. Lawrence, Schuyler, Seneca, Steuben, Tioga, Tompkins",
            "address": "450 S. Salina Street Room 204, Syracuse, NY 13202",
            "city": "Syracuse",
            "phone": "(315) 479-3215",
            "source_url": NY_ACB,
        },
        {
            "name": "Asbestos Notifications and License and Certification Unit",
            "counties": "unknown",
            "address": "State Office Campus, Room 161A, Albany, NY 12226",
            "city": "Albany",
            "phone": "(518) 457-2735",
            "source_url": NY_ACB,
        },
    ]
    return rows


def table(caption: str, table_id: str, headers: list[str], body_rows: list[str]) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in headers)
    return f"""    <div class="filter">
      <label for="q-{table_id}">Filter this table</label>
      <input id="q-{table_id}" type="search" data-filter="{table_id}" placeholder="Name, city, license…">
    </div>
    <div class="table-wrap">
      <table class="dir-table labs-table" id="{table_id}">
        <caption>{escape(caption)}</caption>
        <thead>
          <tr>{th}</tr>
        </thead>
        <tbody>
{chr(10).join(body_rows)}
        </tbody>
      </table>
    </div>
"""


def nvlap_rows(records: list[dict]) -> list[str]:
    out = []
    for r in records:
        out.append(
            "<tr>"
            f'<td class="name" data-label="Laboratory">{escape(r["name"])}</td>'
            f'<td data-label="NVLAP code">{escape(r["nvlap_lab_code"])}</td>'
            f'<td data-label="City">{escape(r["city"])}</td>'
            f'<td data-label="State">{escape(r["state"])}</td>'
            f'<td data-label="Country">{escape(r["country"])}</td>'
            + phone_cell(None)
            + "</tr>"
        )
    return out


def fl_rows(records: list[dict]) -> list[str]:
    out = []
    for r in records:
        dba = r["doing_business_as"]
        out.append(
            "<tr>"
            f'<td class="name" data-label="Name">{escape(r["name"])}</td>'
            f'<td data-label="Doing business as">{escape(dba)}</td>'
            f'<td data-label="City">{escape(r["city"])}</td>'
            f'<td data-label="State">{escape(r["state"])}</td>'
            f'<td data-label="License">{escape(r["license"])}</td>'
            f'<td data-label="Occupation">{escape(r["occupation"])}</td>'
            f'<td data-label="Status">{escape(r["primary_status"])}'
            f' / {escape(r["secondary_status"])}</td>'
            + phone_cell(None)
            + "</tr>"
        )
    return out


def ca_rows(records: list[dict]) -> list[str]:
    out = []
    for r in records:
        out.append(
            "<tr>"
            f'<td class="name" data-label="Employer / DBA">{escape(r["name"])}</td>'
            f'<td data-label="City">{escape(r["city"])}</td>'
            f'<td data-label="State">{escape(r["state"])}</td>'
            f'<td data-label="Reg #">{escape(r["registration_number"])}</td>'
            f'<td data-label="CSLB #">{escape(r["cslb_number"])}</td>'
            f'<td data-label="Expires">{escape(r["expires"])}</td>'
            + phone_cell(r["phone"] if r["phone"] != "unknown" else None)
            + "</tr>"
        )
    return out


def ny_rows(records: list[dict]) -> list[str]:
    out = []
    for r in records:
        out.append(
            "<tr>"
            f'<td class="name" data-label="Office">{escape(r["name"])}</td>'
            f'<td data-label="City">{escape(r["city"])}</td>'
            f'<td data-label="Address">{escape(r["address"])}</td>'
            f'<td data-label="Counties">{escape(r["counties"])}</td>'
            + phone_cell(r["phone"])
            + "</tr>"
        )
    return out


def main() -> dict:
    nvlap = parse_nvlap()
    fl_cjc, fl_cons, occ_counts, fl_total = parse_florida()
    ca, ca_updated = parse_california()
    ny = ny_offices()

    dump_json(
        DATA / "nvlap-labs.json",
        {
            "source": {
                "url": NVLAP_SEARCH,
                "program": "Asbestos Fiber Analysis",
                "program_page": NVLAP_PROGRAM,
                "retrieved": RETRIEVED_ISO,
                "notes": "Rows transcribed from the official NVLAP directory search results (POST to directory.results, programId=2). Phone numbers are not on that public results table.",
            },
            "count": len(nvlap),
            "records": nvlap,
        },
    )
    dump_json(
        DATA / "florida-contractors.json",
        {
            "source": {
                "url": FL_CSV_URL,
                "layout": FL_LAYOUT,
                "codes": FL_CODES,
                "retrieved": RETRIEVED_ISO,
                "notes": "Occupation code CJC = Asbestos Contractor per DBPR Understanding DBPR Codes. CSV has no phone field.",
            },
            "count": len(fl_cjc),
            "records": fl_cjc,
        },
    )
    dump_json(
        DATA / "florida-consultants.json",
        {
            "source": {
                "url": FL_CSV_URL,
                "layout": FL_LAYOUT,
                "codes": FL_CODES,
                "retrieved": RETRIEVED_ISO,
                "notes": "Occupation codes AX, AF, DD, EA, IA are asbestos consultant classes per DBPR. CSV has no phone field.",
            },
            "count": len(fl_cons),
            "records": fl_cons,
        },
    )
    dump_json(
        DATA / "california-registrants.json",
        {
            "source": {
                "url": CA_LIST,
                "search_page": CA_SEARCH,
                "document_date": ca_updated,
                "retrieved": RETRIEVED_ISO,
                "notes": "Cal/OSHA Asbestos Registrants' Database full list. Phone transcribed only when present on the official table. A hyphen on the source is stored as unknown.",
            },
            "count": len(ca),
            "records": ca,
        },
    )
    dump_json(
        DATA / "ny-district-offices.json",
        {
            "source": {
                "url": NY_ACB,
                "retrieved": RETRIEVED_ISO,
                "notes": "District offices and the license unit transcribed from the Asbestos Control Bureau page. These are bureau contacts, not contractors. No contractor table was returned by the listing URL cited in DOL publications.",
            },
            "count": len(ny),
            "records": ny,
        },
    )

    us_nvlap = sum(1 for r in nvlap if r["country"] == "US")
    ca_phones = sum(1 for r in ca if r["phone"] != "unknown")

    # Homepage
    page(
        "index.html",
        "Find an NVLAP-accredited asbestos lab | Asbestos Lab Index",
        "Find an NVLAP-accredited lab that can analyze asbestos — then a licensed contractor if the report says to remove it. Analyze first, abate second. No rankings.",
        "index.html",
        f"""    <h1 class="page">Find an NVLAP-accredited lab that can analyze asbestos — then a licensed contractor if the report says to remove it.</h1>
    <p class="lede">Analyze first, abate second. This directory transcribes official laboratory and contractor lists. It does not rank labs, contractors, or products.</p>
    <p class="meta">First version published {RETRIEVED} (US/Pacific).</p>

    <div class="cards two cta-cards">
      <div class="card">
        <h3><a href="nvlap.html">NVLAP labs — {len(nvlap)} laboratories</a></h3>
        <p>NIST National Voluntary Laboratory Accreditation Program, Asbestos Fiber Analysis. Name, NVLAP lab code, city, and state from the official directory search. Phone is unknown; it is not on that results table.</p>
        <a class="btn" href="nvlap.html">Open NVLAP labs</a>
      </div>
      <div class="card">
        <h3><a href="florida.html">Florida — {len(fl_cjc)} contractors, {len(fl_cons)} consultants</a></h3>
        <p>Florida DBPR weekly asbestos extract. Name, city, and license from the CSV. The file has no phone column, so call links are omitted.</p>
        <a class="btn secondary" href="florida.html">Open Florida licenses</a>
      </div>
      <div class="card">
        <h3><a href="california.html">California — {len(ca)} Cal/OSHA registrants</a></h3>
        <p>Asbestos Contractors’ Registration Unit full list, last updated {escape(ca_updated)} on the official page. Name, city, registration number, CSLB number, and phone when the table printed one.</p>
        <a class="btn secondary" href="california.html">Open California registrants</a>
      </div>
    </div>
    <p><a href="states.html">State directory</a> · <a href="new-york.html">New York Asbestos Control Bureau</a> (contractor table not retrieved).</p>

    <div class="flow">
      <article>
        <span class="step">1. Analyze</span>
        <h2>Use an accredited laboratory</h2>
        <p>EPA: you generally cannot tell whether a material contains asbestos by looking at it. A trained professional should take samples; a qualified laboratory analyzes them. Start with <a href="nvlap.html">NVLAP Asbestos Fiber Analysis labs</a>.</p>
      </article>
      <article>
        <span class="step">2. Read the report</span>
        <h2>Leave intact material alone</h2>
        <p>EPA: asbestos-containing materials that are not damaged or disturbed are not likely to pose a health risk. Usually the best thing is to leave material in good condition alone. <a href="when-to-test.html">When to test, with citations</a>.</p>
      </article>
      <article>
        <span class="step">3. Abate only if needed</span>
        <h2>Hire a licensed contractor</h2>
        <p>EPA: removal must be done only by a trained and accredited asbestos professional. Improper removal can increase exposure. Use a state license list — not a ranking.</p>
      </article>
    </div>

    <div class="callout">
      <h2>What this site will not do</h2>
      <p>We do not invent laboratories, contractors, or phone numbers. If a field is not on the official source, it is marked unknown or omitted. We do not rank labs or abatement firms. There are no live Amazon, ELC, or other affiliate links on this version.</p>
    </div>
""",
    )

    # NVLAP
    page(
        "nvlap.html",
        "NVLAP asbestos fiber analysis labs | Asbestos Lab Index",
        f"{len(nvlap)} laboratories from NIST NVLAP Asbestos Fiber Analysis directory search. Name, lab code, city, state. No invented phones.",
        "nvlap.html",
        f"""    <h1 class="page">NVLAP-accredited asbestos fiber analysis laboratories</h1>
    <p class="lede">Transcribed from the National Institute of Standards and Technology National Voluntary Laboratory Accreditation Program (NVLAP) public directory, program <strong>Asbestos Fiber Analysis</strong>.</p>
    <p class="meta">Directory search retrieved {RETRIEVED}. Official search: <a href="{NVLAP_SEARCH}">{NVLAP_SEARCH}</a>. Program page (updated 17 July 2026): <a href="{NVLAP_PROGRAM}">{NVLAP_PROGRAM}</a>.</p>

    <div class="callout compact">
      <h2>How to read this table</h2>
      <p>NVLAP’s Asbestos Fiber Analysis program accredits laboratories to analyze asbestos using polarized light microscopy (PLM) and/or transmission electron microscopy (TEM). AHERA requires NVLAP accreditation for laboratories that analyze asbestos samples taken from public or private elementary or secondary schools. Source: <a href="{NVLAP_PROGRAM}">NIST Asbestos Fiber Analysis LAP</a>.</p>
      <p><strong>Phone is unknown</strong> on every row. The public results table lists lab code, name, city, state, and country only. We did not copy numbers from marketing sites. Confirm current accreditation in the official directory before you ship a sample.</p>
      <p>Country code <strong>CA</strong> on this table is Canada, as returned by NVLAP — not California. California laboratories have State = CA and Country = US.</p>
    </div>

{table(f"{len(nvlap)} laboratories from NVLAP Asbestos Fiber Analysis directory, retrieved {RETRIEVED}", "nvlap", ["Laboratory", "NVLAP code", "City", "State", "Country", "Phone"], nvlap_rows(nvlap))}
    <p>Machine-readable copy: <a href="data/nvlap-labs.json">data/nvlap-labs.json</a>. Every record includes the directory <code>source_url</code>. {us_nvlap} rows are Country = US.</p>
""",
        wide=True,
    )

    occ_note = ", ".join(f"{k} {v} ({occ_counts[k]})" for k, v in sorted(occ_counts.items(), key=lambda kv: -kv[1]))
    page(
        "florida.html",
        "Florida licensed asbestos contractors | Asbestos Lab Index",
        f"Florida DBPR asbestos extract: {len(fl_cjc)} contractors and {len(fl_cons)} consultants. Name, city, license. No phone column on the CSV.",
        "florida.html",
        f"""    <h1 class="page">Florida licensed asbestos contractors and consultants</h1>
    <p class="lede">Transcribed from the Florida Department of Business and Professional Regulation weekly asbestos licensee extract. Analyze with an <a href="nvlap.html">NVLAP lab</a> first. Hire a licensed contractor only if the report and the law say the material should be removed.</p>
    <p class="meta">CSV retrieved {RETRIEVED} from <a href="{FL_CSV_URL}">{FL_CSV_URL}</a>. Column layout: <a href="{FL_LAYOUT}">Asbestos public records</a>. Occupation and status codes: <a href="{FL_CODES}">Understanding DBPR Codes</a>. The extract includes active, inactive, and voluntarily inactive licensees; null-and-void, delinquent, and involuntarily inactive records are omitted by DBPR.</p>

    <div class="callout compact">
      <h2>How to read these tables</h2>
      <p><strong>Phone is unknown</strong> on every row. The official file layout has no phone field, and no phone-like values appear in the CSV. Call links are omitted. Verify a license on <a href="https://www.myfloridalicense.com/">MyFloridaLicense</a> before you hire.</p>
      <p><strong>Asbestos Contractor (CJC)</strong> is the occupation code DBPR lists for contractors. <strong>AX, AF, DD, EA, and IA</strong> are consultant classes. We did not list financial responsible officers, course providers, or training courses as contractors. Those occupation codes are in the extract ({escape(occ_note)}; {fl_total} rows total) and are not tabulated here.</p>
      <p>DBPR Asbestos Licensing Unit (agency, not a contractor): 2601 Blair Stone Road, Tallahassee, FL 32399. Telephone <a href="tel:+18504871395">850.487.1395</a> (from the public-records page).</p>
    </div>

    <h2>Asbestos contractors (CJC)</h2>
{table(f"{len(fl_cjc)} asbestos contractor licenses from lic59asb.csv, retrieved {RETRIEVED}", "fl-cjc", ["Name", "Doing business as", "City", "State", "License", "Occupation", "Status", "Phone"], fl_rows(fl_cjc))}

    <h2>Asbestos consultants</h2>
    <p>These rows are licensed consultants on the same extract. EPA recommends using separate firms for inspection and for removal when you can, so there is no conflict of interest.</p>
{table(f"{len(fl_cons)} asbestos consultant licenses from lic59asb.csv, retrieved {RETRIEVED}", "fl-cons", ["Name", "Doing business as", "City", "State", "License", "Occupation", "Status", "Phone"], fl_rows(fl_cons))}
    <p>Machine-readable copies: <a href="data/florida-contractors.json">data/florida-contractors.json</a> and <a href="data/florida-consultants.json">data/florida-consultants.json</a>. Every record includes <code>source_url</code>.</p>
""",
        wide=True,
    )

    page(
        "california.html",
        "California Cal/OSHA asbestos registrants | Asbestos Lab Index",
        f"{len(ca)} Cal/OSHA asbestos registrants from the official database updated {ca_updated}. Name, city, registration number, CSLB, phone when listed.",
        "california.html",
        f"""    <h1 class="page">California Cal/OSHA asbestos registrants</h1>
    <p class="lede">Transcribed from the Division of Occupational Safety and Health Asbestos Registrants’ Database. These are employers registered to perform asbestos-related work — not NVLAP laboratories. Analyze first with an <a href="nvlap.html">NVLAP lab</a>.</p>
    <p class="meta">Full list retrieved {RETRIEVED} from <a href="{CA_LIST}">{CA_LIST}</a>. The official page stated it was last updated on {escape(ca_updated)}. Search interface: <a href="{CA_SEARCH}">{CA_SEARCH}</a>.</p>

    <div class="callout compact">
      <h2>How to read this table</h2>
      <p>Cal/OSHA: listing a building contractor as a registrant does not assure that the contractor license is current and active. Check CSLB status from the registrant’s detail page on the official site. Some registrants whose registration has just expired may remain on the database and cannot work until renewal is approved.</p>
      <p>Phone numbers are copied only when the official table printed one. One row listed a hyphen; that phone is marked unknown and has no call link. Restrictions that the table left blank are marked unknown.</p>
    </div>

{table(f"{len(ca)} Cal/OSHA asbestos registrants, official list dated {ca_updated}", "ca", ["Employer / DBA", "City", "State", "Reg #", "CSLB #", "Expires", "Phone"], ca_rows(ca))}
    <p>{ca_phones} rows have a phone from the official table. Machine-readable copy: <a href="data/california-registrants.json">data/california-registrants.json</a>.</p>
""",
        wide=True,
    )

    page(
        "new-york.html",
        "New York asbestos control bureau | Asbestos Lab Index",
        "New York DOL Asbestos Control Bureau: official links and district-office contacts transcribed from the bureau page. No contractor table was returned.",
        "new-york.html",
        f"""    <h1 class="page">New York Asbestos Control Bureau</h1>
    <p class="lede">The New York State Department of Labor Asbestos Control Bureau oversees asbestos abatement inspections and enforces Labor Law and Industrial Code Rule 56. We could not fetch a public contractor table from the listing URL DOL still cites.</p>
    <p class="meta">Bureau page retrieved {RETRIEVED}: <a href="{NY_ACB}">{NY_ACB}</a>.</p>

    <div class="callout">
      <h2>No contractor rows on this version</h2>
      <p>The bureau page points readers to an “Asbestos Contractors Listing.” DOL publication P-224 tells readers to use <a href="{NY_OLD_LIST}">{NY_OLD_LIST}</a>. Fetching that URL on {RETRIEVED} returned the generic Division of Safety and Health page, not a contractor table. We did not invent names, licenses, or phones to fill the gap. Use the bureau page and district offices below, and confirm any firm through DOL.</p>
    </div>

    <h2>Laboratories in New York</h2>
    <p>NYS DOH Wadsworth Center Environmental Laboratory Approval Program (ELAP) certifies laboratories for asbestos analysis. The <a href="{NY_DOH_SAMPLE}">Sampling and Testing for Asbestos</a> page (revised October 2023) does not publish a lab table. It says to contact ELAP at <a href="tel:+15184855570">(518) 485-5570</a> or elap@health.state.ny.us. School samples still need an <a href="nvlap.html">NVLAP-accredited</a> laboratory under AHERA.</p>

    <h2>District offices (bureau contacts, not contractors)</h2>
    <p>Transcribed from the Asbestos Control Bureau page. These phones are DOL offices.</p>
{table("New York Asbestos Control Bureau district offices and license unit, from dol.ny.gov/asbestos-control-bureau", "ny", ["Office", "City", "Address", "Counties", "Phone"], ny_rows(ny))}
    <p>Emails published on that page include labor.sm.dosh@labor.ny.gov, labor.sm.AskDOL.asbestos.mold@labor.ny.gov, license&amp;certificate@labor.ny.gov, and asbestoscontrolbureau@labor.ny.gov. Machine-readable copy: <a href="data/ny-district-offices.json">data/ny-district-offices.json</a>.</p>
""",
        wide=True,
    )

    page(
        "when-to-test.html",
        "When to test for asbestos in the home | Asbestos Lab Index",
        "EPA homeowner guidance: test damaged or soon-to-be-disturbed materials through an accredited professional and a qualified lab. Leave intact asbestos alone. Analyze first, abate second.",
        "when-to-test.html",
        f"""    <h1 class="page">When to test for asbestos in the home</h1>
    <p class="lede">This page cites EPA’s current homeowner guidance. It is not a removal how-to and not a product list.</p>
    <p class="meta">Primary source: <a href="{EPA_HOME}">EPA, Protect Your Family from Exposures to Asbestos</a>, last updated 25 June 2026. Retrieved {RETRIEVED}.</p>

    <div class="callout ok">
      <h2>EPA in one line</h2>
      <p>If building materials are not damaged and will not be disturbed, EPA says you do not need to have your home tested. Material in good condition should be left alone. If you are remodeling, or materials are damaged, have a trained and accredited asbestos professional inspect and sample — then a qualified laboratory analyze the samples.</p>
    </div>

    <h2>You usually cannot tell by looking</h2>
    <p>EPA: generally, you cannot tell whether a material contains asbestos simply by looking at it, unless it is labeled. If in doubt, treat the material as if it contains asbestos and leave it alone.</p>
    <p>EPA says you may want a trained and accredited asbestos professional to inspect if you are planning to remodel, or if the home has damaged building materials (for example crumbling drywall or insulation that is falling apart).</p>

    <h2>Who should take the sample</h2>
    <p>EPA: a trained and accredited asbestos professional should take samples for analysis. A professional knows what to look for, and there may be an increased health risk if fibers are released. If done incorrectly, sampling can be more hazardous than leaving the material alone. Taking samples yourself is not recommended.</p>
    <p>Have the samples analyzed by an accredited laboratory. For school samples, federal AHERA rules require a laboratory accredited under NIST NVLAP. Homeowners outside that school rule should still start with the <a href="nvlap.html">NVLAP Asbestos Fiber Analysis directory</a> or their state certification program — not a kit sold with an abatement bid.</p>

    <h2>If asbestos is present</h2>
    <p>EPA: asbestos-containing materials that are not damaged or disturbed are not likely to pose a health risk. Usually the best thing is to leave asbestos-containing material alone if it is in good condition. Fibers may be released when material is disturbed, damaged, removed improperly, repaired, cut, torn, sanded, sawed, drilled, or scraped.</p>
    <p>For slightly damaged material, EPA says sometimes the best approach is to limit access and not touch it. If material is more than slightly damaged, or you will make changes that might disturb it, repair or removal by a trained and accredited asbestos professional is needed.</p>

    <h2>Do’s and don’ts (EPA)</h2>
    <ul>
      <li>Do leave undamaged asbestos-containing materials alone.</li>
      <li>Do keep activities to a minimum in areas with damaged material that may contain asbestos, including limiting children’s access.</li>
      <li>Do have removal and major repair done by people trained and qualified in handling asbestos. EPA highly recommends that sampling and minor repair also be done by a trained and accredited professional.</li>
      <li>Don’t dust, sweep, or vacuum debris that may contain asbestos.</li>
      <li>Don’t saw, sand, scrape, or drill holes in asbestos-containing materials.</li>
      <li>Don’t use abrasive pads or power strippers on flooring that may contain asbestos.</li>
    </ul>

    <h2>Inspectors are not contractors</h2>
    <p>EPA describes two main types of accredited professionals: <strong>inspectors</strong> (inspect, sample, advise, and later check the work) and <strong>contractors</strong> (repair or remove). Avoid a conflict of interest: the professional hired to assess the need for repair or removal should not be connected with the firm that does the removal. Use two different firms when you can. Ask each person for proof of federal or state-approved training.</p>
    <p>Federal law does not require persons who inspect, repair, or remove asbestos in detached single-family homes to be trained and accredited; some states and localities do. EPA still says homeowners should ensure workers are trained and accredited. State agencies have the most up-to-date listings — which is why this site transcribes those lists instead of ranking companies.</p>
    <p>Removal “must be done only by a trained and accredited asbestos professional. Improper removal may actually increase your and your family’s exposure to asbestos fibers.” Source: <a href="{EPA_HOME}">EPA Protect Your Family from Exposures to Asbestos</a> (25 June 2026).</p>
""",
    )

    page(
        "states.html",
        "State asbestos lab and contractor directory | Asbestos Lab Index",
        "NVLAP labs nationwide, Florida DBPR contractors, California Cal/OSHA registrants live. New York bureau contacts; contractor list not retrieved.",
        "states.html",
        f"""    <h1 class="page">State directory</h1>
    <p class="lede">Live pages are built from official lists we could actually fetch. If a state has no transcribed rows, we say so and link the agency.</p>
    <p class="meta">Last updated {RETRIEVED}.</p>

    <ul class="state-list">
      <li><span><a href="nvlap.html"><strong>United States (NVLAP labs)</strong></a> — {len(nvlap)} Asbestos Fiber Analysis laboratories from NIST</span> <span class="badge">Live</span></li>
      <li><span><a href="florida.html"><strong>Florida</strong></a> — {len(fl_cjc)} contractors and {len(fl_cons)} consultants from DBPR’s weekly extract</span> <span class="badge">Live</span></li>
      <li><span><a href="california.html"><strong>California</strong></a> — {len(ca)} Cal/OSHA asbestos registrants (list dated {escape(ca_updated)})</span> <span class="badge">Live</span></li>
      <li><span><a href="new-york.html"><strong>New York</strong></a> — Asbestos Control Bureau contacts; contractor listing URL did not return a table</span> <span class="badge soon">Bureau only</span></li>
      <li><span>Other states</span> <span class="badge soon">Coming soon</span></li>
    </ul>

    <h2>How other states will be added</h2>
    <p>We will not publish a contractor or lab table until we can transcribe a current official list, or honestly say what we could not verify. EPA tells homeowners that state agencies keep the most up-to-date listings of accredited professionals. See <a href="about.html">methodology</a>.</p>
""",
    )

    page(
        "about.html",
        "About Asbestos Lab Index | Stephen Shortell",
        "Asbestos Lab Index lists NVLAP labs and official contractor registers. Compiled by Stephen Shortell. No invented records, no rankings, no live affiliate links.",
        "about.html",
        f"""    <h1 class="page">About Asbestos Lab Index</h1>
    <p class="lede">A directory by Stephen Shortell. We publish NVLAP-accredited asbestos laboratories and official state contractor or registrant lists. We do not invent records.</p>
    <p class="meta">First version published {RETRIEVED} (US/Pacific).</p>

    <h2>What we are</h2>
    <p>Asbestos Lab Index helps a homeowner find a laboratory NIST has accredited for asbestos fiber analysis — then, if a report and the law say material should come out, a contractor who actually appears on a state license or registration list. It is not a government website, not a laboratory, and not an abatement contractor.</p>

    <h2>Methodology</h2>
    <ul>
      <li>Lab and contractor rows are transcribed from official directories, CSVs, or agency HTML tables. Each JSON record carries a <code>source_url</code>.</li>
      <li>If a field is not on the source (especially phone), we write <strong>unknown</strong> and do not add a call link.</li>
      <li>We do not copy business-directory phone numbers or enrich records from Google, Yelp, or company marketing sites.</li>
      <li>We do not publish rankings, “best abatement company” lists, invented statistics, or unsourced prices.</li>
      <li>Guidance pages quote or closely paraphrase EPA and NIST, with page dates.</li>
    </ul>
    <p>How this site is built: <a href="README.md">README.md</a>. What we fetched: <a href="SOURCES.md">SOURCES.md</a>.</p>

    <h2>Commission disclosure</h2>
    <p>This project is intended to become an income site. Later versions may earn a commission if you buy a related service through a labeled link. <strong>This first version has no live Amazon, ELC, or other affiliate links and no paid placements.</strong> Laboratory and contractor listings are not advertisements.</p>

    <h2>Contact</h2>
    <p>Byline: Stephen Shortell / Asbestos Lab Index. This static first version does not yet publish an editorial email on the public pages.</p>
""",
    )

    stats = {
        "nvlap": len(nvlap),
        "nvlap_us": us_nvlap,
        "fl_total_csv": fl_total,
        "fl_contractors": len(fl_cjc),
        "fl_consultants": len(fl_cons),
        "fl_occ": dict(occ_counts),
        "ca": len(ca),
        "ca_phones": ca_phones,
        "ca_updated": ca_updated,
        "ny_offices": len(ny),
    }
    (DATA / "_build_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    main()
