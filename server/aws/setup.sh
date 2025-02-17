#!/bin/bash

sudo apt-get update
sudo apt-get install -y certbot ca-certificates curl unzip
sudo systemctl disable certbot.timer
sudo systemctl stop certbot.timer
PUBLIC_IP=$(curl http://169.254.169.254/latest/meta-data/public-ipv4)
curl "https://update.dedyn.io/?hostname=${domain}&myipv4=$PUBLIC_IP" --header "Authorization: Token ${domain_token}"
cd /home/ubuntu
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip ./aws
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo mkfs -t ext4 /dev/nvme1n1
sudo mkdir -p /mnt/ebs_disk
sudo mount /dev/nvme1n1 /mnt/ebs_disk
sudo mkdir -p /mnt/ebs_disk/db
sudo docker run -v /mnt/ebs_disk/db:/mnt/db litestream/litestream:0.3.13 restore -o /mnt/db/requests.db s3://json-logger-db-backup/db
