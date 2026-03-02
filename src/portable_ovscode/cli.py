#!/usr/bin/env python3
"""portable-ovscode: install and run openvscode-server with one command."""

from __future__ import annotations

import argparse
import os
import platform
import secrets
import socket
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

GITHUB_RELEASE_URL = (
    "https://github.com/gitpod-io/openvscode-server/releases/download"
)
LATEST_VERSION = "1.109.5"
PKG_VERSION = "0.3.0"

SUPPORTED_PLATFORMS = {"linux"}
SUPPORTED_ARCHS = {"x86_64", "amd64", "aarch64", "arm64"}


def check_platform() -> None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system not in SUPPORTED_PLATFORMS:
        print(
            f"[portable-ovscode] ERROR: unsupported platform: {system} "
            f"(only Linux is supported)",
            file=sys.stderr,
        )
        sys.exit(1)
    if machine not in SUPPORTED_ARCHS:
        print(
            f"[portable-ovscode] ERROR: unsupported architecture: {machine} "
            f"(supported: x86_64, arm64)",
            file=sys.stderr,
        )
        sys.exit(1)


def detect_arch() -> str:
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    if machine.startswith("arm"):
        return "armhf"
    return "x64"


def download_url(version: str, arch: str) -> str:
    name = f"openvscode-server-v{version}-linux-{arch}"
    return f"{GITHUB_RELEASE_URL}/openvscode-server-v{version}/{name}.tar.gz"


