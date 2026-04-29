#!/usr/bin/env python3
"""
Re-process all men's clothing images with correct canvas aspect ratios
that match the CSS slot dimensions (stage 300x520px):
  top:    76% x 30%  → 228x156  → ratio 1.46 → canvas (350, 239)
  bottom: 68% x 52%  → 204x270  → ratio 0.756 → canvas (256, 339)
  shoes:  68% x 13%  → 204x68   → ratio 3.0  → canvas (300, 100)
  acc:    35% x 9%   → 105x47   → ratio 2.23 → canvas (220, 98)
"""

import sys, os, base64, io
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))

CANVAS = {
    'top':    (350, 239),
    'bottom': (256, 339),
    'shoes':  (300, 100),
    'acc':    (220, 98),
    'full':   (300, 500),
    'bag':    (200, 200),
}

# Maps: (image_filename_stem, ward_key, slot)
MENS_ITEMS = [
    # Tops
    ('mens-flannel-shirt-1900s40s',        'mens_shirt',    'top'),
    ('mens-denim-vest-1900s40s',           'mens_vest',     'top'),
    ('mens-white-tee-1950s',               'm50_tee',       'top'),
    ('mens-leather-jacket-1950s',          'm50_jacket',    'top'),
    ('mens-floral-shirt-1960s',            'm60_shirt',     'top'),
    ('mens-denim-jacket-1970s',            'm70_jacket',    'top'),
    ('mens-stripe-shirt-1970s',            'm70_shirt',     'top'),
    ('mens-tweed-blazer-1980s',            'm1980_blazer',  'top'),
    ('mens-striped-dress-shirt-1980s',     'm1980_shirt',   'top'),
    ('mens-psychobunny-tee-2000s',         'm2000_tee',     'top'),
    ('mens-striped-shortslv-shirt-2000s',  'm2000_shirt',   'top'),
    ('mens-oioi-oversized-tee-2010s',      'm2010_tee',     'top'),
    ('mens-striped-rugby-shirt-2010s',     'm2010_rugby',   'top'),
    ('mens-grunge-tee-1990s',              'm80_tee',       'top'),
    ('mens-plaid-flannel-1990s',           'm80_flannel',   'top'),
    # Acc
    ('mens-round-shades-1960s',            'm60_shades',    'acc'),
    # Bottoms
    ('mens-dark-jeans-1900s40s',           'mens_jeans',    'bottom'),
    ('mens-cuffed-jeans-1950s',            'm50_jeans',     'bottom'),
    ('mens-patched-jeans-1960s',           'm60_jeans',     'bottom'),
    ('mens-flare-jeans-1970s',             'm70_jeans',     'bottom'),
    ('mens-faded-straight-jeans-1980s',    'm1980_jeans',   'bottom'),
    ('mens-ripped-jeans-1990s',            'm80_jeans',     'bottom'),
    ('mens-rock-revival-jeans-2000s',      'm2000_jeans',   'bottom'),
    ('mens-barrel-leg-jeans-2010s',        'm2010_jeans',   'bottom'),
    # Shoes
    ('mens-work-boots-1900s40s',           'mens_boots',    'shoes'),
    ('mens-saddle-shoes-1950s',            'm50_shoes',     'shoes'),
    ('mens-canvas-sneakers-1960s',         'm60_shoes',     'shoes'),
    ('mens-platform-oxfords-1970s',        'm70_shoes',     'shoes'),
    ('mens-black-derby-oxfords-1980s',     'm1980_shoes',   'shoes'),
    ('mens-hightop-converse-1990s',        'm80_shoes',     'shoes'),
    ('mens-dc-skate-shoes-2000s',          'm2000_shoes',   'shoes'),
    ('mens-new-balance-990-2010s',         'm2010_shoes',   'shoes'),
]


def autocrop(img, pad=6):
    arr = np.array(img)
    alpha = arr[:, :, 3]
    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not rows.any():
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    h, w = arr.shape[:2]
    rmin = max(0, rmin - pad)
    rmax = min(h, rmax + pad)
    cmin = max(0, cmin - pad)
    cmax = min(w, cmax + pad)
    return img.crop((cmin, rmin, cmax, rmax))


def process_image(stem, key, slot, force_remove_bg=True):
    src_path = os.path.join(HERE, 'images', stem + '.png')
    if not os.path.exists(src_path):
        print(f'  MISSING: {src_path}')
        return None

    print(f'  Processing {stem} → {key} ({slot})...')

    with open(src_path, 'rb') as f:
        raw = f.read()

    # Remove background (always re-apply for consistency)
    print(f'    removing background...')
    removed = remove(raw)

    img = Image.open(io.BytesIO(removed)).convert('RGBA')
    img = autocrop(img)

    tw, th = CANVAS[slot]

    # Scale content to fill ~90% of the canvas dimension (leaves small margin)
    scale_w = tw * 0.90
    scale_h = th * 0.90
    img.thumbnail((int(scale_w), int(scale_h)), Image.LANCZOS)

    canvas = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    # For shoes, align to bottom; for others, align slightly up from center
    if slot == 'shoes':
        paste_y = th - img.height
    elif slot == 'top':
        paste_y = 0  # pin to top of slot
    else:
        paste_y = (th - img.height) // 2
    paste_x = (tw - img.width) // 2
    canvas.paste(img, (paste_x, paste_y))

    # Save processed PNG back to images/
    buf = io.BytesIO()
    canvas.save(buf, format='PNG')
    data = buf.getvalue()

    with open(src_path, 'wb') as f:
        f.write(data)

    b64 = 'data:image/png;base64,' + base64.b64encode(data).decode('utf-8')
    return b64


def update_images_js(updates):
    js_path = os.path.join(HERE, 'images.js')
    print(f'\nReading images.js ({os.path.getsize(js_path)//1024}KB)...')
    with open(js_path, 'r') as f:
        content = f.read()

    for key, b64 in updates.items():
        old_pattern = f'    {key}: "data:image/png;base64,'
        # Find existing entry
        start = content.find(old_pattern)
        if start == -1:
            # Key doesn't exist — append before closing
            new_entry = f'    {key}: "{b64}",\n'
            content = content.replace('  }\n});\n', new_entry + '  }\n});\n')
            print(f'  Added new key: {key}')
        else:
            # Replace existing entry
            end = content.find('",\n', start) + 3
            new_entry = f'    {key}: "{b64}",\n'
            content = content[:start] + new_entry + content[end:]
            print(f'  Updated key: {key}')

    with open(js_path, 'w') as f:
        f.write(content)
    print(f'Wrote images.js ({os.path.getsize(js_path)//1024}KB)')


def main():
    print(f'Re-processing {len(MENS_ITEMS)} men\'s clothing items...\n')
    updates = {}

    for stem, key, slot in MENS_ITEMS:
        b64 = process_image(stem, key, slot)
        if b64:
            updates[key] = b64

    print(f'\nProcessed {len(updates)}/{len(MENS_ITEMS)} items successfully.')
    update_images_js(updates)
    print('\nDone.')


if __name__ == '__main__':
    main()
