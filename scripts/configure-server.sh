#!/usr/bin/env bash
# Installs our system-service drop-in; does not restart or stop the server.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
command -v systemctl >/dev/null
if [[ $(systemctl show ollama.service --property=LoadState --value) != loaded ]]; then
    echo 'Expected an installed system-level ollama.service. See the README for manual serving.' >&2
    exit 1
fi
admin=()
if (( EUID != 0 )); then
    command -v sudo >/dev/null
    admin=(sudo)
fi
destination=/etc/systemd/system/ollama.service.d/90-ser8.conf
"${admin[@]}" install -d -m 0755 /etc/systemd/system/ollama.service.d
if "${admin[@]}" test -f "$destination"; then
    backup="${destination}.backup.$(date +%Y%m%d-%H%M%S).$$"
    "${admin[@]}" cp -p -- "$destination" "$backup"
    echo "Previous SER8 drop-in backed up: $backup"
fi
"${admin[@]}" install -m 0644 "$root/systemd/90-ser8.conf" "$destination"
"${admin[@]}" systemctl daemon-reload
echo 'Settings installed. Finish active work and unload listed models with ollama stop MODEL.'
echo 'Then apply them: sudo systemctl restart ollama'
echo 'Inspect combined configuration: systemctl cat ollama'
