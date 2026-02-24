#!/usr/bin/env python3
"""portable-ovscode: install and run openvscode-server with one command."""

from __future__ import annotations

import argparse
import os
import platform
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

GITHUB_RELEASE_URL = (
    "https://github.com/gitpod-io/openvscode-server/releases/download"
)
LATEST_VERSION = "1.109.5"


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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="portable-ovscode",
        description="Install and run openvscode-server with one command.",
        epilog=(
            "Any extra arguments after -- are passed directly to openvscode-server.\n\n"
            "Example:\n"
            "  uvx portable-ovscode --port 8080 --folder ~/project\n"
            "  uvx portable-ovscode -- --without-connection-token"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--install-dir",
        default="~/.local/share/openvscode-server",
        help="Directory to install the binary (default: ~/.local/share/openvscode-server)",
    )
    parser.add_argument(
        "--version",
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
        default="3000",
        help="Bind port (default: 3000)",
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
        "--install-only",
        action="store_true",
        help="Only install, don't start the server",
    )

    args, extra = parser.parse_known_args()

    check_platform()

    binary = install(args.install_dir, args.version)

    if args.install_only:
        print(binary)
        return

    token = args.token or secrets.token_hex(16)

    cmd = [binary, "--host", args.host, "--port", args.port]

    if args.no_token:
        cmd.append("--without-connection-token")
    else:
        cmd.extend(["--connection-token", token])

    folder = os.path.abspath(os.path.expanduser(args.folder))

    cmd.extend(extra)

    url = f"http://{args.host}:{args.port}/?folder={folder}"
    if not args.no_token:
        url += f"&tkn={token}"

    print(f"[portable-ovscode] starting server", file=sys.stderr)
    print(f"[portable-ovscode] open: {url}", file=sys.stderr)

    try:
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print("\n[portable-ovscode] stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
