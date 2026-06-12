# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Maciej Kasperek
"""
Generate the three OMR-optimised EHRS Log data-capture forms
(pilot / doctor / dispatcher) as print-ready A4 PDFs, plus a layout
JSON that records every bubble centre so the OMR reader app can sample
fills after fiducial-based alignment.

Design:
  - AUTO fields (from flight log / dispatch system) are printed as
    pre-filled lines, NOT bubbled.
  - MANUAL categorical fields are single-choice bubble rows.
  - Dispatcher counts are OMR digit grids (rows of 0-9 bubbles).
  - Doctor card carries a QR/serial box assigned at scan (after shuffle),
    no date, no flight link.
  - Four solid corner fiducials define the registration frame.
Lean 25-field set: pilot 11 (P01-P11), doctor 8 (D01-D08), dispatcher 6 (X01-X06).
"""
import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

OUTDIR = os.environ.get("EHRS_OUTDIR", ".")  # relative by default; no absolute paths

W, H = A4  # 595.27 x 841.89 pt
MARGIN = 50.0
CONTENT_L = MARGIN
CONTENT_R = W - MARGIN

# fiducials: solid squares, centres 30 pt from each edge
FID = 30.0
FID_SIDE = 16.0
FID_CENTRES = [(FID, FID), (W - FID, FID), (FID, H - FID), (W - FID, H - FID)]

# orientation pip: a small SOLID square placed asymmetrically near the top-left
# fiducial. It breaks the 180-degree symmetry of the four corner fiducials so the
# reader can tell an upright scan from an upside-down one. Kept small enough
# (area well below the fiducial lower bound) that the reader never mistakes it
# for a fifth fiducial.
ORIENT_PIP_SIDE = 8.0
# One solid mark per form, each in its own slot down the left margin. A single
# mark still breaks the 180-degree symmetry (orientation), and WHICH slot is
# marked encodes WHICH form it is (identity). All three forms share the same
# four corner fiducials, so the reader can align a page before it knows the
# form, then read the slot to identify it. The mark carries form TYPE only,
# identical on every card of a kind, so the doctor card stays unlinkable.
MARK_SLOTS = {
    "pilot":      (FID, H - 92.0),
    "doctor":     (FID, H - 112.0),
    "dispatcher": (FID, H - 132.0),
}

BUBBLE_R = 6.0          # categorical bubble radius (~4.2 mm dia)
DIGIT_R = 5.0           # digit-grid bubble radius
LINE = 14.0             # base line height

INK = (0.10, 0.10, 0.12)
GREY = (0.45, 0.45, 0.48)
ACCENT = (0.16, 0.22, 0.45)


def tl(y):
    """reportlab bottom-left y -> top-left y for the layout map."""
    return round(H - y, 2)


