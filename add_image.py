#!/usr/bin/env python3
"""
Usage: python3 add_image.py <image_file> <js_key> "<Label>" <slot> <era>

Slots: top | bottom | full | shoes | acc
Era examples: "1980s"  "1970s"  "1900s–40s"

Example:
  python3 add_image.py my_jacket.png m90_jacket "Leather Blazer" top "1990s"

What it does:
  1. Removes the background (AI, via rembg)
  2. Saves the transparent PNG to images/
  3. Adds the base64 entry to images.js
  4. Prints the WARD snippet to paste into jeans.html
"""

import sys, os, base64, re, shutil, io
import numpy as np
from PIL import Image
from rembg import remove

def autocrop(data, pad=8):
    img = Image.open(io.BytesIO(data)).convert('RGBA')
    arr = np.array(img)
    alpha = arr[:,:,3]
    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    rmin, rmax = np.where(rows)[0][[0,-1]]
    cmin, cmax = np.where(cols)[0][[0,-1]]
    h, w = arr.shape[:2]
    rmin, rmax = max(0, rmin-pad), min(h, rmax+pad)
    cmin, cmax = max(0, cmin-pad), min(w, cmax+pad)
    cropped = img.crop((cmin, rmin, cmax, rmax))
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()

def main():
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    src      = sys.argv[1]
    key      = sys.argv[2]
    label    = sys.argv[3]
    slot     = sys.argv[4]
    era      = sys.argv[5]

    base     = os.path.splitext(os.path.basename(src))[0]
    dest_name = base + '.png'
    dest_path = os.path.join(os.path.dirname(__file__), 'images', dest_name)

    # Remove background
    print(f'Removing background from {src}...')
    with open(src, 'rb') as f:
        data = remove(f.read())

    # Auto-crop transparent edges
    data = autocrop(data)

    # Fit to slot-appropriate canvas size
    canvas_size = {'top': (350,320), 'full': (300,500), 'bottom': (200,430),
                   'shoes': (320,160), 'acc': (200,200)}.get(slot, (350,320))
    img = Image.open(io.BytesIO(data)).convert('RGBA')
    tw, th = canvas_size
    img.thumbnail((tw, th), Image.LANCZOS)
    canvas = Image.new('RGBA', (tw, th), (0,0,0,0))
    canvas.paste(img, ((tw-img.width)//2, (th-img.height)//2))
    buf = io.BytesIO()
    canvas.save(buf, format='PNG')
    data = buf.getvalue()

    with open(dest_path, 'wb') as f:
        f.write(data)
    print(f'Saved → images/{dest_name}  ({tw}x{th})')

    # Encode to base64
    b64 = 'data:image/png;base64,' + base64.b64encode(data).decode('utf-8')

    # Insert into images.js
    js_path = os.path.join(os.path.dirname(__file__), 'images.js')
    with open(js_path, 'r') as f:
        content = f.read()

    new_entry = f'    {key}: "{b64}",\n'
    content = content.replace('  }\n});\n', new_entry + '  }\n});\n')

    with open(js_path, 'w') as f:
        f.write(content)
    print(f'Added {key} to images.js')

    # Print the WARD snippet
    section = 'tops' if slot in ('top', 'full', 'acc') else 'bottoms'
    gender_hint = 'female' if key.startswith('w') else 'male'
    print(f'\nAdd this line to WARD.{gender_hint}.{section} in jeans.html:')
    print(f"      {{key:'{key}', label:'{label}', era:'{era}', slot:'{slot}'}},")

if __name__ == '__main__':
    main()
