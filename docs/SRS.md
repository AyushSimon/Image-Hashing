**Software Requirements Specification (SRS)**

**Project: Image Hashing for Near-Duplicate Image Detection**

## 1. Introduction

This document specifies the software requirements for a mini-project that implements an image hashing system. The system generates compact perceptual fingerprints of images and uses them to detect duplicate or near-duplicate images (resized, compressed, cropped, or watermarked versions of the same picture).

## 2. Objectives

- To generate perceptual hash values (aHash, pHash, dHash) for a given set of images using Python.

- To detect duplicate and near-duplicate images by comparing hash values using Hamming distance.

- To compare the accuracy and performance of different hashing algorithms.

- To build a simple tool/interface that accepts a folder or pair of images and reports similarity.

- To evaluate the system's robustness against resizing, compression, and minor edits.

## 3. Scope

The system will process a local dataset of images, compute hashes, and identify similar/duplicate images. It is intended as an academic demonstration, not a production-scale search engine.

## 4. Functional Requirements

- FR1: The system shall accept image files (JPEG/PNG) as input.

- FR2: The system shall compute a perceptual hash for each image.

- FR3: The system shall compare two or more hashes and output a similarity/difference score.

- FR4: The system shall flag image pairs as duplicates if the score is below a threshold.

- FR5: The system shall display or export results (e.g., list of duplicate pairs).

## 5. Non-Functional Requirements

- Performance: Hash computation for a single image should complete within 1 second.

- Usability: The tool should be operable via a simple command-line or GUI interface.

- Portability: The system shall run on any platform supporting Python 3.

- Reliability: The system shall handle corrupt or unsupported files gracefully.

## 6. System Requirements

| **Requirement** | **Details** |
| --- | --- |
| Language | Python 3.8+ |
| Libraries | imagehash, Pillow, NumPy, OpenCV (optional) |
| Hardware | Any standard PC (no GPU required) |
| Input | Set of sample/test images (dataset folder) |
| Output | Hash values, similarity scores, duplicate report |

## 7. Assumptions & Constraints

- The dataset used for testing is limited in size and locally stored.

- The project focuses on perceptual hashing, not cryptographic hashing.

- Accuracy depends on the chosen hashing algorithm and threshold value.
