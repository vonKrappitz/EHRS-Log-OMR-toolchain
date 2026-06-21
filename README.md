# EHRS Log OMR toolchain

Capture tooling for the **EHRS Log**, the data-capture instrument of the European
HEMS Operational Reporting Standard (EHRS). It contains three OMR-optimised A4
forms (pilot / doctor / dispatcher) and a reader that turns scanned paper sheets
into a structured Excel workbook. Proof of concept accompanying the EHRS
manuscript.

The reader finds the four printed corner marks on a scan, corrects rotation and
scale, samples each bubble, assembles digit grids into numbers, pools and
shuffles the doctor cards before assigning anonymous serial numbers, and writes
one Excel sheet per stream.

---

## Quick start (about 3 minutes)

Works on **Windows, macOS and Linux**. Two ready-made sample scans paths are
included, so you can see the whole thing work **without installing anything
system-level**.

### 1. Get the code and a clean environment

```bash
# 1) download or clone this repository, then open a terminal in its folder
# 2) create and activate a clean virtual environment:

# macOS / Linux
python3 -m venv venv && source venv/bin/activate

# Windows (Command Prompt / PowerShell)
python -m venv venv
venv\Scripts\activate
```

### 2. Install the libraries (one command)

```bash
pip install -r requirements.txt
```

### 3. Run the reader on the included sample scans

The repository ships with filled, slightly rotated sample scans under `scans/`,
so you can run the reader **immediately, with no extra tools**:

```bash
python omr_reader.py --layout EHRS_forms_layout_full.json --root scans --out EHRS_capture.xlsx
```

Open the generated `EHRS_capture.xlsx`. You will see three sheets (pilot, doctor,
dispatcher) populated with the recovered data, including the pilot mission-number
key, the categorical clinical fields and the dispatcher missed-case counts. A
reference copy of the expected result is committed as `EHRS_capture_SAMPLE.xlsx`.

That is the whole proof of concept: paper sheet in, structured database out.

---

## Optional: the full round-trip self-test

This regenerates mock scans from the blank PDFs, applies random rotation and
scale to imitate real scanning, reads them back and verifies recovery:

```bash
python test_omr_roundtrip.py
```

It prints a field-by-field check ending in `ROUND-TRIP: ALL OK` and writes
`EHRS_capture_SAMPLE.xlsx`.

> **Note.** This test rasterises the blank PDFs to images and therefore needs the
> system tool **`pdftoppm`** (from Poppler). Installing Poppler on Windows can be
> fiddly, so it is **not required** for the Quick Start above. The Quick Start
> runs entirely on the bundled sample PNGs and needs only the pip packages.

---

## Process your own scans

Scan the filled paper sheets to PNG or JPG, drop them into the matching
subfolder, and run the reader:

```text
scans/pilot/*.png
scans/doctor/*.png
scans/dispatcher/*.png
```

```bash
python omr_reader.py --layout EHRS_forms_layout_full.json --root scans --out EHRS_capture.xlsx
```

Single stream only:

```bash
python omr_reader.py --layout EHRS_forms_layout_full.json --form dispatcher --images "scans/dispatcher/*.png" --out out.xlsx
```

Use `EHRS_forms_layout.json` instead if you printed the core 25-field forms.

---

## Optional: regenerate the blank forms

The blank A4 forms are committed under `forms/`. To rebuild them and the
coordinate maps (needs `reportlab`, already in `requirements.txt`):

```bash
python generate_ehrs_forms.py
```

This writes both variants (core 25-field and full 29-field) plus the matching
`EHRS_forms_layout*.json` to the current directory. Output location can be
overridden with the `EHRS_OUTDIR` environment variable. No absolute paths are
used anywhere in the code.

---

## Repository contents

```text
omr_reader.py               the reader (scan -> Excel)
test_omr_roundtrip.py       round-trip self-test (needs pdftoppm)
generate_ehrs_forms.py      builds the blank forms and coordinate maps
EHRS_forms_layout.json      bubble coordinates, core 25-field forms
EHRS_forms_layout_full.json bubble coordinates, full 29-field forms
forms/                      blank A4 forms, both variants (PDF)
scans/                      filled sample scans (pilot, doctor, dispatcher)
EHRS_capture_SAMPLE.xlsx    reference reader output
requirements.txt            Python dependencies
CITATION.cff                citation metadata (GitHub "Cite this repository")
LICENSE / NOTICE            Apache-2.0
```

## How it works

1. Detect the four solid corner fiducials on the scan.
2. Build a homography from the layout frame onto the scan, correcting rotation,
   scale, translation and mild perspective.
3. Sample each bubble interior and measure the dark fraction. Categorical fields
   take the single marked option; digit grids read one bubble per place and
   assemble the number.
4. The pilot enters the join key (`P01`, mission number) as an OMR digit grid,
   filled after the flight; the remaining pilot fields are joined to the flight
   log by that number. Sheets are interchangeable blanks, so the pilot never has
   to pick a specific one.
5. Doctor cards are pooled and **shuffled before** sequential serials (`D01`) are
   assigned, so the serial carries no order, date or link, and the doctor sheet
   omits the scan-file column. The card is anonymous by design: broad age bands,
   no sex, no date, no flight link, categorical only.

This is the data-minimisation posture the standard relies on (GDPR art. 5(1)(c)):
the instrument measures the system, not the patient.

## Limitations (proof of concept)

- Single-mark assumption per categorical row and per digit place; double marks
  are flagged, not resolved.
- Dispatcher sub-counts are single-digit per shift category; totals are two-digit.
- Fill threshold and fiducial filters are tuned for clean 150-300 dpi scans; a
  field deployment should calibrate them against real scanner output and add a
  reject-and-recapture workflow. Real-world fill quality under operational stress
  has not yet been measured and needs a prospective pilot.

## License and citation

Apache-2.0. Copyright 2026 Maciej M. Kasperek (vonKrappitz). See `LICENSE` and `NOTICE`.

If you use this toolchain, please cite the accompanying article and this
repository. Citation metadata is provided in `CITATION.cff`, which GitHub renders
as a "Cite this repository" button. A permanent archived version with a DOI is
available on Zenodo: `10.5281/zenodo.20592467`.
