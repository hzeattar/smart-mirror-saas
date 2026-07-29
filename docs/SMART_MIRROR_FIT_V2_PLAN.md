# Smart Mirror Fit Engine v2

## Goal
Turn the current static PNG prototype into a production-oriented 2D AR fitting experience that recommends a size, deforms the garment to the torso, follows movement, and exposes in-mirror controls and product information.

## Phase A — Body and fitting model
- Track shoulders, hips, elbows, wrists, nose and ears.
- Derive shoulder width, hip width, torso height, torso angle and body centre.
- Smooth the complete pose geometry instead of only shoulder width.
- Estimate physical shoulder, chest and torso measurements after 2 m calibration.
- Recommend the nearest available size with an explainable fit score.

## Phase B — Garment deformation
- Replace uniform resize with a four-corner perspective warp between shoulder and hip anchors.
- Respect configurable garment anchor margins.
- Rotate and deform the garment with the torso.
- Add optional arm occlusion masks so forearms can appear in front of the garment.
- Keep the overlay stable when confidence briefly drops.

## Phase C — Mirror controls and merchandising
- Product name, formatted price, selected/recommended size and confidence.
- Previous/next controls by keyboard and clickable on-screen arrows.
- Size override controls and automatic-size toggle.
- Full-screen toggle, calibration guidance and connection status.
- Optional hand-raise gesture navigation with debounce.

## Phase D — Product data
- Garment type and fit profile.
- Shoulder, chest, waist, hip, torso height and sleeve length per size.
- Per-product texture anchor margins.
- Real front-facing transparent garment assets.

## Phase E — Validation
- Unit tests for size recommendation, geometry smoothing and perspective targets.
- Standalone local texture mode remains supported.
- Backward-compatible catalog handling for products that only have the original three measurements.
