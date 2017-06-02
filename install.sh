#!/usr/bin/env bash
# drc-sim(-backend): Wii U gamepad emulator.
#
# drc-sim-backend install script
# https://github.com/rolandoislas/drc-sim
#
# Changelog
#
# June 1, 2017 - 1.1
#    Add output on error for make, cmake, and setup.py
#    Add setup.py outputs to install.txt during install and it is read from for an uninstall
#    Move init script, desktop launcher, and icon to setup.py
#    Add version number
#    Add pkg-info - wpa_supplicant compile fails without it
#    Remove virtualenv
# June 1, 2017 - 1.1.1
#    Fix Make, cmake, and setup.py not returning on errors
#    Fix current directory not being restored on a git update failure

VERSION="1.1"
REPO_DRC_SIM="https://github.com/rolandoislas/drc-sim.git"
REPO_WPA_SUPPLICANT_DRC="https://github.com/rolandoislas/drc-hostap.git"
REPO_DRC_SIM_C="https://github.com/rolandoislas/drc-sim-c.git"
INSTALL_DIR="/opt/drc_sim/"
dependencies=()
branch_drc_sim=""

# Checks to see if OS has apt-get and sets dependencies
# Exits otherwise
check_os() {
    if command -v apt-get &> /dev/null; then
        echo "Command apt-get found."
        # Backend dependencies
        dependencies=("python3" "python3-pip"
        "net-tools" "wireless-tools" "sysvinit-utils" "psmisc" "rfkill"
        "isc-dhcp-client" "ifmetric" "python3-tk" "gksu")
        # Wpa supplicant compile dependencies
        dependencies+=("git" "libssl-dev" "libnl-genl-3-dev" "gcc" "make" "pkg-config")
        # DRC Sim Server C++
        dependencies+=("libavcodec-dev" "libswscale-dev" "libjpeg-dev" "cmake")
    else
        echo "The command apt-get was not found. This OS is not supported."
        exit 1
    fi
}

# Check to see if the script is running as root
# Exits if not root
check_root() {
    if [[ ${EUID} -ne 0 ]]; then
        echo "Install script must be executed with root privileges."
        exit 1
    fi
}

# Checks and installs pre-defined decencies array
# Exits on failed dependency
install_dependencies() {
    echo "Installing dependencies."
    for dependency in "${dependencies[@]}"
    do
        installed="$(dpkg -s ${dependency} 2>&1)"
        if [[ ${installed} =~ "Status: install ok installed" ]]; then
            echo "${dependency} [INSTALLED]"
        else
            echo "${dependency} [INSTALLING]"
            if command apt-get -y install ${dependency} &> /dev/null; then
                echo "${dependency} [INSTALLED]"
            else
                echo "${dependency} [FAILED]"
                exit 1
            fi
        fi
    done
}

# Update git directory while stashing changed return 1
# Returns 1 on failure
update_git() {
    cur_dir="${PWD}"
    cd "${1}" &> /dev/null || return 1
    if [[ -d "${1}" ]]; then
        echo "Found existing git directory ${1}"
        if command git stash --include-untracked &> /dev/null; then
            echo "Stashed git changes"
            echo "Updating git repo"
            if command git pull &> /dev/null; then
                echo "Updated git repo"
            else
                cd "${cur_dir}" &> /dev/null || return 1
                return 1
            fi
        else
            cd "${cur_dir}" &> /dev/null || return 1
            return 1
        fi
    fi
    cd "${cur_dir}" &> /dev/null || return 1
    return 0
}

# Clones a git repo to the install path
# If the directory exists it is removed
# Param $1: git repo url
get_git() {
    git_dir="${INSTALL_DIR}${2}"
    if update_git ${git_dir}; then
        return 0
    else
        # Remove directory for a clean clone
        if [[ -d "${git_dir}" ]]; then
            rm -rf "${git_dir}"
        fi
    fi
    # Clone
    echo "Cloning ${1} into ${git_dir}"
    if command git clone ${1} ${git_dir} &> /dev/null; then
        echo "Cloned ${1}"
    else
        echo "Failed to clone ${1}"
        exit 1
    fi
}