class Form:
    def __init__(self, key, c, full=False):
        self.key = key
        self.c = c
        self.full = full
        self.layout = {"fiducials": [], "fields": {}}

    def fiducials(self):
        c = self.c
        c.setFillColorRGB(0, 0, 0)
        for (cx, cy) in FID_CENTRES:
            c.rect(cx - FID_SIDE / 2, cy - FID_SIDE / 2, FID_SIDE, FID_SIDE, stroke=0, fill=1)
            self.layout["fiducials"].append([round(cx, 2), tl(cy)])

    def orientation_pip(self):
        """Draw this form's orientation/identity mark in its own slot."""
        c = self.c
        cx, cy = MARK_SLOTS[self.key]
        s = ORIENT_PIP_SIDE
        c.setFillColorRGB(0, 0, 0)
        c.rect(cx - s / 2, cy - s / 2, s, s, stroke=0, fill=1)
        self.layout["orientation_pip"] = {"cx": round(cx, 2), "cy": tl(cy),
                                          "r": round(s / 2.0, 2)}

    def header(self, title, window):
        c = self.c
        y = H - 52
        c.setFillColorRGB(*ACCENT)
        c.setFont("Helvetica-Bold", 8.5)
        variant = "full 29-field set" if self.full else "core 25-field set"
        c.drawString(CONTENT_L, y + 12, "EHRS LOG  -  European HEMS Operational Reporting Standard  -  v1.0  -  %s" % variant)
        c.setFillColorRGB(*INK)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(CONTENT_L, y - 6, title)
        c.setFillColorRGB(*GREY)
        c.setFont("Helvetica", 8.5)
        c.drawString(CONTENT_L, y - 20, window)
        c.setStrokeColorRGB(*ACCENT)
        c.setLineWidth(1.2)
        c.line(CONTENT_L, y - 27, CONTENT_R, y - 27)
        return y - 44

    def fill_instruction(self, y):
        c = self.c
        c.setFillColorRGB(*GREY)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(CONTENT_L, y, "Fill the bubble completely with blue or black pen. One mark per row unless stated. Do not tick or cross.")
        return y - 14

    def note(self, y, lines, bold_first=False):
        c = self.c
        for i, ln in enumerate(lines):
            c.setFont("Helvetica-Bold" if (bold_first and i == 0) else "Helvetica", 8)
            c.setFillColorRGB(*(ACCENT if (bold_first and i == 0) else GREY))
            c.drawString(CONTENT_L, y, ln)
            y -= 11
        return y - 4

    def auto_field(self, y, fid, label):
        c = self.c
        c.setFillColorRGB(*INK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(CONTENT_L, y, "%s  %s" % (fid, label))
        # box for the imported value
        bx = 300
        c.setStrokeColorRGB(0.7, 0.7, 0.72)
        c.setLineWidth(0.6)
        c.rect(bx, y - 3, CONTENT_R - bx, 12, stroke=1, fill=0)
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColorRGB(*GREY)
        c.drawString(bx + 4, y, "auto-imported")
        self.layout["fields"][fid] = {"type": "auto", "label": label}
        return y - 17

    def bubble_row(self, y, fid, label, options, tier=""):
        c = self.c
        c.setFillColorRGB(*INK)
        c.setFont("Helvetica-Bold", 8.5)
        head = "%s  %s" % (fid, label)
        if tier:
            head += "   [Tier %s]" % tier
        c.drawString(CONTENT_L, y, head)
        yb = y - 15
        x = CONTENT_L + 4
        opts_rec = []
        c.setFont("Helvetica", 8.5)
        for opt in options:
            c.setStrokeColorRGB(*INK)
            c.setLineWidth(0.9)
            c.setFillColorRGB(1, 1, 1)
            c.circle(x + BUBBLE_R, yb, BUBBLE_R, stroke=1, fill=0)
            opts_rec.append({"value": opt, "cx": round(x + BUBBLE_R, 2), "cy": tl(yb), "r": BUBBLE_R})
            c.setFillColorRGB(*INK)
            lx = x + 2 * BUBBLE_R + 4
            c.drawString(lx, yb - 3, opt)
            x = lx + c.stringWidth(opt, "Helvetica", 8.5) + 18
        self.layout["fields"][fid] = {"type": "bubble_single", "label": label, "options": opts_rec}
        return yb - 16

    def qr_box(self, y, fid, label):
        c = self.c
        c.setFillColorRGB(*INK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(CONTENT_L, y, "%s  %s" % (fid, label))
        bw, bh = 74, 74
        bx, by = CONTENT_L + 4, y - 12 - bh
        c.setStrokeColorRGB(*INK)
        c.setLineWidth(1.0)
        c.rect(bx, by, bw, bh, stroke=1, fill=0)
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColorRGB(*GREY)
        c.drawString(bx, by - 11, "QR / serial applied at scan")
        # explanatory text to the right
        tx = bx + bw + 16
        for i, ln in enumerate(["Assigned at scan, after the card pool is",
                                 "shuffled across bases. Carries no date,",
                                 "no order, no link to flight or person.",
                                 "Do not write in this box."]):
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(*GREY)
            c.drawString(tx, by + bh - 12 - i * 11, ln)
        self.layout["fields"][fid] = {"type": "qr_serial", "label": label,
                                       "box": [round(bx, 2), tl(by + bh), round(bw, 2), round(bh, 2)]}
        return by - 28

    def digit_count(self, y, fid, label, sub_id, ndigits, indent=0, sublabel=None, show_header=True):
        """One count as ndigits rows of 0-9 bubbles. The 0-9 guide is printed once,
        above the top row, so digits never clash with bubbles. Records under fid/subcounts/sub_id."""
        c = self.c
        x0 = CONTENT_L + 4 + indent
        step = 20.0
        row_gap = 18.0
        if sublabel is not None:
            x0b = x0 + 100
        else:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColorRGB(*INK)
            c.drawString(x0, y, label)
            x0b = x0
            y -= 20
        # 0-9 guide once, above the top row
        if show_header:
            c.setFont("Helvetica", 6)
            c.setFillColorRGB(*GREY)
            for d in range(10):
                cx = x0b + d * step + DIGIT_R
                c.drawCentredString(cx, y + DIGIT_R + 4, str(d))
        places = ["tens", "units"] if ndigits == 2 else ["units"]
        rec_places = []
        for pi, place in enumerate(places):
            yb = y - pi * row_gap
            if sublabel is not None:
                c.setFont("Helvetica", 8)
                c.setFillColorRGB(*INK)
                c.drawString(x0, yb - 2.5, sublabel)
            else:
                c.setFont("Helvetica", 6.5)
                c.setFillColorRGB(*GREY)
                c.drawString(x0b - 26, yb - 2, place)
            digits = []
            for d in range(10):
                cx = x0b + d * step + DIGIT_R
                c.setStrokeColorRGB(*INK)
                c.setLineWidth(0.8)
                c.setFillColorRGB(1, 1, 1)
                c.circle(cx, yb, DIGIT_R, stroke=1, fill=0)
                digits.append({"digit": d, "cx": round(cx, 2), "cy": tl(yb), "r": DIGIT_R})
            rec_places.append({"place": place, "bubbles": digits})
        node = self.layout["fields"].setdefault(fid, {"type": "digit_count", "label": label, "subcounts": {}})
        node["subcounts"][sub_id] = {"label": (sublabel or "total"), "places": rec_places}
        return y - row_gap * (len(places) - 1) - 16

    def digit_key(self, y, fid, label, ndigits=6):
        """Join key as ndigits rows of 0-9 bubbles (one bubble per row).
        Recorded as type digit_key; the reader returns the digit string."""
        c = self.c
        x0 = CONTENT_L + 4
        step = 20.0
        row_gap = 18.0
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColorRGB(*INK)
        c.drawString(x0, y, "%s  %s" % (fid, label))
        y -= 12
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColorRGB(*GREY)
        c.drawString(x0, y, "Mark one bubble per row. Top row = first digit. Leave leading rows blank for shorter numbers; mark every internal zero.")
        y -= 15
        x0b = x0 + 34
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(*GREY)
        for d in range(10):
            cx = x0b + d * step + DIGIT_R
            c.drawCentredString(cx, y + DIGIT_R + 4, str(d))
        places = []
        for i in range(ndigits):
            yb = y - i * row_gap
            c.setFont("Helvetica", 6.5)
            c.setFillColorRGB(*GREY)
            c.drawString(x0b - 26, yb - 2, "d%d" % (i + 1))
            bubs = []
            for d in range(10):
                cx = x0b + d * step + DIGIT_R
                c.setStrokeColorRGB(*INK)
                c.setLineWidth(0.8)
                c.setFillColorRGB(1, 1, 1)
                c.circle(cx, yb, DIGIT_R, stroke=1, fill=0)
                bubs.append({"digit": d, "cx": round(cx, 2), "cy": tl(yb), "r": DIGIT_R})
            places.append({"place": "d%d" % (i + 1), "bubbles": bubs})
        self.layout["fields"][fid] = {"type": "digit_key", "label": label, "places": places}
        return y - row_gap * (ndigits - 1) - 16

    def footer(self):
        c = self.c
        c.setFillColorRGB(*GREY)
        c.setFont("Helvetica", 6.5)
        c.drawString(CONTENT_L, FID + 18, "EHRS Log %s form  -  OMR sheet  -  align corner marks when scanning  -  data minimisation per GDPR art. 5(1)(c)" % self.key)
        c.drawRightString(CONTENT_R, FID + 18, "Supplementary annex")


def build(full=False, suffix=""):
    forms_layout = {}
    paths = {}

    # ---------------- PILOT ----------------
    p = os.path.join(OUTDIR, "EHRS_form_pilot%s.pdf" % suffix)
    c = canvas.Canvas(p, pagesize=A4)
    f = Form("pilot", c, full)
    f.fiducials()
    f.orientation_pip()
    y = f.header("Pilot operational record", "Completed by the pilot at shutdown (about 2 minutes). Linked to the mission record via Mission ID.")
    y = f.fill_instruction(y)
    if full:
        y = f.note(y, ["The pilot marks the mission number (join key), mission category, flight conditions and crew configuration.",
                       "Everything else is joined from the flight log by the mission number."])
    else:
        y = f.note(y, ["The pilot marks the mission number (join key), mission category and flight conditions.",
                       "Everything else is joined from the flight log by the mission number."])
    y = f.digit_key(y, "P01", "Mission number (join key)  -  fill after flight", 6)
    y -= 4
    y = f.auto_field(y, "P02", "Date and shift")
    y = f.auto_field(y, "P03", "Base of departure")
    y = f.auto_field(y, "P05", "Day / night operation")
    y = f.auto_field(y, "P07", "Activation (alert) time")
    y = f.auto_field(y, "P08", "Airborne time")
    y = f.auto_field(y, "P09", "On-scene time")
    y = f.auto_field(y, "P10", "Scene-departure time")
    y = f.auto_field(y, "P11", "Arrival at destination hospital")
    if full:
        y = f.auto_field(y, "P13", "Aircraft type / category")
    y -= 4
    y = f.bubble_row(y, "P04", "Mission category", ["Primary", "Secondary", "Interfacility", "SAR"], tier="A")
    y = f.bubble_row(y, "P06", "Flight conditions", ["VMC", "IMC"], tier="B")
    if full:
        y = f.bubble_row(y, "P12", "Crew configuration", ["Physician + HCM", "Physician + paramedic", "Paramedic + HCM", "Other"], tier="B")
    f.footer()
    c.save()
    forms_layout["pilot"] = f.layout
    paths["pilot"] = p

    # ---------------- DOCTOR ----------------
    p = os.path.join(OUTDIR, "EHRS_form_doctor%s.pdf" % suffix)
    c = canvas.Canvas(p, pagesize=A4)
    f = Form("doctor", c, full)
    f.fiducials()
    f.orientation_pip()
    y = f.header("Clinical card", "Completed by the physician after handover (about 3 minutes).")
    y = f.fill_instruction(y)
    y = f.note(y, ["Standalone anonymous card. No date. Not linked to flight, crew, or patient identity.",
                   "Categorical only, no free text. Irreversibly anonymous by design."], bold_first=True)
    y = f.qr_box(y, "D01", "Card serial")
    y = f.bubble_row(y, "D02", "Age category", ["Child (<18)", "Adult (18-65)", "Senior (65+)"], tier="A")
    y = f.bubble_row(y, "D03", "Leading problem", ["Trauma", "Cardiac", "OHCA", "Neurological", "Other"], tier="A")
    y = f.bubble_row(y, "D04", "NACA score", [str(n) for n in range(8)], tier="A")
    y = f.bubble_row(y, "D05", "Cardiac arrest (OHCA)", ["Yes", "No"], tier="A")
    y = f.bubble_row(y, "D06", "ROSC achieved", ["Yes", "No", "N/A"], tier="A")
    y = f.bubble_row(y, "D07", "Advanced airway / intubation", ["Yes", "No"], tier="B")
    y = f.bubble_row(y, "D08", "Destination hospital level", ["Tertiary", "PCI centre", "Trauma centre"], tier="B")
    if full:
        y = f.bubble_row(y, "D09", "Condition at handover", ["Stable / improved", "Unchanged", "Deteriorated", "Deceased"], tier="B")
    f.footer()
    c.save()
    forms_layout["doctor"] = f.layout
    paths["doctor"] = p

    # ---------------- DISPATCHER ----------------
    p = os.path.join(OUTDIR, "EHRS_form_dispatcher%s.pdf" % suffix)
    c = canvas.Canvas(p, pagesize=A4)
    f = Form("dispatcher", c, full)
    f.fiducials()
    f.orientation_pip()
    y = f.header("Dispatch shift wrap-up", "Completed by the dispatcher at end of shift (about 3 minutes). Shift-level aggregates, no patient records.")
    y = f.fill_instruction(y)
    y = f.note(y, ["Captures the missed-case denominator. Calls received and missions launched are imported;",
                   "aborted, declined and rejected counts are entered as digit grids (mark one bubble per digit place)."])
    y = f.auto_field(y, "X01", "Shift / base")
    y = f.auto_field(y, "X02", "Calls received in shift")
    y = f.auto_field(y, "X03", "Missions launched")
    if full:
        y = f.auto_field(y, "X07", "Aircraft serviceability hours")
    y -= 2
    y = f.digit_count(y, "X04", "Missions aborted (total)", "total", 2)
    c.setFont("Helvetica-Oblique", 7.5); c.setFillColorRGB(*GREY)
    c.drawString(CONTENT_L + 4, y, "by stage:"); y -= 20
    y = f.digit_count(y, "X04", "Missions aborted", "pre_launch", 1, indent=10, sublabel="Pre-launch", show_header=True)
    y = f.digit_count(y, "X04", "Missions aborted", "en_route", 1, indent=10, sublabel="En-route", show_header=False)
    y = f.digit_count(y, "X04", "Missions aborted", "on_scene", 1, indent=10, sublabel="On-scene", show_header=False)
    y -= 4
    y = f.digit_count(y, "X05", "Missions declined (total)", "total", 2)
    c.setFont("Helvetica-Oblique", 7.5); c.setFillColorRGB(*GREY)
    c.drawString(CONTENT_L + 4, y, "by reason:"); y -= 20
    y = f.digit_count(y, "X05", "Missions declined", "weather", 1, indent=10, sublabel="Weather", show_header=True)
    y = f.digit_count(y, "X05", "Missions declined", "crew_duty", 1, indent=10, sublabel="Crew duty time", show_header=False)
    y = f.digit_count(y, "X05", "Missions declined", "technical", 1, indent=10, sublabel="Technical", show_header=False)
    y = f.digit_count(y, "X05", "Missions declined", "parallel", 1, indent=10, sublabel="Parallel mission", show_header=False)
    y -= 4
    y = f.digit_count(y, "X06", "Missions rejected / stood down by dispatcher", "total", 2)
    f.footer()
    c.save()
    forms_layout["dispatcher"] = f.layout
    paths["dispatcher"] = p

    layout = {
        "ehrs_forms_version": "v1.1",
        "page_size_pt": [round(W, 2), round(H, 2)],
        "coordinate_origin": "top-left",
        "units": "pt",
        "fiducial_side_pt": FID_SIDE,
        "orientation_pip_side_pt": ORIENT_PIP_SIDE,
        "orientation_id": {
            "slots": [
                {"form": k, "cx": round(x, 2), "cy": tl(y),
                 "r": round(ORIENT_PIP_SIDE / 2.0, 2)}
                for k, (x, y) in MARK_SLOTS.items()
            ]
        },
        "forms": forms_layout,
    }
    with open(os.path.join(OUTDIR, "EHRS_forms_layout%s.json" % suffix), "w") as fh:
        json.dump(layout, fh, indent=2)

    return paths


if __name__ == "__main__":
    for full, suffix in [(False, ""), (True, "_full")]:
        paths = build(full=full, suffix=suffix)
        for k, v in paths.items():
            print("wrote", v)
        print("wrote", os.path.join(OUTDIR, "EHRS_forms_layout%s.json" % suffix))
