from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "demo-garments" / "real"


def fabric(h: int, w: int, color: tuple[int, int, int]) -> np.ndarray:
    base = np.zeros((h, w, 4), dtype=np.uint8)
    base[:, :, :3] = color
    base[:, :, 3] = 0
    noise = np.random.default_rng(8).normal(0, 7, (h, w, 1)).astype(np.int16)
    rgb = np.clip(base[:, :, :3].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    base[:, :, :3] = rgb
    return base


def poly(img: np.ndarray, points: list[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
    cv2.fillPoly(img, [np.array(points, dtype=np.int32)], color, lineType=cv2.LINE_AA)


def line(img: np.ndarray, a: tuple[int, int], b: tuple[int, int], color=(255, 255, 255, 80), thick=3) -> None:
    cv2.line(img, a, b, color, thick, lineType=cv2.LINE_AA)


def garment(kind: str, color: tuple[int, int, int], accent=(235, 235, 235)) -> np.ndarray:
    img = fabric(900, 700, color)
    c = (*color, 255)
    a = (*accent, 255)

    if kind in {"shirt", "tshirt", "hoodie"}:
        poly(img, [(210, 155), (490, 155), (555, 330), (505, 370), (470, 265), (492, 790), (208, 790), (230, 265), (195, 370), (145, 330)], c)
        if kind == "shirt":
            poly(img, [(292, 155), (350, 245), (408, 155)], (245, 245, 245, 255))
            poly(img, [(270, 160), (335, 245), (302, 270), (245, 168)], c)
            poly(img, [(430, 160), (365, 245), (398, 270), (455, 168)], c)
            for y in range(295, 735, 72):
                cv2.circle(img, (350, y), 8, a, -1, lineType=cv2.LINE_AA)
            line(img, (350, 250), (350, 770), (255, 255, 255, 90), 2)
        elif kind == "hoodie":
            poly(img, [(252, 162), (350, 245), (448, 162), (422, 105), (350, 82), (278, 105)], (*color, 245))
            line(img, (320, 238), (296, 390), (245, 245, 245, 140), 3)
            line(img, (380, 238), (404, 390), (245, 245, 245, 140), 3)
            cv2.ellipse(img, (350, 595), (118, 56), 0, 0, 360, (0, 0, 0, 45), 4, lineType=cv2.LINE_AA)
        else:
            cv2.ellipse(img, (350, 170), (58, 38), 0, 0, 360, (255, 255, 255, 120), 5, lineType=cv2.LINE_AA)
    elif kind == "jacket":
        poly(img, [(190, 150), (510, 150), (575, 345), (515, 386), (478, 270), (506, 790), (194, 790), (222, 270), (185, 386), (125, 345)], c)
        poly(img, [(225, 168), (335, 365), (282, 390), (205, 185)], (35, 42, 50, 255))
        poly(img, [(475, 168), (365, 365), (418, 390), (495, 185)], (35, 42, 50, 255))
        line(img, (350, 160), (350, 790), (235, 235, 235, 100), 4)
        for x in (280, 420):
            cv2.rectangle(img, (x - 45, 465), (x + 45, 535), (255, 255, 255, 65), 3, lineType=cv2.LINE_AA)
    elif kind == "trousers":
        poly(img, [(260, 120), (440, 120), (470, 830), (372, 830), (350, 370), (328, 830), (230, 830)], c)
        line(img, (350, 145), (350, 825), (255, 255, 255, 90), 3)
        line(img, (260, 130), (440, 130), (255, 255, 255, 120), 5)
        for x in (295, 405):
            cv2.ellipse(img, (x, 190), (45, 18), 0, 0, 180, (0, 0, 0, 45), 3, lineType=cv2.LINE_AA)
    elif kind == "suit":
        poly(img, [(185, 135), (515, 135), (585, 345), (528, 388), (480, 280), (520, 805), (180, 805), (220, 280), (172, 388), (115, 345)], c)
        poly(img, [(275, 142), (350, 360), (425, 142), (392, 142), (350, 222), (308, 142)], (245, 245, 245, 255))
        poly(img, [(220, 160), (340, 385), (285, 430), (185, 180)], c)
        poly(img, [(480, 160), (360, 385), (415, 430), (515, 180)], c)
        line(img, (350, 365), (350, 800), (255, 255, 255, 80), 3)
        for y in (455, 530, 605):
            cv2.circle(img, (350, y), 8, a, -1, lineType=cv2.LINE_AA)
    elif kind == "dress":
        poly(img, [(250, 150), (450, 150), (480, 350), (565, 825), (135, 825), (220, 350)], c)
        cv2.ellipse(img, (350, 157), (62, 38), 0, 0, 360, (255, 255, 255, 110), 4, lineType=cv2.LINE_AA)
        line(img, (238, 360), (462, 360), (255, 255, 255, 120), 4)
        for x in (260, 350, 440):
            line(img, (x, 370), (x - 65, 810), (255, 255, 255, 45), 2)

    alpha = img[:, :, 3] > 0
    shadow = cv2.GaussianBlur(alpha.astype(np.uint8) * 130, (39, 39), 0)
    canvas = np.zeros_like(img)
    canvas[:, :, 3] = shadow
    canvas[:, :, :3] = 25
    canvas = np.maximum(canvas, img)
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    specs = {
        "real-white-oxford-shirt.webp": ("shirt", (236, 238, 232), (45, 55, 70)),
        "real-black-vneck-tshirt.webp": ("tshirt", (28, 29, 31), (210, 210, 210)),
        "real-sage-linen-shirt.webp": ("shirt", (133, 154, 130), (245, 245, 238)),
        "real-denim-jacket.webp": ("jacket", (54, 95, 140), (230, 230, 225)),
        "real-charcoal-hoodie.webp": ("hoodie", (64, 68, 72), (230, 230, 230)),
        "real-khaki-chinos.webp": ("trousers", (164, 147, 105), (245, 240, 225)),
        "real-black-tailored-trousers.webp": ("trousers", (32, 34, 37), (210, 210, 210)),
        "real-navy-suit-jacket.webp": ("suit", (25, 45, 78), (230, 230, 230)),
        "real-grey-two-piece-suit.webp": ("suit", (100, 104, 108), (235, 235, 235)),
        "real-burgundy-midi-dress.webp": ("dress", (118, 35, 55), (245, 225, 230)),
    }
    for filename, (kind, color, accent) in specs.items():
        cv2.imwrite(str(OUT / filename), garment(kind, color, accent), [cv2.IMWRITE_WEBP_QUALITY, 92])


if __name__ == "__main__":
    main()
