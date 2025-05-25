#!/bin/sh

sudo nmcli device wifi hotspot ssid SoccerCam password 7202290437
sudo nmcli c mod Hotspot ipv4.address 192.168.20.1/24 ipv4.method manual ipv4.gateway 192.168.20.1 ipv4.dns "8.8.8.8,8.8.4.4"
sudo nmcli c up Hotspot
