# Troubleshooting

No hook activity:

```bash
tail -f ~/.vibecoding-pi-signal/hook.log
```

Mac cannot reach Pi:

```bash
curl http://192.168.31.131:8765/health
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
