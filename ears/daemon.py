"""
ears/daemon.py — Entry point for the Ambient Sensory Memory Module backend.

Run this on the machine that also runs Persona N (C:\\era):

    python -m ears.daemon

The phone companion app posts diarized transcript batches to your local Wi-Fi
or Tailscale mesh VPN IP as they become available.
"""
import uvicorn
from ears.networking.tailscale_config import print_mobile_setup_guide

if __name__ == "__main__":
    print(print_mobile_setup_guide(port=8787))
    uvicorn.run("ears.capture.android_bridge:app", host="0.0.0.0", port=8787, reload=False)
