"""Minimal TLS-terminating TCP proxy using only stdlib."""

from __future__ import annotations

import select
import socket
import ssl
import sys
import threading


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    """Forward bytes from src to dst until EOF."""
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except (OSError, BrokenPipeError):
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _handle(client: socket.socket, backend_addr: tuple[str, int]) -> None:
    """Connect to backend and bidirectionally pipe data."""
    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        backend.connect(backend_addr)
    except OSError:
        client.close()
        return

    t1 = threading.Thread(target=_pipe, args=(client, backend), daemon=True)
    t2 = threading.Thread(target=_pipe, args=(backend, client), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    client.close()
    backend.close()


def run_tls_proxy(
    host: str,
    port: int,
    backend_port: int,
    cert_path: str,
    key_path: str,
) -> None:
    """Run a TLS-terminating TCP proxy in a daemon thread."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(128)

    print(
        f"[portable-ovscode] HTTPS proxy listening on {host}:{port} -> 127.0.0.1:{backend_port}",
        file=sys.stderr,
    )

    def accept_loop() -> None:
        while True:
            try:
                raw_client, _ = listener.accept()
                try:
                    client = ctx.wrap_socket(raw_client, server_side=True)
                except ssl.SSLError:
                    raw_client.close()
                    continue
                threading.Thread(
                    target=_handle,
                    args=(client, ("127.0.0.1", backend_port)),
                    daemon=True,
                ).start()
            except OSError:
                break

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()
