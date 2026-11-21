# Image Hash Lab

Detect duplicate and near-duplicate images using **perceptual hashing** (aHash, dHash, pHash) and Hamming distance. Includes a command-line tool and an interactive web interface that runs locally.

A resized, compressed or watermarked copy of a picture gets a fingerprint that differs from the original in only a few bits, so look-alike images can be found automatically.

## Features

- Three perceptual hash algorithms: **aHash**, **dHash**, **pHash**
- Hamming-distance comparison with an adjustable duplicate threshold
- Duplicates grouped automatically, with a side-by-side comparison and similarity gauge
- Results exported to **CSV** and **Excel (.xlsx)** in the `csv/` folder, opened automatically
- Command-line tool for hashing, comparing, scanning folders and benchmarking
- Graceful handling of corrupt or unsupported files
- Light and dark mode, drag and drop, paste support

## Project structure

```
image-hashing/
├── imghash.py          Command-line tool (hash, compare, scan, evaluate, samples)
├── server.py           Local helper that serves the web app and saves results
├── run_app.bat         One-click launcher for Windows
├── web/
│   └── index.html      Web interface (all hashing runs in the browser)
├── docs/
│   └── SRS.md          Software Requirements Specification
├── csv/                Scan results are saved here (.csv and .xlsx)
├── requirements.txt
├── LICENSE
└── README.md
```

## Getting started

Requires **Python 3.8+**.

```bash
pip install -r requirements.txt
```

### Web app

Windows: double-click `run_app.bat`.
Any platform:

```bash
python server.py
```

Your browser opens automatically. Drop images in, or click **Try demo images**. After a scan, the results are saved into `csv/` and the CSV opens automatically.

> Opening `web/index.html` directly also works, but it cannot save files. Use `server.py` for saving.

### Command line

```bash
python imghash.py samples sample_images      # generate a demo dataset
python imghash.py hash photo.jpg             # show all three hashes
python imghash.py compare a.jpg b.png        # compare two images
python imghash.py scan sample_images --algo phash --threshold 10 --out duplicates.csv
python imghash.py evaluate sample_images --out evaluation.csv
```

Files passed to `--out` are written into the `csv/` folder.

## How it works

| Algorithm | Idea |
|---|---|
| **aHash** | Shrink to 8x8 grayscale, mark each pixel as above or below the average |
| **dHash** | Shrink to 9x8, compare each pixel with its right neighbour (gradients) |
| **pHash** | Shrink to 32x32, apply a DCT, keep the low frequencies, compare to the median |

Each produces a 64-bit hash. The **Hamming distance** is the number of bits that differ between two hashes. A distance at or below the threshold (default 10) marks the pair as a duplicate. Similarity is `1 - distance / 64`.

## Results

Benchmark on a synthetic dataset (threshold 10):

| | aHash | dHash | pHash |
|---|---|---|---|
| Resize 50% | 100% | 100% | 100% |
| JPEG compression | 100% | 100% | 100% |
| Watermark | 100% | 100% | 100% |
| Brightness +25% | 100% | 100% | 100% |
| 10% crop | 100% | 75% | 62.5% |
| 90° rotation | 0% | 0% | 0% |
| False positives | 3.6% | 0% | 0% |
| Time per hash | ~0.3 ms | ~0.3 ms | ~40 ms |

Detection rates are the share of edited copies correctly matched to their original. Results on real photos will differ; run `evaluate` on your own folder.

## Limitations

- Rotation, flipping and heavy cropping are not handled by any of these hashes.
- Thresholds are a trade-off: lower is stricter, higher catches more edits but risks false matches.
- Designed for small to medium local collections (pairwise comparison), not production-scale search.

## Requirements covered

Built from the [Software Requirements Specification](docs/SRS.md) for an image hashing mini-project: JPEG/PNG input, perceptual hashes, Hamming-distance comparison, threshold-based duplicate flagging, exported results, a simple interface, robustness evaluation, and graceful error handling.

## License

MIT, see [LICENSE](LICENSE).
