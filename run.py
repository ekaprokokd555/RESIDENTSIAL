#!/bin/bash

# Update dan upgrade sistem terlebih dahulu
sudo apt-get update -y
sudo apt-get upgrade -y

# Instalasi Squid Proxy Server
sudo apt-get install squid -y

# Instal dependensi jika perlu
sudo apt-get install -y curl

# Informasi akun Luminati (gantikan dengan kredensial Anda)
LUMINATI_USERNAME="your_username"   # Ganti dengan username Luminati Anda
LUMINATI_PASSWORD="your_password"   # Ganti dengan password Luminati Anda
LUMINATI_PORT="your_port"           # Ganti dengan port proxy Luminati Anda (misalnya 22225)
LUMINATI_ZONE="your_zone"           # Ganti dengan zone proxy Luminati (misalnya, 'us' atau 'eu')

# Backup konfigurasi squid yang lama sebelum memodifikasi
sudo cp /etc/squid/squid.conf /etc/squid/squid.conf.backup

# Mengonfigurasi Squid untuk menggunakan Proxy Luminati
sudo bash -c "cat <<EOL >> /etc/squid/squid.conf

# Konfigurasi Proxy Luminati (Bright Data)
cache_peer proxy.luminati.io parent $LUMINATI_PORT 0 no-query login=$LUMINATI_USERNAME-$LUMINATI_ZONE:$LUMINATI_PASSWORD
http_access allow all

EOL"

# Restart Squid untuk menerapkan konfigurasi baru
sudo systemctl restart squid

# Cek status Squid untuk memastikan proxy berjalan dengan benar
sudo systemctl status squid

echo "Proxy Luminati telah berhasil dikonfigurasi pada server ini."
