# Migration Guide: v1 to v2

Version 2.0.0 moves the tool’s algorithmic core to perceptually uniform
color science. The command-line surface is unchanged apart from new
flags; the breaking changes are in defaults, field names, and output
schemas. Each change below lists what breaks and how to keep the v1
behavior where one exists.

A `v1_compat` compatibility shim is planned for v2.3.0.

## `ColorInfo.frequency` is now `ColorInfo.weight`

The perceptual extractor reports cluster coverage, not raw pixel counts,
so the field was renamed. Update any code that reads `color.frequency`:

```python
# v1
print(color.frequency)
# v2
print(color.weight)
```

The JSON schema and the text reports follow the rename: the JSON key is
now `weight`, and the text report prints `Weight:` instead of
`Frequency:`. The `sort_by="frequency"` option keeps its name; it sorts
by weight.

## The default palette extractor is now perceptual clustering

`analyze_image()` defaults to deterministic k-means++ clustering in
OKLab with near-duplicate merging at CIEDE2000 2.2. On images with at
most 256 unique visible colors, the palette RGB values and weights match
v1's exact-counting path; harmonies, CMYK, and added metadata still use
v2 defaults. On high-color images the palette is perceptually clustered
to a bounded size instead of median-cut quantized, so RGB values, palette
sizes, and weights differ from v1.

```python
# v2 default
analyzer.analyze_image("photo.jpg")
# v1 behavior
analyzer.analyze_image("photo.jpg", extractor="legacy")
# or on the CLI
color-analysis photo.jpg output/ --extractor legacy
```

Extraction is deterministic: the same image always yields the same
palette. The seed is fixed (`clustering.KMEANS_SEED`).

## Harmonies are computed in OKLCh

`ColorHarmony.find_harmonies()` now rotates hue in OKLCh and maps
results into the sRGB gamut by hue-preserving chroma reduction. Harmony
colors differ from v1 by construction: HSV hue steps are not perceptually
even, OKLCh steps are. The v1 engine remains available:

```python
ColorHarmony.find_harmonies(rgb, engine="hsv_legacy")
analyzer.analyze_image("photo.jpg", harmony_engine="hsv_legacy")
color-analysis photo.jpg output/ --harmony-engine hsv_legacy
```

## CMYK values are ICC-based (FOGRA39)

`ColorConverter.rgb_to_cmyk()` now converts through ICC profiles using
Pillow’s LittleCMS binding, from sRGB to the bundled ISO Coated v2 (ECI)
profile (FOGRA39) with perceptual rendering intent. Values differ from
the v1 formula, which performed no color management. The v1 formula
remains available:

```python
ColorConverter.rgb_to_cmyk(r, g, b, method="device_naive")
```

The v1 formula is also selectable end to end, so reports can carry
v1-style CMYK values:

```python
analyzer.analyze_image("photo.jpg", cmyk_method="device_naive")
color-analysis photo.jpg output/ --cmyk-method device_naive
```

A different press condition can be supplied with `--cmyk-profile PATH`
or the `profile` argument. The profile behind the values is recorded in
JSON output (`cmyk_profile`) and in the CMYK label of text reports.

## The Tailwind artifact is now Tailwind v4 CSS

`--format css` emits `{name}_tailwind.css`, an `@theme` block with OKLCH
values for Tailwind CSS v4, instead of the v1 `{name}_tailwind.js`
config snippet. Import it after your `tailwindcss` import:

```css
@import "tailwindcss";
@import "./example.png_tailwind.css";
```

## JSON schema changes

Per color entry: `frequency` removed; `weight`, `oklch`, `wcag`, and
`apca` added. `wcag` holds contrast ratios against white, black, and the
dominant color with AA/AAA booleans; `apca` holds APCA Lc values marked
`"status": "experimental"`. Top level: `cmyk_profile` added. The W3C
Design Token file keeps HEX `$value`s and carries OKLCH, WCAG, and APCA
data under `$extensions["com.color-analysis-tool"]`.

APCA values are experimental and are not a WCAG conformance criterion;
do not cite them as conformance results.
