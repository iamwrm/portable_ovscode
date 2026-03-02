# portable-ovscode

[![PyPI](https://img.shields.io/pypi/v/portable-ovscode)](https://pypi.org/project/portable-ovscode/)

Run [openvscode-server](https://github.com/gitpod-io/openvscode-server) anywhere with a single command. No pre-install needed — just `uvx`.

## Quick Start

```bash
# SSH to your server, then:
uvx portable-ovscode
```

That's it. It downloads openvscode-server (if not cached), generates a token, starts the server in the current directory, and prints the URL.

## Usage

```
uvx portable-ovscode [OPTIONS] [-- EXTRA_ARGS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--install-dir DIR` | `~/.local/share/openvscode-server` | Where to put the binary |
| `-V, --version` | | Show package version and exit |
| `--server-version VER` | `1.109.5` | openvscode-server version |
| `--host ADDR` | `127.0.0.1` | Bind address |
| `--port PORT` | `3000` | Bind port (auto-increments if occupied) |
| `--token TOKEN` | auto-generated | Connection token |
| `--no-token` | | Disable auth token |
| `--folder PATH` | | Default folder to open |
| `--https` | | Enable HTTPS with auto-generated self-signed cert |
| `--cert PATH` | | Path to TLS certificate (implies --https) |
| `--cert-key PATH` | | Path to TLS private key (implies --https) |
| `--install-only` | | Download only, print binary path |

Extra arguments after `--` are passed directly to openvscode-server.

## Examples

```bash
# Install + run on port 8080, open ~/work
uvx portable-ovscode --port 8080 --folder ~/work

# Custom install location
uvx portable-ovscode --install-dir /opt/ovscode --folder ~/project

# Specific version
uvx portable-ovscode --server-version 1.95.3 --folder ~/code

# Just install, don't start
uvx portable-ovscode --install-only

# HTTPS with self-signed cert (for LAN access)
uvx portable-ovscode --https --host 192.168.1.50 --port 443

# Bring your own cert
uvx portable-ovscode --cert /path/cert.pem --cert-key /path/key.pem --host 0.0.0.0

# With SSH tunnel (from local machine)
ssh -L 3000:127.0.0.1:3000 user@remote
# then on remote:
uvx portable-ovscode --folder ~/project
# open http://127.0.0.1:3000/?tkn=<printed-token> locally
```

## Agentic Programming

Works great with AI coding agents like [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://github.com/openai/codex), or [pi-agent](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent). Let the agent edit your code, then spin up an editor to review the changes:

```bash
# Agent makes changes in ~/project...
# Review them instantly:
uvx portable-ovscode --folder ~/project
```

No IDE needs to be pre-installed — just open the URL, review diffs, and you're done.

## How It Works

1. Detects platform architecture (x64/arm64).
2. Downloads the release tarball from GitHub (cached in `--install-dir`).
3. Generates a random connection token.
4. Starts `openvscode-server` bound to loopback by default.
5. Prints the URL with token to stderr.

## License

MIT
