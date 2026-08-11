#!/usr/bin/env bash
# Compatibility name. Machine setup is zcutil/check-setup.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check-setup.sh" "$@"
