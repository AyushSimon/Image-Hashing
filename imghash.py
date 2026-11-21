#!/usr/bin/env python3
"""
Image Hashing for Near-Duplicate Image Detection
------------------------------------------------
Computes perceptual hashes (aHash, pHash, dHash), compares them with Hamming
distance, flags duplicates, and benchmarks robustness against common edits.

Commands
  hash      Print hashes of one image
  compare   Compare two images
  scan      Find duplicate / near-duplicate pairs in a folder
  evaluate  Benchmark algorithms (accuracy, robustness, speed)
  samples   Generate a synthetic sample dataset to try the tool on
"""
import argparse
import csv
import io
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

import imagehash
from PIL import Image, ImageDraw, ImageEnhance, UnidentifiedImageError

# ----------------------------------------------------------------------------
# Core hashing  (FR1, FR2)
# ----------------------------------------------------------------------------
ALGORITHMS = {
    "ahash": imagehash.average_hash,
    "phash": imagehash.phash,
    "dhash": imagehash.dhash,
}
SUPPORTED_EXT = {".jpg", ".jpeg", ".png"}
DEFAULT_HASH_SIZE = 8          # 8x8 -> 64-bit hash
DEFAULT_THRESHOLD = 10         # Hamming distance <= threshold => duplicate


def load_image(path):
    """Open an image; raises ValueError with a friendly message on failure."""
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXT:
        raise ValueError(f"unsupported file type: {path.name}")
    try:
        img = Image.open(path)
        img.load()
        return img
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise ValueError(f"corrupt or unreadable image: {path.name} ({e})")


def compute_hash(img, algo="phash", hash_size=DEFAULT_HASH_SIZE):
    return ALGORITHMS[algo](img, hash_size=hash_size)


def hash_file(path, algo="phash", hash_size=DEFAULT_HASH_SIZE):
    return compute_hash(load_image(path), algo, hash_size)


# ----------------------------------------------------------------------------
# Comparison  (FR3, FR4)
# ----------------------------------------------------------------------------
def hamming(h1, h2):
    return h1 - h2


def similarity_pct(distance, hash_size=DEFAULT_HASH_SIZE):
    bits = hash_size * hash_size
    return round(100.0 * (1 - distance / bits), 2)


def is_duplicate(distance, threshold=DEFAULT_THRESHOLD):
    return distance <= threshold


# ----------------------------------------------------------------------------
# Folder scan  (FR5, reliability)
# ----------------------------------------------------------------------------
def list_images(folder):
    return sorted(p for p in Path(folder).rglob("*")
                  if p.is_file() and p.suffix.lower() in SUPPORTED_EXT)


def scan_folder(folder, algo, threshold, hash_size=DEFAULT_HASH_SIZE):
    hashes, skipped = {}, []
    for p in list_images(folder):
        try:
            hashes[p] = hash_file(p, algo, hash_size)
        except Exception as e:                      # graceful handling
            skipped.append((p.name, str(e)))
    pairs = []
    for (a, ha), (b, hb) in combinations(hashes.items(), 2):
        d = hamming(ha, hb)
        if is_duplicate(d, threshold):
            pairs.append({"image_a": str(a), "image_b": str(b),
                          "distance": int(d),
                          "similarity_pct": similarity_pct(d, hash_size)})
    pairs.sort(key=lambda r: r["distance"])
    return hashes, pairs, skipped


def export_pairs(pairs, out_path):
    out = Path(out_path)
    if out.suffix.lower() == ".json":
        out.write_text(json.dumps(pairs, indent=2))
    else:
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["image_a", "image_b", "distance", "similarity_pct"])
            w.writeheader()
            w.writerows(pairs)


