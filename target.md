from google.colab import files

markdown_content = """# MASTER TECHNICAL SPECIFICATION: SPEECH EMOTION RECOGNITION (SER) SYSTEM
**Document Version:** 2.4.0
**Target Environment:** Ubuntu 22.04 / 24.04 LTS, Python 3.10+, Node.js / PM2, Apache 2.4
**Primary Objective:** End-to-end design, training, inference optimization, API packaging, and cloud deployment of a robust Speech Emotion Recognition system for 7 distinct emotional classes.

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

  +-----------------------------------------------------------------------+
  |                             CLIENT LAYER                              |
  |   +--------------------------+     +------------------------------+   |
  |   |   Web UI (Microphone)    |     |   Batch Audio File Upload    |   |
  |   +-------------+------------+     +--------------+---------------+   |
  +-----------------|---------------------------------|-------------------+
                    | HTTP POST (multipart/form-data) |
                    v                                 v
  +-----------------------------------------------------------------------+
  |                  REVERSE PROXY & GATEWAY (Apache 2.4)                 |
  |     - SSL Termination (Let's Encrypt / Certbot)                       |
  |     - ProxyPass / ProxyPassReverse -> http://127.0.0.1:8000           |
  |     - Request Size Filtering & DDoS Throttling (mod_ratelimit)        |
  +-----------------------------------|-----------------------------------+
                                      | Local Reverse Proxy
                                      v
  +-----------------------------------------------------------------------+
  |              APPLICATION LAYER (FastAPI / Uvicorn + PM2)              |
  |   +---------------------------------------------------------------+   |
  |   | REST Endpoints: /health, /predict, /predict/batch             |   |
  |   | Middleware: CORS, Request Validation, Global Exception Catch  |   |
  |   +-------------------------------+-------------------------------+   |
  |                                   | In-Memory Stream
  |                                   v
  |   +---------------------------------------------------------------+   |
  |   | Preprocessing Pipeline:                                       |   |
  |   | - Audio Normalization (Mono, 16kHz resample)                  |   |
  |   | - Dynamic Feature Extraction (MFCC 40 + Tonnetz 6 = 46 dims)  |   |
  |   | - L1 Norm Vector Transformation                               |   |
  |   +-------------------------------+-------------------------------+   |
  |                                   | Tensor Shape: (1, 46, 1)
  |                                   v
  |   +---------------------------------------------------------------+   |
  |   | Inference Engine:                                             |   |
  |   | - Cascade 1D-CNN Model (`CascadeCovM1_BEST.h5`)               |   |
  |   | - Softmax Probability Distribution Vector                     |   |
  |   +---------------------------------------------------------------+   |
  +-----------------------------------------------------------------------+

---

## 2. MATHEMATICAL & FEATURE EXTRACTION SPECIFICATION

### 2.1 Target Classes (Label Mapping)
The system strictly supports 7 mutually exclusive emotion categories:
*   `0`: Happy
*   `1`: Sad
*   `2`: Angry
*   `3`: Surprised
*   `4`: Neutral
*   `5`: Disgust
*   `6`: Fear

### 2.2 Acoustic Feature Definitions
*   **MFCC (Mel-Frequency Cepstral Coefficients):** n_mfcc = 40. Captures spectral envelope characteristics.
*   **Tonnetz (Tonal Centroid Features):** 6 dimensions. Captures harmonic relations, pitch class profiles, and chordal movement.
*   **Combined Dimensionality:** Feature vector V in R^46.
*   **Normalization:** L1 Norm applied row-wise.

---

## 3. PROMPT DIRECTIVE FOR AI IMPLEMENTATION

When using this specification, the AI must implement the following **8 standalone modules** without skipping boilerplate code, error handlers, or configuration blocks.

---

### MODULE 1: Data Preprocessing & Validation Pipeline (`dataset_pipeline.py`)

**Objective:** Extract features safely without memory crashes or data leakage.
*   **Requirements:**
    1. Implement global random seeding across `os`, `random`, `numpy`, and `tensorflow`.
    2. Convert all incoming `.wav` files into mono format and resample to 16,000 Hz.
    3. Implement structured `try-except` wrappers around `soundfile` and `librosa` readers to quarantine corrupted files into an error log (`corrupted_files.log`).
    4. Implement dynamic batch extraction to process datasets exceeding available RAM.
    5. **Zero Data Leakage Rule:** Features must be split via `train_test_split(..., test_size=0.2, stratify=y, random_state=42)` **before** applying `sklearn.preprocessing.normalize`.
    6. Export preprocessed feature sets to disk using compressed NumPy format (`np.savez_compressed`).

---

### MODULE 2: Deep Learning Architecture & Training Engine (`train_engine.py`)

**Objective:** Train and validate the high-accuracy 1D Convolutional Neural Network (`CascadeCovM1`).
*   **Architecture Specification:**
    1. **Input Layer:** `(46, 1)` representing 46 audio features with 1 channel.
    2. **Block 1:** `Conv1D(180, kernel_size=3, padding='same', activation='relu')` -> `MaxPooling1D(pool_size=2)` -> `Dropout(0.2)`.
    3. **Block 2:** `Conv1D(180, kernel_size=3, padding='same', activation='relu')` -> `MaxPooling1D(pool_size=2)` -> `Dropout(0.2)`.
    4. **Block 3:** `Conv1D(360, kernel_size=3, padding='same', activation='relu')` -> `MaxPooling1D(pool_size=2)` -> `Dropout(0.2)`.
    5. **Classification Head:** `Flatten()` -> `Dense(720, activation='relu')` -> `Dropout(0.3)` -> `Dense(360, activation='relu')` -> `Dropout(0.3)` -> `Dense(180, activation='relu')` -> `Dropout(0.3)` -> `Dense(90, activation='relu')` -> `Dense(7, activation='softmax')`.
*   **Compilation & Optimization:**
    *   Optimizer: `Adam(learning_rate=0.0001)`
    *   Loss: `SparseCategoricalCrossentropy()`
    *   Callbacks:
        *   `EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)`
        *   `ModelCheckpoint(filepath='best_model_{val_accuracy:.4f}.h5', save_best_only=True)`
        *   `TensorBoard(log_dir='./logs/fit')`
        *   `ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)`

---

### MODULE 3: Production Inference Engine (`inference_engine.py`)

**Objective:** Stateless, thread-safe class for transforming raw audio into structured predictions.
*   **Requirements:**
    1. Thread-safe singleton pattern for loading the compiled Keras model.
    2. Support raw byte-stream inputs, temporary file paths, and base64 encoded audio strings.
    3. Automatic silence trimming using `librosa.effects.trim(top_db=25)`.
    4. Feature vector output shape strictly matching `(1, 46, 1)`.
    5. Structured return dictionary containing:
        *   `predicted_class`: String name of the winning emotion.
        *   `class_index`: Integer ID (0-6).
        *   `confidence_score`: Float value between 0.0000 and 1.0000.
        *   `probability_distribution`: Dictionary mapping every class name to its exact probability.
        *   `inference_latency_ms`: Float execution duration in milliseconds.

---

### MODULE 4: Enterprise REST API Service (`server.py`)

**Objective:** High-throughput, asynchronous FastAPI backend.
*   **Endpoints:**
    1. `GET /health`: Returns JSON with server status, GPU/CPU availability, and model version.
    2. `POST /api/v1/predict`: Accepts `multipart/form-data` audio file (`.wav`, `.mp3`, `.ogg`, `.flac`).
    3. `POST /api/v1/predict/batch`: Accepts multiple audio files (maximum 20 per request).
*   **Middleware & Security:**
    *   `CORSMiddleware`: Strict origin whitelisting.
    *   File validation: Maximum payload size enforced (15 MB); MIME-type checks for audio headers.
    *   Disk Cleanup: All temporary files stored in `/tmp` must be safely unlinked in a `finally` execution block to prevent storage exhaustion.
    *   Structured Exception Handlers: Standardized error responses (`400 Bad Request`, `415 Unsupported Media Type`, `500 Internal Error`).

---

### MODULE 5: Single-Page Diagnostic Dashboard (`static/index.html`, `static/app.js`, `static/styles.css`)

**Objective:** Clean, dependency-free UI for audio verification, file ingestion, and visualization.
*   **UI Features:**
    1. **Live Microphone Recorder:** Uses Web Audio API (`MediaRecorder`) to capture voice, visualize live waveforms on HTML5 Canvas, and send clean 16kHz WAV blobs directly to `/api/v1/predict`.
    2. **Drag-and-Drop Uploader:** Accepts file drops with instantaneous audio player preview.
    3. **Dynamic Results Visualizer:**
        *   Large badge displaying the dominant predicted emotion with color indicators (e.g., Green for Happy, Red for Angry, Gray for Neutral).
        *   Horizontal animated SVG or CSS progress bars displaying the 0-100% confidence distribution across all 7 classes.
        *   Latency metric tag (e.g., `⚡ Inference Time: 42ms`).

---

### MODULE 6: Automated Test Suite (`tests/test_system.py`)

**Objective:** Complete `pytest` coverage across all pipeline nodes.
*   **Test Cases:**
    1. `test_feature_extraction_shape`: Validates that synthetic audio yields a vector of shape `(46,)`.
    2. `test_corrupted_audio_handling`: Asserts that empty or broken audio buffers fail gracefully without throwing uncaught exceptions.
    3. `test_model_inference_bounds`: Verifies that output probabilities sum to 1.0.
    4. `test_api_predict_endpoint`: Tests `/api/v1/predict` using `httpx.AsyncClient` with mock `.wav` payloads.
    5. `test_unsupported_file_rejection`: Confirms that uploading a `.txt` or `.png` returns an HTTP 415 error code.

---

### MODULE 7: Production Deployment & Process Management (`ecosystem.config.js` & `deploy.sh`)

**Objective:** Shell automation and process configuration for Ubuntu environments.

#### 1. PM2 Configuration (`ecosystem.config.js`)
module.exports = {
  apps: [{
    name: "ser-api-service",
    script: "venv/bin/uvicorn",
    args: "server:app --host 127.0.0.1 --port 8000 --workers 4",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: "2G",
    env: {
      NODE_ENV: "production",
      PYTHONUNBUFFERED: "1"
    },
    error_file: "./logs/pm2-err.log",
    out_file: "./logs/pm2-out.log",
    time: true
  }]
};

#### 2. Apache VirtualHost Reverse Proxy (`/etc/apache2/sites-available/ser-api.conf`)
<VirtualHost *:80>
    ServerName ser.yourdomain.com
    ServerAdmin webmaster@localhost

    # Global proxy settings
    ProxyPreserveHost On
    ProxyRequests Off

    # Route backend API traffic to Uvicorn
    ProxyPass /api http://127.0.0.1:8000/api
    ProxyPassReverse /api http://127.0.0.1:8000/api

    ProxyPass /health http://127.0.0.1:8000/health
    ProxyPassReverse /health http://127.0.0.1:8000/health

    # Route frontend static interface
    DocumentRoot /var/www/ser-frontend
    <Directory /var/www/ser-frontend>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/ser_api_error.log
    CustomLog ${APACHE_LOG_DIR}/ser_api_access.log combined
</VirtualHost>

#### 3. Setup & Deployment Shell Script (`deploy.sh`)
#!/bin/bash
set -e

echo "[+] Updating system packages..."
sudo apt-get update -y && sudo apt-get install -y ffmpeg libsndfile1 apache2 nodejs npm

echo "[+] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install tensorflow keras librosa soundfile fastapi uvicorn pydantic scikit-learn httpx pytest

echo "[+] Installing and starting PM2 service..."
sudo npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "[+] Configuring Apache reverse proxy..."
sudo a2enmod proxy proxy_http headers rewrite
sudo a2ensite ser-api.conf
sudo apache2ctl configtest
sudo systemctl restart apache2

echo "[+] Deployment complete! Service active on port 80/8000."
"""

# Write the string to a local Markdown file
with open('target.md', 'w', encoding='utf-8') as f:
    f.write(markdown_content)

# Trigger the browser download
files.download('target.md')
