# Troubleshooting

No hook activity:

```bash
tail -f ~/.vibecoding-pi-signal/hook.log
```

Mac cannot reach Pi:

```bash
curl http://192.168.31.131:8765/health
```

Pi moved to a new IP:

```bash
curl http://NEW_IP:8765/health
~/.local/bin/ai-signal manual configure --configure --host NEW_IP --port 8765
~/.local/bin/ai-signal manual clear --clear
```

You can also open the web console to test states and tune idle brightness:

```bash
open http://NEW_IP:8765/
```

Reset stuck sessions:

```bash
~/.local/bin/ai-signal manual clear --clear
```

This clears the Mac-side session store and returns the ring to `idle`.  To turn
the LEDs off explicitly, send `off` as a state:

```bash
~/.local/bin/ai-signal manual off --state off --session manual-off
```

The terminal hangs when testing hooks manually:

Use the current `mac/agent_hook.py`; it only reads stdin when data is present.

Duplicate `Stop` entries:

Remove the older notify wrapper after TOML hooks are working:

```bash
python3 mac/remove_legacy_notify.py
```

Make lights softer:

Reinstall the Pi service with a lower brightness:

```bash
BRIGHTNESS=12 sh pi/install_service.sh
```
