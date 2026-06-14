from __future__ import annotations

from io import BytesIO, StringIO

import numpy as np
from PIL import Image


def heightmap_to_csv_bytes(heightmap: np.ndarray) -> bytes:
    csv_buffer = StringIO()
    np.savetxt(csv_buffer, heightmap, delimiter=",", fmt="%.6f")
    return csv_buffer.getvalue().encode("utf-8")


def heightmap_to_png_bytes(heightmap: np.ndarray) -> bytes:
    grayscale_array = np.rint(np.clip(heightmap, 0.0, 1.0) * 255).astype(np.uint8)
    image = Image.fromarray(grayscale_array, mode="L")
    png_buffer = BytesIO()
    image.save(png_buffer, format="PNG")
    return png_buffer.getvalue()
