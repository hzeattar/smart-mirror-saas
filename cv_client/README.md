# Smart Mirror Computer Vision Client

The client runs locally beside a standard webcam. It pairs with the Laravel API, fetches the tenant catalog, tracks MediaPipe pose and hand landmarks, recommends the nearest product size, perspective-warps the garment to the shoulder/hip geometry, preserves visible forearms, and exposes touch, keyboard and gesture controls inside the mirror window.

## Setup

```bash
cd cv_client
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python download_model.py
```

Pair and start:

```bash
python main.py --api-url https://YOUR-RAILWAY-DOMAIN --pairing-code DEMO2026 --device-name "Main Store Mirror"
```

After the first successful pairing, the device token is stored under `.smart-mirror/mirror.token`. Future runs only need:

```bash
python main.py --api-url https://YOUR-RAILWAY-DOMAIN
```

Hybrid kiosk mode:

```powershell
cv_client\run_kiosk.ps1
```

Equivalent direct command:

```bash
python main.py --api-url https://YOUR-RAILWAY-DOMAIN --camera 0 --camera-backend dshow --ai-tryon --experience hybrid --hybrid-auto-start --kiosk-health-hud
```

Local texture mode:

```bash
python main.py --texture ./assets/sample_garment.png --reference-shoulder-cm 44
```

## Phase 1 gesture controls

- Open-palm swipe left: next garment.
- Open-palm swipe right: previous garment.
- Hold thumbs-up: save the rendered frame and product metadata.
- Hold thumb/index pinch: switch automatic size recommendation on or off.
- Hold two fingers: move to the next manual size.
- Hold open palm without moving: show on-screen controls.
- Hold a fist: hide on-screen controls.

Every gesture has a hold threshold, movement threshold and cooldown to reduce accidental commands. A progress bar in the top-right panel shows when a hold gesture is about to trigger.

## Hybrid kiosk gestures

- Hold open palm: start the countdown/capture flow.
- Open-palm swipe left/right: move through the outfit gallery.
- Hold thumbs-up: show the QR code for the current result.
- Hold a fist: close the gallery and return to the attractor.

Hybrid mode can also auto-start after a centred person is visible for 1.5 seconds. Use `--no-hybrid-auto-start` to require manual open-palm start.

Snapshots are saved by default under:

```text
cv_client/.smart-mirror/snapshots/
```

Each capture creates a high-quality JPEG and a JSON file containing product, price, selected size, fit confidence and capture time. Press `S` as a keyboard fallback.

Useful tuning flags:

```bash
python main.py \
  --api-url https://YOUR-RAILWAY-DOMAIN \
  --gesture-cooldown 1.1 \
  --gesture-hold 0.75 \
  --swipe-distance 0.20 \
  --gesture-debug
```

Use `--no-gestures` to disable hand tracking on low-power devices.

## Keyboard and touch fallback

- Click/touch the visible left and right arrows, or press `[` / `]`, to change garments.
- Click/touch `-` / `+`, or press the same keys, to override the selected size.
- `A`: switch automatic size recommendation on or off.
- `C`: capture calibration while standing exactly 2 metres from the camera.
- `R`: reset pose smoothing.
- `F`: toggle full-screen mirror mode.
- `S`: save a snapshot.
- `Q` or `Esc`: exit.

The mirror HUD displays the product name, price, selected/recommended size, calibration state, gesture state and fit confidence. Physical measurements are estimates for product-size guidance, not tailoring-grade body measurements.

Calibration is camera-specific. Repeat it whenever the camera position, focal length, zoom or resolution changes. Set `--reference-shoulder-cm` to the measured shoulder width used during calibration for better size recommendations.
