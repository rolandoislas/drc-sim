import os

# Info
VERSION = "2.0"
NAME = "DRC SIM Server"

# Paths
PATH_ROOT = os.path.expanduser("~/.drc-sim/")
PATH_LOG_DIR = os.path.join(PATH_ROOT, "log/")
PATH_CONF_CONNECT = os.path.join(PATH_ROOT, "connect_to_wii_u.conf")
PATH_LOG_WPA = os.path.join(PATH_LOG_DIR, "wpa_supplicant_drc.log")
PATH_CONF_NETWORK_MANAGER = "/etc/NetworkManager/NetworkManager.conf"
PATH_TMP = "/tmp/drc-sim/"
PATH_CONF_CONNECT_TMP = os.path.join(PATH_TMP, "get_psk.conf")
PATH_LOG_DRC_SIM_C = os.path.join(PATH_LOG_DIR, "drc_sim_c.log")
