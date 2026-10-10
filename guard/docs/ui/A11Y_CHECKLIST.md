# CareSentry-AI Guard Console — Accessibility (a11y) Verification Checklist (U-08)

This document verifies compliance with **WCAG 2.1 AA** standards for the CareSentry Guard Console web application.

---

## 1. Multi-Attribute State Representation (Never Color Alone)

To ensure users with color vision deficiencies can immediately distinguish clinical safety end states without ambiguity, all verdict cards implement three distinct sensory channels:

| Verdict State | Icon (Channel 1) | Word Title (Channel 2) | Border Style (Channel 3) | Contrast Ratio |
| :--- | :--- | :--- | :--- | :---: |
| **VERIFIED** | Checkmark (`check.svg`) | `VERIFIED` | Solid 2px stroke (`#3fb950`) | > 5.5:1 |
| **ANNOTATED** | Triangle Warning (`alert.svg`) | `ANNOTATED` | Dashed 2px stroke (`#e3b341`) | > 6.2:1 |
| **WITHHELD** | Stop Circle (`stop.svg`) | `WITHHELD — Not shown for your safety` | Solid 3px bold stroke (`#f85149`) | > 7.1:1 |
| **ABSTAIN** | Question Circle (`help.svg`) | `COULD NOT VERIFY` | Dotted 2px stroke (`#8b949e`) | > 4.8:1 |

---

## 2. ARIA Live Regions & Screen Reader Semantics

- **Status Announcements (`role="status"`, `aria-live="polite"`):**
  - Gateway connectivity badge announces connection changes.
  - Normal verdict cards (`VERIFIED`, `ANNOTATED`, `ABSTAIN`) announce completion without interrupting speech.
- **Urgent Safety Alerts (`role="alert"`):**
  - Any `WITHHELD` verdict card immediately emits an assertive alert to notify screen readers of critical medication or allergy conflicts.
- **Concealed Output (`aria-expanded`, `aria-hidden`):**
  - Unverified text for `WITHHELD` decisions is hidden by default with `aria-hidden="true"`.
  - The reveal button explicitly announces its state via `aria-expanded="false"`, switching to `"true"` only after explicit user interaction.

---

## 3. Keyboard Navigation Walkthrough

All interactive elements are fully operable using standard keyboard controls:

| Key Sequence | Action | Target Element | Focus Indicator |
| :--- | :--- | :--- | :--- |
| `Tab` | Top-to-bottom logical traversal | Nav tabs $\rightarrow$ Record inputs $\rightarrow$ Buttons | High-visibility 3px blue focus ring (`#58a6ff`) |
| `Shift + Tab` | Reverse traversal | Previous interactive control | High-visibility 3px blue focus ring |
| `Enter` | Activate button or send question | `#sendBtn`, `#demoBtn`, `#runCheckBtn` | Immediate visual pressed state |
| `Space` | Toggle tabs / reveal controls | `.reveal-unverified-btn`, `.tab-btn` | Button state update |
| `Arrow Keys` | Tablist switching | `nav-tabs` (`[role="tab"]`) | Focus indicator moves across tabs |

---

## 4. Zoom & Scalability (200% Zoom Test)

- Root typography uses responsive relative units (`rem`, `px` clamped scale).
- Layout automatically responds and reflows into single-column cards at 200% browser zoom or mobile viewports without horizontal clipping.
- Touch/click targets exceed minimum 44px by 44px dimensions for ease of operation by caregivers and nurses on tablet devices.

---

## 5. Offline & Zero External Dependency Verification

- **Fonts:** System native sans-serif stack (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`). No Google Fonts or Typekit network calls.
- **Icons:** Pure SVG elements bundled locally in `guard/ui/icons/` and inlined into DOM nodes.
- **Zero Third-Party Scripts:** No external CDNs, trackers, analytics, or framework dependencies.
