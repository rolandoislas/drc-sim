#!/usr/bin/env bash
# drc-sim(-backend): Wii U gamepad emulator.
#
# drc-sim-backend initialization script
# https://github.com/rolandoislas/drc-sim

INSTALL_DIR="/opt/drc_sim/venv_drc/"

# Check to see if the script is running as root
# Exits if not root
check_root() {
    if [[ ${EUID} -ne 0 ]]; then
        echo "Drc-sim must be executed with root privileges."
        exit 1
    fi
}

start_drc_sim() {
    # Activate venv
    source "${INSTALL_DIR}bin/activate" &> /dev/null || exit 1
    # Start
    drc-sim-backend.py "$@"
}

main() {
    check_root
    start_drc_sim "$@"
}

main "$@"
