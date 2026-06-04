# Raspberry Pi install

Copy or clone this project on the Raspberry Pi, then run:

```bash
cd /home/pi/vibecoding-pi-signal
sh pi/install_service.sh
```

Useful overrides:

```bash
BRIGHTNESS=24 LED_COUNT=8 LED_PIN=18 PORT=8765 sh pi/install_service.sh
```

The current ring uses the legacy `neopixel` wrapper from:

```text
/home/pi/Desktop/HR-SLPTIME
/home/pi/rpi_ws281x/python
```

If your Pi uses a different library path, set `PYTHONPATH_EXTRA` when installing.

Check the service:

```bash
sudo systemctl status vibecoding-signal-ring.service --no-pager
curl http://127.0.0.1:8765/health
```