# ----------------------------------------------------------------------------
# Image transformations used for robustness evaluation
# ----------------------------------------------------------------------------
def t_resize(img):
    return img.resize((max(1, img.width // 2), max(1, img.height // 2)))

def t_jpeg(img):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=30)
    buf.seek(0)
    return Image.open(buf)

def t_crop(img):
    w, h = img.size
    return img.crop((int(w * .05), int(h * .05), int(w * .95), int(h * .95)))

def t_watermark(img):
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    d.text((im.width // 20, im.height - im.height // 8), "(c) SAMPLE WATERMARK", fill=(255, 255, 255))
    return im

def t_brightness(img):
    return ImageEnhance.Brightness(img.convert("RGB")).enhance(1.25)

def t_rotate(img):
    return img.rotate(90, expand=True)   # expected to be a hard case

TRANSFORMS = {
    "resize_50%": t_resize,
    "jpeg_q30": t_jpeg,
    "crop_10%": t_crop,
    "watermark": t_watermark,
    "brightness+25%": t_brightness,
    "rotate_90": t_rotate,
}


def evaluate(folder, threshold, hash_size=DEFAULT_HASH_SIZE):
    # top-level files only, so a "near_duplicates" subfolder is not treated as originals
    paths = sorted(p for p in Path(folder).iterdir()
                   if p.is_file() and p.suffix.lower() in SUPPORTED_EXT)
    images = []
    for p in paths:
        try:
            images.append((p.name, load_image(p).convert("RGB")))
        except ValueError as e:
            print(f"  skipped: {e}")
    if len(images) < 2:
        sys.exit("Need at least 2 valid images to evaluate.")

    results = []
    for algo in ALGORITHMS:
        # speed
        t0 = time.perf_counter()
        base = {n: compute_hash(im, algo, hash_size) for n, im in images}
        avg_ms = (time.perf_counter() - t0) / len(images) * 1000

        row = {"algorithm": algo, "avg_hash_ms": round(avg_ms, 2)}
        # positives: edited version vs original
        for tname, fn in TRANSFORMS.items():
            dists = [hamming(base[n], compute_hash(fn(im), algo, hash_size)) for n, im in images]
            row[f"{tname}_avg_dist"] = round(sum(dists) / len(dists), 2)
            row[f"{tname}_detected_%"] = round(100 * sum(d <= threshold for d in dists) / len(dists), 1)
        # negatives: different images should NOT match
        neg = [hamming(base[a], base[b]) for a, b in combinations(base, 2)]
        row["false_positive_%"] = round(100 * sum(d <= threshold for d in neg) / len(neg), 1)
        row["avg_distance_unrelated"] = round(sum(neg) / len(neg), 2)
        results.append(row)
    return results


# ----------------------------------------------------------------------------
# Sample dataset generator
# ----------------------------------------------------------------------------
def make_samples(folder, n=8, size=(400, 300), seed=42):
    rnd = random.Random(seed)
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    dup = out / "near_duplicates"
    dup.mkdir(exist_ok=True)
    originals = []
    for i in range(n):
        img = Image.new("RGB", size, tuple(rnd.randint(0, 255) for _ in range(3)))
        d = ImageDraw.Draw(img)
        for _ in range(12):
            x0, y0 = rnd.randint(0, size[0] - 60), rnd.randint(0, size[1] - 60)
            x1, y1 = x0 + rnd.randint(30, 200), y0 + rnd.randint(30, 150)
            col = tuple(rnd.randint(0, 255) for _ in range(3))
            (d.ellipse if rnd.random() < .5 else d.rectangle)([x0, y0, x1, y1], fill=col)
        p = out / f"original_{i + 1}.png"
        img.save(p)
        originals.append((p, img))
    # add near-duplicates for the first 3 originals
    for i, (p, img) in enumerate(originals[:3]):
        t_resize(img).save(dup / f"original_{i + 1}_resized.jpg")
        t_jpeg(img).save(dup / f"original_{i + 1}_compressed.jpg")
        t_watermark(img).save(dup / f"original_{i + 1}_watermarked.png")
    # one corrupt file to demonstrate graceful handling
    (dup / "corrupt.jpg").write_bytes(b"this is not an image")
    print(f"Created sample dataset in {out}/")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def csv_path(name):
    """Results always go into the csv/ folder next to this script."""
    folder = Path(__file__).resolve().parent / "csv"
    folder.mkdir(exist_ok=True)
    return str(folder / Path(name).name)


def main():
    ap = argparse.ArgumentParser(description="Perceptual image hashing & near-duplicate detection")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, algo=True):
        if algo:
            p.add_argument("--algo", choices=list(ALGORITHMS), default="phash")
        p.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                       help="max Hamming distance to call a duplicate (default 10)")
        p.add_argument("--hash-size", type=int, default=DEFAULT_HASH_SIZE)

    p = sub.add_parser("hash", help="print hashes of an image")
    p.add_argument("image")
    p.add_argument("--hash-size", type=int, default=DEFAULT_HASH_SIZE)

    p = sub.add_parser("compare", help="compare two images")
    p.add_argument("image1"); p.add_argument("image2")
    common(p, algo=False)

    p = sub.add_parser("scan", help="find duplicate pairs in a folder")
    p.add_argument("folder"); p.add_argument("--out", help="export to .csv or .json")
    common(p)

    p = sub.add_parser("evaluate", help="benchmark all algorithms")
    p.add_argument("folder"); p.add_argument("--out", help="export results to .csv")
    common(p, algo=False)

    p = sub.add_parser("samples", help="generate a synthetic sample dataset")
    p.add_argument("folder", nargs="?", default="sample_images")

    a = ap.parse_args()
    if getattr(a, "out", None):
        a.out = csv_path(a.out)

    try:
        if a.cmd == "hash":
            img = load_image(a.image)
            for name in ALGORITHMS:
                print(f"{name}: {compute_hash(img, name, a.hash_size)}")

        elif a.cmd == "compare":
            i1, i2 = load_image(a.image1), load_image(a.image2)
            print(f"{'Algorithm':<8} {'Distance':>8} {'Similarity':>11}  Verdict")
            for name in ALGORITHMS:
                d = hamming(compute_hash(i1, name, a.hash_size), compute_hash(i2, name, a.hash_size))
                v = "DUPLICATE" if is_duplicate(d, a.threshold) else "different"
                print(f"{name:<8} {int(d):>8} {similarity_pct(d, a.hash_size):>10}%  {v}")

        elif a.cmd == "scan":
            hashes, pairs, skipped = scan_folder(a.folder, a.algo, a.threshold, a.hash_size)
            print(f"Hashed {len(hashes)} images with {a.algo} (threshold {a.threshold})")
            for name, why in skipped:
                print(f"  [skipped] {name}: {why}")
            print(f"\nFound {len(pairs)} duplicate/near-duplicate pair(s):")
            for r in pairs:
                print(f"  {Path(r['image_a']).name}  <->  {Path(r['image_b']).name}"
                      f"   dist={r['distance']}  sim={r['similarity_pct']}%")
            if a.out:
                export_pairs(pairs, a.out)
                print(f"\nExported to {a.out}")

        elif a.cmd == "evaluate":
            res = evaluate(a.folder, a.threshold, a.hash_size)
            for r in res:
                print(f"\n== {r['algorithm'].upper()} ==  avg time/hash: {r['avg_hash_ms']} ms")
                for t in TRANSFORMS:
                    print(f"  {t:<15} avg dist {r[t + '_avg_dist']:>5}   detected {r[t + '_detected_%']:>5}%")
                print(f"  false positives (unrelated pairs): {r['false_positive_%']}%"
                      f"  (avg dist {r['avg_distance_unrelated']})")
            if a.out:
                with open(a.out, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
                    w.writeheader(); w.writerows(res)
                print(f"\nExported to {a.out}")

        elif a.cmd == "samples":
            make_samples(a.folder)

    except ValueError as e:
        sys.exit(f"Error: {e}")
    except FileNotFoundError as e:
        sys.exit(f"Error: file or folder not found ({e})")


if __name__ == "__main__":
    main()
