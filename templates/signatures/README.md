# Authorized Signatures Dropzone

Place your signature images in this directory.

### Supported Formats
- `.png`
- `.jpg` / `.jpeg`
- `.webp`

### How Pillow Live Fetching Works
1. You can drop a raw photograph taken on a smartphone (e.g. black or blue pen on white paper).
2. The Pillow image processing engine will automatically:
   - Correct camera EXIF rotation.
   - Detect and remove paper background shadows, making it 100% transparent.
   - Clean and recolor ink strokes to dark navy (`#14213D`) matching your certificate palette.
   - Auto-crop margins and save the optimized vector graphic as `processed_signature.png`.
3. Any newly added image here is live-fetched and used on all newly rendered certificates.
