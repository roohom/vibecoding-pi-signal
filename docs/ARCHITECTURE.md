# Architecture

The project is split into three layers.

```text
Agent hooks on Mac -> session runtime -> HTTP state protocol -> Pi renderer
```

## Mac side

`vibecoding_pi_signal.hooks.cli` adapts agent lifecycle events into normalized
states. `SignalRuntime` stores per-session state locally and aggregates all
active sessions by priority before sending one final state to the Pi.

This keeps multiple Codex windows from fighting the hardware directly.

## Protocol

The Pi only receives state updates:

```http
POST /signal
Content-Type: application/json

{"state":"working","source":"codex:PreToolUse","session":"codex:abc","text":"Bash"}
```

Keeping the protocol small is what makes the display replaceable.

## Pi side

`vibecoding_pi_signal.server` owns the animation thread and exposes the HTTP
server. The current renderer is `SignalRing`, which controls an 8-pixel WS2812
ring through the legacy `neopixel` wrapper.

To support a dot-matrix display or LCD later, keep the HTTP/server layer and
replace the renderer object with one that implements:

```python
fill(pixel_color)
set_pixels(colors)
off()
count()
```

For richer screens, keep the same state protocol and render each state as a UI
view instead of individual pixels.
