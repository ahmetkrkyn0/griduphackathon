#!/usr/bin/env python3
"""OpenSCAD bagimsiz, saf Python/NumPy ile din-kutu.scad geometrisini ikili (binary) STL'e ceviren uretec.

Olculer hardware/mekanik/din-kutu.scad ile birebir aynidir:
  - Govde dis: 125 x 60 x 92 mm
  - Cidar kalinligi: 2.2 mm
  - DIN ray klipsi: 35 mm EN 50022 ray yuvasi
  - Alt klemens kesikleri: 10 x (8 x 14 mm, 3 mm aralik)
  - Ust anten delikleri: 2 x SMA deligi (8 mm cap)
"""

from __future__ import annotations

import struct
from pathlib import Path
import numpy as np

W = 125.0  # mm (X)
D = 60.0   # mm (Y)
H = 92.0   # mm (Z)
WALL = 2.2 # mm

DIN_W = 35.0
DIN_D = 7.5
DIN_TRAVEL = 4.0

CONN_W = 8.0
CONN_H = 14.0
CONN_GAP = 3.0
CONN_COUNT = 10

ANT_D = 8.0


def add_quad(triangles: list[tuple], p0, p1, p2, p3):
    """Adds two triangles for a quad (p0, p1, p2, p3) in CCW winding."""
    triangles.append((p0, p1, p2))
    triangles.append((p0, p2, p3))


def add_box(triangles: list[tuple], x0, y0, z0, x1, y1, z1):
    """Adds 6 faces (12 triangles) for an axis-aligned box [x0..x1, y0..y1, z0..z1]."""
    # -Z (bottom)
    add_quad(triangles, (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))
    # +Z (top)
    add_quad(triangles, (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1))
    # -Y (front)
    add_quad(triangles, (x0, y0, z0), (x0, y0, z1), (x1, y0, z1), (x1, y0, z0))
    # +Y (back)
    add_quad(triangles, (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))
    # -X (left)
    add_quad(triangles, (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1))
    # +X (right)
    add_quad(triangles, (x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0))


def compute_normal(v0, v1, v2) -> tuple[float, float, float]:
    a = np.array(v1) - np.array(v0)
    b = np.array(v2) - np.array(v0)
    c = np.cross(a, b)
    norm = np.linalg.norm(c)
    if norm < 1e-9:
        return (0.0, 0.0, 1.0)
    c /= norm
    return (float(c[0]), float(c[1]), float(c[2]))


def generate_enclosure_stl(output_path: Path):
    triangles: list[tuple] = []

    # 1. Taban (bottom wall): z from 0 to WALL
    add_box(triangles, 0, 0, 0, W, D, WALL)

    # 2. Yan duvarlar (left & right): x in [0..WALL] and [W-WALL..W] from z=WALL to H
    add_box(triangles, 0, 0, WALL, WALL, D, H)
    add_box(triangles, W - WALL, 0, WALL, W, D, H)

    # 3. Arka duvar (back wall: y in [D-WALL..D]) from z=WALL to H
    add_box(triangles, WALL, D - WALL, WALL, W - WALL, D, H)

    # 4. On duvar (front wall with 10 connector cutouts):
    # Connector total span
    conn_total = CONN_COUNT * CONN_W + (CONN_COUNT - 1) * CONN_GAP
    conn_start_x = (W - conn_total) / 2.0

    # Sol kenar on duvar
    add_box(triangles, WALL, 0, WALL, conn_start_x, WALL, H)
    # Sag kenar on duvar
    add_box(triangles, conn_start_x + conn_total, 0, WALL, W - WALL, WALL, H)
    # Kesiklerin uzerindeki ust on serit (z from CONN_H to H)
    add_box(triangles, conn_start_x, 0, CONN_H, conn_start_x + conn_total, WALL, H)

    # Kesikler arasindaki kucuk sutunlar (z from WALL to CONN_H)
    for i in range(CONN_COUNT - 1):
        col_x0 = conn_start_x + (i + 1) * CONN_W + i * CONN_GAP
        col_x1 = col_x0 + CONN_GAP
        add_box(triangles, col_x0, 0, WALL, col_x1, WALL, CONN_H)

    # 5. Ust kapak kenar dudaklari ve tavan paneli (anten deligi bosluklariyla)
    # 2 delik: SMA U.FL gecis deligi (X=37.5, Y=30) ve Hucresel (X=87.5, Y=30)
    # Tavan kismi (z in [H - WALL .. H])
    add_box(triangles, WALL, WALL, H - WALL, W * 0.25, D - WALL, H)
    add_box(triangles, W * 0.35, WALL, H - WALL, W * 0.65, D - WALL, H)
    add_box(triangles, W * 0.75, WALL, H - WALL, W - WALL, D - WALL, H)
    # Deliklerin onu ve arkasi seritleri
    add_box(triangles, W * 0.25, WALL, H - WALL, W * 0.35, D / 2.0 - ANT_D / 2.0, H)
    add_box(triangles, W * 0.25, D / 2.0 + ANT_D / 2.0, H - WALL, W * 0.35, D - WALL, H)
    add_box(triangles, W * 0.65, WALL, H - WALL, W * 0.75, D / 2.0 - ANT_D / 2.0, H)
    add_box(triangles, W * 0.65, D / 2.0 + ANT_D / 2.0, H - WALL, W * 0.75, D - WALL, H)

    # 6. DIN Ray Klipsi (arka yuzeyde y > D)
    # translate([box_width/2 - din_rail_width/2 - 3, -3, box_height - 18])
    clip_x0 = W / 2.0 - DIN_W / 2.0 - 3.0
    clip_x1 = clip_x0 + DIN_W + 6.0
    clip_y0 = D
    clip_y1 = D + DIN_D + DIN_TRAVEL + 3.0
    clip_z0 = H - 18.0
    clip_z1 = clip_z0 + 16.0
    # Klips sol, sag ve ust kovan govdesi
    add_box(triangles, clip_x0, clip_y0, clip_z0, clip_x0 + 3.0, clip_y1, clip_z1)
    add_box(triangles, clip_x1 - 3.0, clip_y0, clip_z0, clip_x1, clip_y1, clip_z1)
    add_box(triangles, clip_x0 + 3.0, clip_y1 - 3.0, clip_z0, clip_x1 - 3.0, clip_y1, clip_z1)
    add_box(triangles, clip_x0, clip_y0, clip_z1 - 2.0, clip_x1, clip_y1, clip_z1)

    # Binary STL yaz
    num_triangles = len(triangles)
    header = b"GridUp Pano-Beyni DIN Enclosure (Fibox ARCA 92/125 PC V-0)" + b" " * (80 - 58)

    with open(output_path, "wb") as f:
        f.write(header[:80])
        f.write(struct.pack("<I", num_triangles))
        for v0, v1, v2 in triangles:
            n = compute_normal(v0, v1, v2)
            # 50 bytes per triangle
            data = struct.pack(
                "<3f3f3f3fH",
                n[0], n[1], n[2],
                v0[0], v0[1], v0[2],
                v1[0], v1[1], v1[2],
                v2[0], v2[1], v2[2],
                0
            )
            f.write(data)

    print(f"STL basariyla uretildi: {output_path} ({num_triangles} ucgen, {output_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    out = Path(__file__).parent / "din-kutu.stl"
    generate_enclosure_stl(out)
