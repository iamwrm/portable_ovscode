"""Tests for port auto-detection logic."""

from __future__ import annotations

import socket
import unittest

from portable_ovscode.cli import _find_available_port


class TestFindAvailablePort(unittest.TestCase):
    """Tests for _find_available_port()."""

    def test_returns_start_when_free(self):
        """When the start port is free, it should be returned directly."""
        # Pick a high ephemeral port that's very likely free
        port = _find_available_port("127.0.0.1", 19750)
        self.assertEqual(port, 19750)

    def test_skips_occupied_port(self):
        """When the start port is occupied, the next free one is returned."""
        # Occupy a port
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 19760))
        blocker.listen(1)
        try:
            port = _find_available_port("127.0.0.1", 19760)
            self.assertEqual(port, 19761)
        finally:
            blocker.close()

    def test_skips_multiple_occupied_ports(self):
        """When several consecutive ports are occupied, skips all of them."""
        blockers = []
        try:
            for p in range(19770, 19774):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
                s.listen(1)
                blockers.append(s)

            port = _find_available_port("127.0.0.1", 19770)
            self.assertEqual(port, 19774)
        finally:
            for s in blockers:
                s.close()

    def test_fallback_when_all_tries_exhausted(self):
        """When max_tries is tiny and all candidates occupied, falls back to OS-assigned port."""
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 19780))
        blocker.listen(1)
        try:
            port = _find_available_port("127.0.0.1", 19780, max_tries=1)
            # Should get a valid port from the OS, not 19780
            self.assertNotEqual(port, 19780)
            self.assertGreater(port, 0)
        finally:
            blocker.close()

    def test_returned_port_is_actually_bindable(self):
        """The returned port should be bindable."""
        port = _find_available_port("127.0.0.1", 19790)
        # Verify we can bind to it
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
