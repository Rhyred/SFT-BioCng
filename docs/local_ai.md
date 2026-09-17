# NICEGAS Local AI Foundation (Docker Model Runner)

Dokumentasi fondasi Local AI untuk project **NICEGAS (Bio-CNG SCADA & Monitoring System)** menggunakan **Docker Model Runner (DMR)** sebagai primary local development runtime.

---

## 1. Architecture

```
+-----------------------------------------------------------------------------------+
| Host Machine (Windows 11 / WSL2 Backend)                                          |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Docker Desktop Runtime                                                      |  |
|  |                                                                             |  |
|  |   [ nicegas-postgres ]        [ nicegas-mqtt ]                              |  |
|  |   (Port 5432)                 (Port 1883)                                   |  |
|  |             \                      /                                        |  |
|  |              \                    /                                         |  |
|  |            [ nicegas-backend (FastAPI) ]                                    |  |
|  |            (Port 8000)                                                      |  |
|  |                 |                                                           |  |
|  |                 | HTTP Request (model-runner.docker.internal / host IP)     |  |
|  |                 v                                                           |  |
|  |   +-----------------------------------------------------------------------+ |  |
|  |   | Docker Model Runner (DMR) Service                                     | |  |
|  |   | Engine: llama.cpp backend                                             | |  |
|  |   | Host TCP Port: 12434                                                  | |  |
|  |   | OpenAI-compatible API: /v1/chat/completions                           | |  |
|  |   |                                                                       | |  |
|  |   | Active Model:                                                         | |  |
|  |   | huggingface.co/huggingfacetb/smollm2-1.7b-instruct-gguf:latest        | |  |
|  |   +-----------------------------------------------------------------------+ |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                  ^
                                  | Future API Endpoint (/api/v1/ai/...)
                     +--------------------------+
                     | Flutter Mobile / Desktop |
                     +--------------------------+
```

### Key Routing Contracts
- **Host → DMR**: `http://localhost:12434/v1`
- **Docker Container (FastAPI) → DMR**: `http://model-runner.docker.internal/v1` (atau `http://host.docker.internal:12434/v1`)
- **Flutter Client → Backend**: `http://<HOST_IP>:8000/api/v1/...` (Flutter **TIDAK** mengakses DMR secara langsung).

---

## 2. Requirements

- **OS**: Windows 11 Pro 64-bit (atau Linux dengan Docker Engine)
- **Docker Desktop**: Version 4.88.1+ (Engine v29.7.2+)
- **WSL2**: Linux Kernel 6.18+
- **CPU**: Minimal 4 Cores (Diverifikasi pada Intel Core i7-12700K 12 Cores / 20 Threads)
- **RAM**: Minimal 8 GB RAM (Diverifikasi pada 32 GB RAM, penggunaan DMR model ~1.29 GB)
- **Storage**: Free space minimal 5 GB untuk runtime & model weights (Diverifikasi pada NVMe SSD)

---

## 3. How to Enable Docker Model Runner (DMR)

Docker Model Runner diaktifkan melalui CLI Docker Desktop atau GUI Settings.

### CLI Command
```powershell
# Aktifkan DMR dengan bind port TCP 12434
docker desktop enable model-runner --tcp=12434

# Instal backend engine (llama.cpp)
docker model install-runner --backend llama.cpp
```

### GUI Settings (Alternatif)
1. Buka **Docker Desktop**.
2. Masuk ke menu **Settings** (`Gear icon`) → **AI**.
3. Centang **Enable Docker Model Runner**.
4. Set port HTTP ke `12434`.

---

## 4. How to Verify DMR

Jalankan perintah berikut pada terminal host:

```powershell
# Cek status runner
docker model status

# Cek versi client & server
docker model version

# Cek endpoint HTTP
curl.exe -s http://localhost:12434/v1/models
```

Output yang diharapkan:
- Status: `Docker Model Runner is running`
- Backend: `llama.cpp Running`
- Models HTTP: Return JSON list `{"object":"list","data":[...]}`

---

## 5. Model Chosen

| Properti | Nilai Aktual |
|---|---|
| **Model Name** | `huggingface.co/huggingfacetb/smollm2-1.7b-instruct-gguf:latest` |
| **Source** | HuggingFace (`hf.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF`) |
| **Parameter Size** | `1.71B` parameters |
| **Quantization** | `MOSTLY_Q4_K_M` |
| **Format** | `GGUF` (Llama architecture) |
| **Disk Size** | `1.05 GB` |
| **Context Window** | `8,192 tokens` |
| **Alasan Pemilihan** | Sangat ringan (1.05 GB disk, ~1.29 GB RAM), throughput sangat tinggi (>280 tok/s), responsif untuk bio-cng telemetry & fault analysis, serta arsitektur GGUF yang identik dan 100% kompatibel untuk di-porting ke `llama.cpp` di Android / Termux. |

---

## 6. Model Resource Requirements