# Compiles wpa_supplicant after fetching it from git
compile_wpa() {
    get_git ${REPO_WPA_SUPPLICANT_DRC} "wpa"
    echo "Compiling wpa_supplicant_drc"
    compile_dir="${INSTALL_DIR}wpa/wpa_supplicant/"
    cur_dir="${PWD}"
    cd "${compile_dir}" &> /dev/null || return 1
    cp ../conf/wpa_supplicant.config ./.config &> /dev/null || return 1
    compile_log="${compile_dir}make.log"
    echo "Compile log at ${compile_log}"
    if ! make &> ${compile_log}; then cat "${compile_log}"; return 1; fi
    echo "Installing wpa_supplicant_drc and wpa_cli_drc to /usr/local/bin"
    cp wpa_supplicant /usr/local/bin/wpa_supplicant_drc &> /dev/null || return 1
    cp wpa_cli /usr/local/bin/wpa_cli_drc &> /dev/null || return 1
    cd "${cur_dir}" &> /dev/null || return 1
    return 0
}

# Compiles drc_sim_c after fetching it from git
compile_drc_sim_c() {
    get_git ${REPO_DRC_SIM_C} "drc_sim_c"
    echo "Compiling drc_sim_c"
    compile_dir="${INSTALL_DIR}drc_sim_c/"
    cur_dir="${PWD}"
    cd "${compile_dir}" &> /dev/null || return 1
    compile_log="${compile_dir}make.log"
    cmake_log="${compile_dir}cmake.log"
    echo "Compile log at ${compile_log}"
    if ! cmake "${compile_dir}" &> "${cmake_log}"; then cat "${cmake_log}"; return 1; fi
    if ! make &> "${compile_log}"; then cat "${compile_log}"; return 1; fi
    echo "Installing drc_sim_c to /usr/local/bin"
    make install &> /dev/null || return 1
    cd "${cur_dir}" &> /dev/null || return 1
    return 0
}