def install(install_dir: str, version: str) -> str:
    """Download and extract openvscode-server. Returns path to binary."""
    install_dir = os.path.expanduser(install_dir)
    arch = detect_arch()
    dirname = f"openvscode-server-v{version}-linux-{arch}"
    binary = os.path.join(install_dir, dirname, "bin", "openvscode-server")

    if os.path.isfile(binary) and os.access(binary, os.X_OK):
        print(f"[portable-ovscode] already installed: {binary}", file=sys.stderr)
        return binary

    url = download_url(version, arch)
    print(f"[portable-ovscode] downloading {url}", file=sys.stderr)

    os.makedirs(install_dir, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = tmp.name
        urllib.request.urlretrieve(url, tmp_path)

    try:
        print(f"[portable-ovscode] extracting to {install_dir}", file=sys.stderr)
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(path=install_dir)
    finally:
        os.unlink(tmp_path)

    if not os.path.isfile(binary):
        print(f"[portable-ovscode] ERROR: binary not found at {binary}", file=sys.stderr)
        sys.exit(1)

    # convenience symlink
    symlink = os.path.join(install_dir, "ovscode")
    try:
        if os.path.islink(symlink) or os.path.exists(symlink):
            os.unlink(symlink)
        os.symlink(binary, symlink)
    except OSError:
        pass

    print(f"[portable-ovscode] installed: {binary}", file=sys.stderr)
    return binary


def generate_self_signed_cert(cert_dir: str, host: str) -> tuple[str, str]:
    """Generate a self-signed certificate. Returns (cert_path, key_path)."""
    cert_path = os.path.join(cert_dir, "cert.pem")
    key_path = os.path.join(cert_dir, "key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"[portable-ovscode] reusing existing cert: {cert_path}", file=sys.stderr)
        return cert_path, key_path

    # Use openssl CLI (available on virtually all Linux systems)
    san = f"IP:{host}" if _is_ip(host) else f"DNS:{host}"
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", key_path, "-out", cert_path,
        "-days", "365", "-nodes",
        "-subj", f"/CN={host}",
        "-addext", f"subjectAltName={san}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        print(
            "[portable-ovscode] ERROR: openssl not found, cannot generate cert",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(
            f"[portable-ovscode] ERROR: cert generation failed: {e.stderr.decode()}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[portable-ovscode] generated self-signed cert: {cert_path}", file=sys.stderr)
    return cert_path, key_path


def _is_ip(host: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return True
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="portable-ovscode",
        description="Install and run openvscode-server with one command.",
        epilog=(
            "Any extra arguments after -- are passed directly to openvscode-server.\n\n"
            "Example:\n"
            "  uvx portable-ovscode --port 8080 --folder ~/project\n"
            "  uvx portable-ovscode --https --port 443\n"
            "  uvx portable-ovscode -- --without-connection-token"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {PKG_VERSION}",
    )
    parser.add_argument(
        "--install-dir",
        default="~/.local/share/openvscode-server",
        help="Directory to install the binary (default: ~/.local/share/openvscode-server)",
    )
    parser.add_argument(
        "--server-version",
        default=LATEST_VERSION,
        help=f"openvscode-server version (default: {LATEST_VERSION})",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Bind port (default: 3000, auto-increments if occupied)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Connection token (default: auto-generated)",
    )
    parser.add_argument(
        "--no-token",
        action="store_true",
        help="Disable connection token (--without-connection-token)",
    )
    parser.add_argument(
        "--folder",
        default=os.getcwd(),
        help="Default folder to open (default: current directory)",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Enable HTTPS with a self-signed certificate",
    )
    parser.add_argument(
        "--cert",
        default=None,
        help="Path to TLS certificate (implies --https)",
    )
    parser.add_argument(
        "--cert-key",
        default=None,
        help="Path to TLS private key (implies --https)",
    )
    parser.add_argument(
        "--install-only",
        action="store_true",
        help="Only install, don't start the server",
    )

    args, extra = parser.parse_known_args()

    check_platform()

    binary = install(args.install_dir, args.server_version)

    if args.install_only:
        print(binary)
        return

    token = args.token or secrets.token_hex(16)
    use_https = args.https or args.cert or args.cert_key

    if args.port is not None:
        port = int(args.port)
    else:
        port = _find_available_port(args.host, 3000)
        if port != 3000:
            print(
                f"[portable-ovscode] port 3000 in use, using {port}",
                file=sys.stderr,
            )

    folder = os.path.abspath(os.path.expanduser(args.folder))

    if use_https:
        # openvscode-server binds to loopback; HTTPS proxy binds to requested host:port
        backend_port = _find_free_port()

        if args.cert and args.cert_key:
            cert_path, key_path = args.cert, args.cert_key
        else:
            cert_dir = os.path.join(
                os.path.expanduser("~/.local/share/openvscode-server"), "certs"
            )
            os.makedirs(cert_dir, exist_ok=True)
            cert_path, key_path = generate_self_signed_cert(cert_dir, args.host)

        cmd = [binary, "--host", "127.0.0.1", "--port", str(backend_port)]
    else:
        backend_port = port
        cmd = [binary, "--host", args.host, "--port", str(port)]

    if args.no_token:
        cmd.append("--without-connection-token")
    else:
        cmd.extend(["--connection-token", token])

    cmd.extend(extra)

    scheme = "https" if use_https else "http"
    url = f"{scheme}://{args.host}:{port}/?folder={folder}"
    if not args.no_token:
        url += f"&tkn={token}"

    print(f"[portable-ovscode] starting server", file=sys.stderr)
    print(f"[portable-ovscode] open: {url}", file=sys.stderr)

    if use_https:
        # Start openvscode-server as subprocess, then run HTTPS proxy
        proc = subprocess.Popen(cmd)

        # Wait briefly for backend to start
        import time
        time.sleep(1)

        from portable_ovscode.proxy import run_tls_proxy
        run_tls_proxy(args.host, port, backend_port, cert_path, key_path)

        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            print("\n[portable-ovscode] stopped", file=sys.stderr)
        sys.exit(proc.returncode or 0)
    else:
        try:
            proc = subprocess.run(cmd)
            sys.exit(proc.returncode)
        except KeyboardInterrupt:
            print("\n[portable-ovscode] stopped", file=sys.stderr)


def _find_available_port(host: str, start: int, max_tries: int = 100) -> int:
    """Try to bind to *start*, then start+1, … Returns the first available port."""
    for offset in range(max_tries):
        candidate = start + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, candidate))
                return candidate
        except OSError:
            continue
    # Fallback: let the OS pick one
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    main()
