"""
ears/networking/tailscale_config.py — Auto-detects Tailscale and Wi-Fi IP addresses
to configure mobile-to-PC ingestion over local networks or global 4G/5G VPNs.
"""
import socket
import subprocess
from typing import Optional, Dict, List


def get_local_wifi_ip() -> Optional[str]:
    """Discover the primary local Wi-Fi / LAN IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually connect, just inspects routing table for default outbound interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and not ip.startswith("100."):
            return ip
    except Exception:
        pass
    return None


def get_tailscale_ip() -> Optional[str]:
    """Discover the Tailscale mesh VPN IPv4 address (100.64.0.0/10 range)."""
    # Try via tailscale CLI first if available
    try:
        out = subprocess.check_output(
            ["tailscale", "ip", "-4"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        ip = out.strip()
        if ip and ip.startswith("100."):
            return ip
    except Exception:
        pass

    # Fallback: check host network interfaces via socket/getaddrinfo
    try:
        hostname = socket.gethostname()
        for addr_info in socket.getaddrinfo(hostname, None):
            ip = addr_info[4][0]
            if ip.startswith("100.") and "." in ip:
                # Check basic Tailscale CGNAT prefix (100.64.0.0 to 100.127.255.255)
                parts = [int(p) for p in ip.split(".")]
                if len(parts) == 4 and parts[0] == 100 and 64 <= parts[1] <= 127:
                    return ip
    except Exception:
        pass
    return None


def get_available_endpoints(port: int = 8787) -> Dict[str, Optional[str]]:
    """Return a dictionary of all available ingest endpoints for the Android companion app."""
    local_ip = get_local_wifi_ip()
    ts_ip = get_tailscale_ip()
    
    return {
        "local_wifi": f"http://{local_ip}:{port}/ingest" if local_ip else None,
        "tailscale_global": f"http://{ts_ip}:{port}/ingest" if ts_ip else None,
        "localhost": f"http://127.0.0.1:{port}/ingest"
    }


def print_mobile_setup_guide(port: int = 8787) -> str:
    """Generate a formatted setup guide for configuring ForegroundMicService.kt."""
    endpoints = get_available_endpoints(port)
    guide = [
        "=" * 60,
        "EARS MOBILE COMPANION SETUP ENDPOINTS",
        "=" * 60,
        "",
        "Copy and paste one of the following into `ForegroundMicService.kt` (line 46):",
        ""
    ]
    
    if endpoints["tailscale_global"]:
        guide.extend([
            "[RECOMMENDED - Global 4G/5G Sync via Mesh VPN]:",
            f'    private val backendUrl = "{endpoints["tailscale_global"]}"',
            ""
        ])
    else:
        guide.extend([
            "[Tailscale Not Detected] - Install Tailscale on PC & Mobile for global 4G/5G sync.",
            ""
        ])
        
    if endpoints["local_wifi"]:
        guide.extend([
            "[Home Wi-Fi Sync Only]:",
            f'    private val backendUrl = "{endpoints["local_wifi"]}"',
            ""
        ])
        
    guide.extend([
        "[Local Emulator / USB Tethering]:",
        f'    private val backendUrl = "{endpoints["localhost"]}"',
        "=" * 60
    ])
    return "\n".join(guide)


if __name__ == "__main__":
    print(print_mobile_setup_guide())
