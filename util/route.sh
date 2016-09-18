#!/bin/bash
# Wii NIC
wiiface="wlx687f747d2e59"

# Normal NIC
interface="enp2s0"
ip="192.168.2.141"
subnet="192.168.2.0/24" # subnet? terminology might be wrong
gateway="192.168.2.1"

# These are for the Wii U and gamepad.
# They appear to be static but here Justin Case.
WII_LOCAL_IP="192.168.1.11"
WII_SUBNET="192.168.1.0/24"
WII_GATEWAY="192.168.1.1"

# Assign an ip to the interface.
sudo ifconfig $wiiface $WII_LOCAL_IP

# This creates two different routing tables, that we use based on the source-address.
sudo ip rule add from $ip table 1
sudo ip rule add from $WII_LOCAL_IP table 2

# Configure the two different routing tables
sudo ip route add $subnet dev $interface scope link table 1
sudo ip route add default via $gateway dev $interface table 1

sudo ip route add $WII_SUBNET dev $wiiface scope link table 2
sudo ip route add default via $WII_GATEWAY dev $wiiface table 2

# default route for the selection process of normal internet-traffic
sudo ip route add default scope global nexthop via $gateway dev $interface

# Setup dhcp
sudo dhclient
