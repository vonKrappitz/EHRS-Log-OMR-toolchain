# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Maciej Kasperek
"""
Round-trip self-test for the EHRS Log OMR reader.

Renders the blank full-variant forms, plants known answers by drawing filled
bubbles at the layout coordinates, perturbs each page with a mild rotation and
scale to imitate a scan, runs the reader, and checks the recovered values match
the planted ones. Also emits a sample Excel capture.
"""
import os
import subprocess
import random

import cv2
import numpy as np

import omr_reader as omr

DPI = 150
SCALE = DPI / 72.0
LAYOUT_PATH = "EHRS_forms_layout_full.json"
SCANS = "scans"


def render_blank(form_key):
    pdf = "EHRS_form_%s_full.pdf" % form_key
    out = "blank_%s" % form_key
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), pdf, out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out + "-1.png"


def px(cx, cy):
    return int(round(cx * SCALE)), int(round(cy * SCALE))


def fill_bubble(img, cx, cy, r):
    p = px(cx, cy)
    cv2.circle(img, p, max(3, int(round(r * SCALE * 0.72))), 0, -1)


def fill_single(img, spec, value):
    for o in spec["options"]:
        if str(o["value"]) == str(value):
            fill_bubble(img, o["cx"], o["cy"], o["r"])
            return
    raise KeyError("option %r not in %s" % (value, [o["value"] for o in spec["options"]]))


def fill_count(img, spec, sub, number):
    sd = spec["subcounts"][sub]
    places = sd["places"]
    if len(places) == 2:
        digit_for = {"tens": number // 10, "units": number % 10}
    else:
        digit_for = {"units": number}
    for place in places:
        d = digit_for[place["place"]]
        for b in place["bubbles"]:
            if b["digit"] == d:
                fill_bubble(img, b["cx"], b["cy"], b["r"])
                break


def perturb(img, angle, scale):
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, scale)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR,
                          borderValue=255)


def fill_key(img, spec, number_str):
    places = spec["places"]
    s = str(number_str).zfill(len(places))
    for i, place in enumerate(places):
        d = int(s[i])
        for b in place["bubbles"]:
            if b["digit"] == d:
                fill_bubble(img, b["cx"], b["cy"], b["r"])
                break


# ----------------------- planted answers -----------------------
PILOT = {"P01": "004821", "P04": "Secondary", "P06": "IMC", "P12": "Physician + paramedic"}

DOCTORS = [
    {"D02": "Adult (18-65)", "D03": "Cardiac", "D04": "3", "D05": "No",
     "D06": "N/A", "D07": "No", "D08": "PCI centre", "D09": "Stable / improved"},
    {"D02": "Senior (65+)", "D03": "OHCA", "D04": "6", "D05": "Yes",
     "D06": "Yes", "D07": "Yes", "D08": "Tertiary", "D09": "Deteriorated"},
    {"D02": "Child (<18)", "D03": "Trauma", "D04": "5", "D05": "No",
     "D06": "N/A", "D07": "Yes", "D08": "Trauma centre", "D09": "Unchanged"},
]

DISPATCH = {
    "X04": {"total": 12, "pre_launch": 3, "en_route": 5, "on_scene": 4},
    "X05": {"total": 7, "weather": 4, "crew_duty": 1, "technical": 1, "parallel": 1},
    "X06": {"total": 2},
}


def synth_pilot(layout):
    fl = layout["forms"]["pilot"]
    img = cv2.imread(render_blank("pilot"), cv2.IMREAD_GRAYSCALE)
    for fid, val in PILOT.items():
        if fid == "P01":
            fill_key(img, fl["fields"][fid], val)
        else:
            fill_single(img, fl["fields"][fid], val)
    img = perturb(img, angle=1.3, scale=0.985)
    os.makedirs(os.path.join(SCANS, "pilot"), exist_ok=True)
    cv2.imwrite(os.path.join(SCANS, "pilot", "pilot_001.png"), img)


def synth_doctor(layout):
    fl = layout["forms"]["doctor"]
    base = render_blank("doctor")
    os.makedirs(os.path.join(SCANS, "doctor"), exist_ok=True)
    for i, ans in enumerate(DOCTORS, 1):
        img = cv2.imread(base, cv2.IMREAD_GRAYSCALE)
        for fid, val in ans.items():
            fill_single(img, fl["fields"][fid], val)
        img = perturb(img, angle=-0.9 + 0.6 * i, scale=0.99)
        cv2.imwrite(os.path.join(SCANS, "doctor", "card_%03d.png" % i), img)


def synth_dispatcher(layout):
    fl = layout["forms"]["dispatcher"]
    img = cv2.imread(render_blank("dispatcher"), cv2.IMREAD_GRAYSCALE)
    for fid, subs in DISPATCH.items():
        for sub, n in subs.items():
            fill_count(img, fl["fields"][fid], sub, n)
    img = perturb(img, angle=-1.1, scale=0.99)
    os.makedirs(os.path.join(SCANS, "dispatcher"), exist_ok=True)
    cv2.imwrite(os.path.join(SCANS, "dispatcher", "dispatch_001.png"), img)


def main():
    random.seed(7)
    layout = omr.load_layout(LAYOUT_PATH)
    synth_pilot(layout)
    synth_doctor(layout)
    synth_dispatcher(layout)

    all_records = {}
    for fk in ("pilot", "doctor", "dispatcher"):
        import glob
        imgs = glob.glob(os.path.join(SCANS, fk, "*.png"))
        all_records[fk] = omr.process_images(layout, fk, imgs)

    ok = True

    # pilot
    rp = all_records["pilot"][0]
    for fid, val in PILOT.items():
        got = rp.get(fid)
        good = (got == val)
        ok &= good
        print("PILOT  %s: planted=%-22s got=%-22s %s" % (fid, val, got, "OK" if good else "FAIL"))

    # doctor (shuffled -> compare as multiset of clinical tuples)
    keys = ["D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09"]
    planted = sorted(tuple(d[k] for k in keys) for d in DOCTORS)
    gotset = sorted(tuple(r.get(k) for k in keys) for r in all_records["doctor"])
    dgood = (planted == gotset)
    ok &= dgood
    print("DOCTOR multiset of %d cards: %s" % (len(DOCTORS), "OK" if dgood else "FAIL"))
    serials = sorted(r.get("D01") for r in all_records["doctor"])
    print("DOCTOR serials assigned post-shuffle: %s" % serials)

    # dispatcher
    rd = all_records["dispatcher"][0]
    for fid, subs in DISPATCH.items():
        for sub, n in subs.items():
            got = rd.get(fid, {}).get(sub)
            good = (got == n)
            ok &= good
            print("DISP   %s.%-10s planted=%-3s got=%-3s %s" % (fid, sub, n, got, "OK" if good else "FAIL"))

    omr.write_excel(all_records, layout, "EHRS_capture_SAMPLE.xlsx")
    print("\nwrote EHRS_capture_SAMPLE.xlsx")
    print("\nROUND-TRIP:", "ALL OK" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