# Installs drc-sim in a virtualenv
install_drc_sim() {
    echo "Installing DRC Sim Server GUI/CLI Utility"
    # Paths
    drc_dir="${INSTALL_DIR}drc/"
    cur_dir="${PWD}"
    # Get source
    if [[ "${branch_drc_sim}" != "local" ]]; then
        # Get repo
        get_git ${REPO_DRC_SIM} "drc"
    else
        # Copy local
        if [[ ! -f "${cur_dir}/setup.py" ]]; then
            echo "Cannot perform local install. Missing source files at ${cur_dir}."
            return 1
        fi
        if [[ ! -d "${INSTALL_DIR}" ]]; then
            mkdir "${INSTALL_DIR}" &> /dev/null || return 1
        fi
        rm -rf ${drc_dir} &> /dev/null || return 1
        mkdir ${drc_dir} &> /dev/null || return 1
        cp -R "${cur_dir}/." "${drc_dir%/*}" &> /dev/null || return 1
    fi
    # Install python dependencies
    echo "Installing setuptools"
    python3 -m pip install setuptools &> /dev/null || return 1
    # Remove an existing install of drc-sim
    echo "Attempting to remove previous installations"
    python3 -m pip uninstall -y drcsim &> /dev/null || \
        echo "Failed to remove the previous installation. Attempting to install anyway."
    # Set the directory
    cd "${drc_dir}" &> /dev/null || return 1
    # Branch to checkout
    if [[ "${branch_drc_sim}" != "local" ]]; then
        echo "Using branch \"${branch_drc_sim}\" for drc-sim install"
        git checkout ${branch_drc_sim} &> /dev/null || return 1
    else
        echo "Using current directory as install source"
    fi
    # Install
    echo "Installing drc-sim"
    echo "Downloading Python packages. This may take a while."
    if ! python3 "${drc_dir}setup.py" install --record "${drc_dir}/install.txt" &> "/tmp/drc-sim-py-install.log"; then
        cat "/tmp/drc-sim-py-install.log"
        return 1
    fi
    cd "${cur_dir}" &> /dev/null || return 1
    # Update icon cache
    update-icon-caches /usr/share/icons/* &> /dev/null || echo "Failed to update icon cache."
}

# Echos the general info
print_info() {
    echo "Drc-sim installer (script version ${VERSION})"
    printf "\thttps://github.com/rolandoislas/drc-sim\n"
}

# Uninstalls DRC Sim then exists
uninstall() {
    drc_install_log="${INSTALL_DIR}drc/install.txt"
    echo "Uninstalling DRC Sim Server"
    # Remove setup.py files
    if [[ -f "${drc_install_log}" ]]; then
        echo "Files to remove:"
        cat ${drc_install_log}
        read -p "Remove these files? [Y/N]" reponse
        if [[ ${reponse} =~ [Yy](es)* ]]; then
            tr '\n' '\0' < ${drc_install_log} | xargs -0 sudo rm -f --
            echo "Removed Python installed files"
        else
            echo "Not removing Python installed files"
            echo "Install canceled"
            exit 2
        fi
    else
        cat ${drc_install_log}
        echo "Could not clean Python installed files. Missing ${drc_install_log}"
    fi
    # Launcher (.desktop)
    to_remove=("/usr/share/applications/drc-sim-backend.desktop" "/usr/share/applications/drcsimbackend.desktop"
        "/usr/share/icons/hicolor/512x512/apps/drcsimbackend.png")
    for item in "${to_remove[@]}"; do
        if [[ -f "${item}" ]]; then
            echo "Removing application launcher"
            rm -f ${item} &> /dev/null
        fi
    done
    # Install dir
    echo "Removing install directory"
    rm -rf ${INSTALL_DIR} &> /dev/null || echo "Failed to remove install directory."
    # TODO uninstall packages
    printf "\nNOT removing package dependencies\n"
    printf "${dependencies[*]}\n\n"
    # Done
    echo "Uninstalled DRC Sim Server"
    exit 0
}

# Parses args
check_args() {
    branch_drc_sim=${1:-master}
    # Help
    if [[ "${1}" == "help" ]] || [[ "${1}" == "-h" ]]; then
        echo "Usage: <install.sh> [argument]"
        echo "  Defaults to install."
        echo "  Arguments:"
        echo "    -h, help : help menu"
        echo "    branch : branch to use for drc-sim (master, develop, local) master is used by default"
        echo "    uninstall : uninstall DRC Sim"
        exit 1
    # Uninstall
    elif [[ "${1}" == "uninstall" ]]; then
        uninstall
    # Install branch
    elif [[ "${branch_drc_sim}" != "develop" ]] && [[ "${branch_drc_sim}" != "master" ]] && 
         [[ "${branch_drc_sim}" != "local" ]]; then
        echo "Invalid branch \"${1}\""
        check_args "help"
    fi
}

# Check if command return value is non-zero and exit with message.
# If the command exited with a zero exit value the success message will be echoed
pass_fail() {
    if $1; then
        echo $2
    else
        echo $3
        exit 1
    fi
}

# Echo post install message and exit
post_install() {
    echo "Install finished"
    echo "\"DRC SIM Server\" will now appear in GUI application menus."
    echo "It can also be launched via \"drc-sim-backend\"."
    exit 0
}

# Install drc_sim
install() {
    install_dependencies
    pass_fail compile_wpa "Compiled wpa_supplicant" "Failed to compile wpa_supplicant"
    pass_fail compile_drc_sim_c "Compiled drc_sim_c" "Failed to compile drc_sim_c"
    pass_fail install_drc_sim "Installed drc-sim" "Failed to install drc-sim"
    post_install
}

main() {
    print_info
    check_root
    check_os
    check_args "$@"
    install
}


main "$@"
