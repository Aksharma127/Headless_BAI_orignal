# BAI Cloud And Device Runbook

This runbook turns the local Fedora prototype into something you can run from
another device and deploy to a small student-cloud VM.

## 1. Run From Another Device On Your Wi-Fi

From the project folder:

```bash
cd bai-final-year
./scripts/run_lan_demo.sh
```

Open the printed URL from your phone/laptop on the same Wi-Fi:

```text
http://YOUR_PC_IP:5000/demo-website/index.html
```

Why this works:

- `sensor.js` now sends telemetry to `http://YOUR_PC_IP:8000/api/sync`
  instead of hardcoded `127.0.0.1`.
- The backend binds to `0.0.0.0`.
- `MIN_DESKTOP_VIEWPORT_WIDTH` defaults to `0`, so phone/tablet traffic is not
  silently dropped.

If Fedora firewall blocks the ports:

```bash
sudo firewall-cmd --add-port=5000/tcp --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

## 2. Package Your Custom Chromium Runtime

Do this before building the cloud image:

```bash
./scripts/package_custom_chromium.sh
```

By default, it copies from:

```text
../chromium-main/src/out/Default
```

into:

```text
runtime/chromium
```

This copies `chrome`, Chromium's local `.so` files, ICU data, `.pak` resources,
and locales. Do not copy only the 169 MB `chrome` file; this build depends on
nearby shared libraries.

## 3. Build The Cloud Container

The custom cloud image uses Fedora to avoid Ubuntu/Fedora glibc friction and
installs font/rendering dependencies explicitly.

```bash
docker compose -f docker-compose.cloud.yml build
```

Run locally:

```bash
docker compose -f docker-compose.cloud.yml up
```

Health check:

```bash
curl http://localhost:8000/health
```

## 4. Deploy On A Student Cloud VM

Use a plain Linux VM first, not serverless. A 4 GB RAM VM is the practical floor
for this custom Chromium path; 2 GB can work only with very low traffic.

Recommended path: build the Docker image on the Fedora machine that already has
the custom Chromium build, then push it to a registry and pull it on the VM.
That avoids recompiling Chromium in the cloud.

Local Fedora machine:

```bash
./scripts/package_custom_chromium.sh
docker compose -f docker-compose.cloud.yml build
docker tag bai-final-year-backend ghcr.io/YOUR_GITHUB_USER/bai-backend:latest
docker push ghcr.io/YOUR_GITHUB_USER/bai-backend:latest
```

If you do not have Docker locally, copy the packaged runtime to the VM after
cloning the repo:

```bash
rsync -av runtime/chromium/ USER@SERVER_IP:~/Headless_BAI/bai-final-year/runtime/chromium/
```

Steps on the VM after the image or runtime exists:

```bash
git clone YOUR_REPO_URL
cd Headless_BAI/bai-final-year
cp .env.example .env
```

Edit `.env` with Supabase keys and production CORS origins.

Build and run:

```bash
docker compose -f docker-compose.cloud.yml up -d --build
```

If you pushed the image to GHCR, use the image-only compose file instead:

```bash
docker compose -f docker-compose.cloud.image.yml up -d
```

Open:

```text
http://SERVER_IP:8000/health
```

## 5. How The Four Cloud Bottlenecks Are Handled

Custom binary trap:

- `docker/Dockerfile.custom-chromium` uses Fedora and installs raw Chromium
  display/font dependencies.
- `runtime/chromium` keeps the custom binary and adjacent runtime files
  together.

OOM killer:

- `get_skeleton()` uses a Redis lock named `bai:chromium_extractor_lock`.
- Even if multiple API workers receive traffic, only one headless extraction
  runs at a time.
- `docker-compose.cloud.yml` runs `uvicorn --workers 1` for the MVP.

Ephemeral filesystem:

- Backend extraction no longer reads `/tmp/bai_skeleton.txt`.
- Native Chromium output is captured via `subprocess.PIPE`.
- Skeletons are immediately stored in Redis as `skeleton:{url_hash}`.

Fontconfig/headless rendering:

- The custom Dockerfile installs Liberation/Noto fonts.
- `XDG_CACHE_HOME=/tmp/bai-font-cache` gives Fontconfig a writable cache.
- `fc-cache -f -v` runs at image build time.

## 6. Important Environment Variables

```bash
BAI_CHROME_BINARY=/opt/bai/chromium/chrome
BAI_USE_NATIVE_CHROME=auto
BAI_CHROME_TIMEOUT_SECONDS=25
SKELETON_CACHE_TTL_SECONDS=86400
EXTRACTOR_LOCK_WAIT_SECONDS=90
EXTRACTOR_LOCK_TTL_SECONDS=120
REDIS_HOST=redis
REDIS_PORT=6379
```

Use `BAI_USE_NATIVE_CHROME=false` only if you intentionally want the Playwright
DOM fallback.
