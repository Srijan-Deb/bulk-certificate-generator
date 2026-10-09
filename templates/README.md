# Certificate Templates & Layout Specifications

This directory contains configuration, architectural specifications, and assets for certificate design templates.

## 1. Engine Architecture
The application uses **ReportLab** for pure vector PDF rendering. Unlike HTML-to-PDF headless browsers (which consume heavy RAM and introduce security vulnerabilities), ReportLab compiles PostScript drawing commands directly into binary PDF streams.

## 2. Default Predefined Template: Executive Classic (A4 Landscape)
The predefined template is implemented in [`app/services/certificate_service.py`](../app/services/certificate_service.py).

### Geometry & Coordinates
- **Page Size**: A4 Landscape (`841.89 pt x 595.27 pt`)
- **Borders**: Double concentric vector borders (Deep Navy 3.5pt outer border, Amber Gold 1.2pt inner border).
- **Corner Accents**: 3.5pt geometric gold stud circles at each margin intersection.
- **Dynamic Recipient Sizing**: Iterative calculation via `canvas.stringWidth()` scaling font size between 30pt and 14pt.
- **Institutional Seal**: Concentric vector circular medallions (`VERIFIED EXCELLENCE`) rendered at `(page_width / 2, 120pt)`.
- **Signatory & Date**: Dual-column layout with horizontal rule underlines at `y = 105pt`.
- **Integrity Banner**: Monospaced audit footer rendering `Certificate ID` and deterministic `Verification Code` (`V-XXXX-XXXX-XXXX`).

## 3. Adding New Templates
To introduce additional layout templates (e.g. Modern Minimalist, Dark Edition):
1. Define layout dimensions and color constants.
2. Implement canvas drawing routines following the `CertificateGenerator` interface.
3. Register the template key in `GenerationJob.template_id`.