- **VRAM / RAM Footprint**: ~1.29 GB Working Set RAM
- **Cold Start Latency**: ~3.75s – 5.90s (Inisialisasi llama-server)
- **Warm Latency**: ~0.24s (Sub-second response)
- **Inference Speed**: ~280 – 328 tokens/sec (Warm request)

---

## 7. API Endpoints

Docker Model Runner mengekspos REST API standar OpenAI-compatible:

| Endpoint | Method | Fungsi |
|---|---|---|
| `/v1/models` | `GET` | Menampilkan daftar model lokal yang tersedia |
| `/v1/chat/completions` | `POST` | Generate respons chat (mendukung non-streaming & streaming SSE) |

---

## 8. Host Access Example

### Direct HTTP Request (cURL)
```powershell
curl.exe -X POST http://localhost:12434/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{"model": "huggingface.co/huggingfacetb/smollm2-1.7b-instruct-gguf:latest", "messages": [{"role": "user", "content": "Reply exactly: NICEGAS AI ONLINE"}], "temperature": 0.0}'
```

### Python (OpenAI SDK)
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:12434/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="huggingface.co/huggingfacetb/smollm2-1.7b-instruct-gguf:latest",
    messages=[
        {"role": "system", "content": "You are NICEGAS local AI."},
        {"role": "user", "content": "Reply exactly: NICEGAS LOCAL AI READY"}
    ],
    temperature=0.0
)

print(response.choices[0].message.content)
```

---

## 9. Container Access Example (FastAPI Backend)

Dari dalam container backend NICEGAS (`nicegas-backend`), akses DMR menggunakan DNS built-in Docker Desktop:

- **Base URL**: `http://model-runner.docker.internal/v1` (atau `http://host.docker.internal:12434/v1`)

```python
import os
from openai import OpenAI

AI_BASE_URL = os.getenv("AI_BASE_URL", "http://model-runner.docker.internal/v1")
AI_MODEL = os.getenv("AI_MODEL", "huggingface.co/huggingfacetb/smollm2-1.7b-instruct-gguf:latest")

client = OpenAI(
    base_url=AI_BASE_URL,
    api_key="not-needed"
)

def analyze_sensor_telemetry(prompt: str) -> str:
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "You are an industrial telemetry monitoring AI for Bio-CNG plants."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content
```

---

## 10. Test Commands

```powershell
# 1. Pull model
docker model pull hf.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF

# 2. List model lokal
docker model list

# 3. Jalankan automated test suite
python scratch/test_dmr.py

# 4. Jalankan failure test suite
python scratch/test_failures.py

# 5. Cek konektivitas dari container backend
docker exec nicegas-backend python -c "import urllib.request; print(urllib.request.urlopen('http://model-runner.docker.internal/v1/models').read().decode())"
```

---

## 11. Troubleshooting

1. **Backend `llama.cpp` Not Running / Error**:
   - Jalankan: `docker model reinstall-runner --backend llama.cpp`
   - Pastikan Docker Desktop tidak mengalami resource lock.
2. **Port 12434 Conflict**:
   - Jika port 12434 digunakan service lain, ganti konfigurasi via `docker desktop enable model-runner --tcp=<PORT_BARU>`.
3. **Container Cannot Resolve `model-runner.docker.internal`**:
   - Gunakan fallback `http://host.docker.internal:12434/v1`.

---

## 12. Performance Baseline

- **Cold Start (Model initial load)**: 3.75s – 5.90s
- **Warm Request Latency**: 0.24s – 0.25s
- **Time To First Token (TTFT)**: 0.03s – 0.04s
- **Peak Throughput**: ~280 – 328 tokens/sec
- **Process Memory Footprint**: ~1.29 GB RAM (`com.docker.llama-server.exe`)
- **Host CPU Impact**: < 5% saat warm inference

---

## 13. Future Android Migration Plan

Untuk transisi ke standalone Android runtime (Edge AI / On-Device SCADA):

```
+------------------------------------------------------------+
| Android Device                                             |
|                                                            |
|  +------------------------------------------------------+  |
|  | Termux / Native Android App                          |  |
|  |  └── llama-server (llama.cpp ARM64 compilation)      |  |
|  |        - Model: SmolLM2-1.7B-Instruct-Q4_K_M.gguf    |  |
|  |        - Port: localhost:8080 (OpenAI-compatible)    |  |
|  +------------------------------------------------------+  |
|                            ^                               |
|                            | http://127.0.0.1:8080/v1      |
|  +------------------------------------------------------+  |
|  | NICEGAS Flutter App / Local Service                  |  |
|  |  └── Uses same OpenAI-compatible API contracts       |  |
|  +------------------------------------------------------+  |
+------------------------------------------------------------+
```

Karena model yang digunakan berformat standard **GGUF (Q4_K_M)**, bobot model yang sama dapat langsung disalin ke Android dan dijalankan via `llama.cpp` / `llama-server` tanpa konversi ulang bobot.
