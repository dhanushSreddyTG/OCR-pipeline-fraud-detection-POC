# OCR Fraud Detector

An advanced, high-performance proof-of-concept (POC) system for document integrity audits, metadata forensic investigations, and pixel-level digital tampering analysis. The system combines a responsive **Node.js Express** server with a concurrent **Python 3** forensic computing engine to deliver real-time, side-by-side visual comparisons, software footprint detection, and statistical JPEG anomaly diagnostics.

---

## 🚀 Key Features

* **Unified Python Analysis Engine (`fraud_detector.py`)**: Runs filesystem audits, metadata header extractions, and Error Level Analysis (ELA) inside a single, unified execution framework.
* **Concurrent Multi-Threading**: Executes the ELA pixel scans and structural metadata audits in parallel using Python `ThreadPoolExecutor` workers to bypass GIL wait cycles during Pillow image compression routines.
* **Aspect-Ratio Preserved Image Comparator**: Display original files alongside their ELA compression maps side-by-side without squishing or stretching, scaling naturally across layout viewports.
* **High-Precision Visual Overlay Maps**: Dynamically overlay pulsing, semi-transparent bounding boxes (`.anomaly-bounding-box`) over exact pixel-tampering coordinates.
* **Dynamic Color-Interpolated Risk Scoring**: Replaced traditional circular progress charts with numeric scoring boards colored via an HSL/RGB interpolation gradient scaling from green ($0\%$) to yellow ($50\%$) to red ($100\%$).
* **Collapsible Side-Control Center**: Minimizes controls to expand the workspace on larger monitors.
* **Collapsible Accordion Panels**: Stack metadata flags, extracted property trees, pixel coordinates, and raw JSON reports inside individual drawer toggles.
* **Multi-Format Upload Support**: Programmatically and visually handles `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`, and `.docx` uploads.

---

## 📐 Core Forensic Concepts & Pipelines

The application evaluates uploaded assets through two distinct, concurrent pipelines:

### 1. Metadata Forensic Auditor
Extracts physical and digital file footprints to find traces left behind by editing tools:
* **Filesystem Profiler**: Collects file size, permissions, and system timestamps. Maps numeric owner and group IDs (UID/GID) using Python's `pwd` and `grp` modules.
* **Checksum Verification**: Calculates cryptographic MD5 and SHA-256 signatures in 65KB chunks to prevent high RAM overhead.
* **Deep EXIF Parser**: Parses image headers to find cameras, orientation, and geotags.
* **GPS Coordinate Decoder**: Decodes nested GPS rational tuple arrays into decimal coordinates using the formula:
  $$\text{Decimal Degrees} = \text{Degrees} + \frac{\text{Minutes}}{60.0} + \frac{\text{Seconds}}{3600.0}$$
* **PDF Revision Tracker**: Audits the physical structure of PDF documents, checking for multiple `%EOF` trailers to flag hidden revisions or appended data blocks.
* **Office Document Parser**: Inspects Microsoft OpenXML properties (`docProps/core.xml` and `docProps/app.xml`) to extract the creating application, author, creation date, and modifications.
* **Software Footprint Database**: Validates tags against a list of common editing software (e.g. *Canva*, *Photoshop*, *GIMP*, *Acrobat*). Footprint matches yield high-risk ratings ($45$ risk points).

### 2. Pixel-Level Tampering Engine (Error Level Analysis - ELA)
Detects digital manipulations by checking pixel compression states:
* **JPEG Compression Physics**: JPEG operates on lossy $8\times8$ pixel matrices. Every time a JPEG is saved, color and edge detail are discarded. If an image is edited and resaved:
  1. The unedited parts undergo compression for the second time, experiencing minimal detail loss.
  2. The newly modified pixels undergo compression for the first time, experiencing a high rate of detail loss.
* **Resaving & Subtraction**: ELA converts the file to RGB, resaves it at a predefined quality factor ($90\%$), and calculates the absolute subtraction map:
  $$\text{Difference} = |\text{Original Pixel} - \text{Compressed Pixel}|$$
* **Luminance Normalization & Enhancement**: Normalizes differences to a grayscale channel ($L$) and amplifies them using a dynamic scaling factor based on peak pixel delta:
  $$\text{Scale Factor} = \frac{255}{\text{Max Error}}$$
  The scale factor is capped between $5.0$ and $25.0$ to produce a high-contrast forensic ELA visualization.
* **Grid-Based Statistical Anomaly Engine**: Segment the image into a $30\times30$ grid (900 blocks). A block is flagged as a compression anomaly if:
  $$\text{Block Mean} > \text{Global Block Average} + (3.5 \times \text{Global StdDev}) \quad \text{AND} \quad \text{Block Mean} > 0.8$$

---

## 🏗️ Project Structure

```text
ocr-fraud-detection-poc/
├── fraud_detector.py        # Unified Python Forensic Analysis & ELA Engine
├── metadata_forensics.py    # Extracts physical and digital file footprints
├── watermark_detector.py    # Detects digital watermarks and overlays
├── font_analyzer.py         # Analyzes text fonts for irregularities
├── ela_analyzer.py          # Error Level Analysis for tampering detection
├── run_batch_tests.py       # Script to run tests in batch mode
├── rule-engine/             # Configurable rule engines for validation
├── processors/              # Image and document processors
├── schemas/                 # Data validation and structural schemas
├── batch_results/           # Output directory for batch analyses
├── server.js                # Node.js Express Backend & Process Spawn Controller
├── package.json             # Node.js dependencies & scripts
├── public/                  # Web Dashboard Assets
│   ├── index.html           # Professional HTML5 dashboard mockup
│   ├── style.css            # Custom layout rules and visual variables
│   └── app.js               # State manager, animations, ELA overlay generator
└── README.md                # System documentation (This file)
```

---

## 🚦 Getting Started

### Prerequisites
* **Node.js** (v18+)
* **Python 3.8+**
* Python dependencies: `Pillow`
  ```bash
  pip install Pillow
  ```

### Running Locally
1. Install Node.js dependencies:
   ```bash
   npm install
   ```
2. Start the Express server:
   ```bash
   node server.js
   ```
3. Open your browser and navigate to:
   ```url
   http://localhost:3000/
   ```

---

## 🧪 API Verification

You can verify the backend analyzer endpoint programmatically using `curl` from a terminal:

```bash
curl -X POST -F "document=@/path/to/document.png" http://localhost:3000/api/analyze
```

---

## 👥 Contributors
* Forensic Document Shield Built By **Dhanush Reddy S**
* Confidential internal deployment. OCR fraud detector.
