# portable-ovscode

Run [openvscode-server](https://github.com/gitpod-io/openvscode-server) anywhere with a single command. No pre-install needed — just `uvx`.

## Quick Start

```bash
# SSH to your server, then:
uvx portable-ovscode --port 3000 --folder ~/project
```

That's it. It downloads openvscode-server (if not cached), generates a token, starts the server, and prints the URL.

## Usage

```
uvx portable-ovscode [OPTIONS] [-- EXTRA_ARGS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--install-dir DIR` | `~/.local/share/openvscode-server` | Where to put the binary |
| `--version VER` | `1.109.5` | openvscode-server version |
| `--host ADDR` | `127.0.0.1` | Bind address |
| `--port PORT` | `3000` | Bind port |
| `--token TOKEN` | auto-generated | Connection token |
| `--no-token` | | Disable auth token |
| `--folder PATH` | | Default folder to open |
| `--install-only` | | Download only, print binary path |

Extra arguments after `--` are passed directly to openvscode-server.

## Examples

```bash
# Install + run on port 8080, open ~/work
uvx portable-ovscode --port 8080 --folder ~/work

# Custom install location
uvx portable-ovscode --install-dir /opt/ovscode --folder ~/project

# Specific version
uvx portable-ovscode --version 1.95.3 --folder ~/code

# Just install, don't start
uvx portable-ovscode --install-only

# With SSH tunnel (from local machine)
ssh -L 3000:127.0.0.1:3000 user@remote
# then on remote:
uvx portable-ovscode --folder ~/project
# open http://127.0.0.1:3000/?tkn=<printed-token> locally
```

## How It Works

1. Detects platform architecture (x64/arm64).
2. Downloads the release tarball from GitHub (cached in `--install-dir`).
3. Generates a random connection token.
4. Starts `openvscode-server` bound to loopback by default.
5. Prints the URL with token to stderr.

## License

MIT
