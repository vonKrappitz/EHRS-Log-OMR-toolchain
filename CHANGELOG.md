# Changelog

## v1.1.0 (unreleased, set date at release)

Robustness improvements and a new orientation marker. Backward compatible with v1.0 forms.

### Added
- Asymmetric orientation and identity marker. One small solid mark per form, each in its own slot down the left margin. A single mark breaks the 180-degree symmetry (orientation) and which slot is marked encodes which form it is (identity). The mark carries form TYPE only, identical on every card of a kind, so the doctor card stays unlinkable. Recorded per form as `orientation_pip` and at top level as `orientation_id.slots`. Layout version bumped to `v1.1`.
- Automatic form recognition. The reader no longer needs scans pre-sorted into pilot/doctor/dispatcher folders. Because all three forms share the same four corner fiducials, the homography is computed before the form is known, then the marked slot names the form. `identify_form()` returns the form and orientation by argmax over the two orientations and the slots; `process_images_auto()` routes a flat folder of mixed scans to streams; CLI gains `--auto DIR`.
- `build_homography_oriented()` in the reader. It picks the upright or 180-degree homography by testing which one makes the pip location read dark. Layouts without a pip (v1.0) fall back to upright.

### Changed
- Bubble binarisation now uses a page-global Otsu threshold instead of a fixed 128, so dim or unevenly lit scans read correctly. `find_fiducials()` returns the Otsu threshold, threaded through `read_form()` and `fill_ratio()`.
- `CITATION.cff`. Version 1.1.0. The `doi:` field now holds the concept DOI 10.5281/zenodo.20592466. The v1.0.0 file mislabelled the version DOI 20592467 as the concept DOI. The 1.1.0 version DOI is filled at deposit.
- README. Orientation reframed from a limitation to an auto-detected feature. Citation and badge point to the concept DOI.

### Fixed
- Batch processing no longer aborts on a single unreadable or fiducial-less file. `process_images()` wraps each file in try/except, warns on stderr, and continues.

### Note for users
- The form PDFs changed. They now carry the orientation marker. Reprint forms to use orientation auto-detection. Forms already printed from v1.0 still read, but without 180-degree protection.

### Verification
- `test_omr_roundtrip.py` passes. It covers the normal round-trip, a 180-degree case where an upside-down pilot page reads identically, and an auto-routing case where a flat folder of mixed scans with non-revealing filenames (one of them upside down) is sorted to the correct streams and read correctly. Backward compatibility verified by reading an upright scan with a pip-less v1.0 layout, and by confirming a marker-less scan is skipped in auto mode rather than misclassified. The marks are small enough that `find_fiducials()` still returns exactly four fiducials.
