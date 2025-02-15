#!/bin/sh

set -xe

CERT_BUCKET_NAME="json-logger-certificates"
DOMAIN="avocadotoast.life"
TLS_EMAIL="ilya.razenshteyn@gmail.com"

sudo docker compose down
sudo docker container rm -f $(sudo docker container ls -aq) || true
sudo docker compose up -d
output=$(aws s3 ls s3://$CERT_BUCKET_NAME/certificates.tar.gz || true)
if [ -z "$output" ]; then
  until sudo certbot certonly --webroot -w ./webserver_root -d $DOMAIN --non-interactive --agree-tos -m $TLS_EMAIL
  do
    echo "Trying again"
    sleep 60
  done
  sudo tar -czf certificates.tar.gz /etc/letsencrypt
  aws s3 cp certificates.tar.gz s3://$CERT_BUCKET_NAME/
fi
aws s3 cp s3://$CERT_BUCKET_NAME/certificates.tar.gz .
sudo tar -xzf certificates.tar.gz -C /
sudo rm -rf /home/ubuntu/renew.sh
sudo cat <<EOF >/home/ubuntu/renew.sh
#!/bin/sh

set -xe

TS=\$(date -u +"%Y%m%d%H%M%S")
echo \$TS
certbot renew
tar -czf /home/ubuntu/certificates.tar.gz /etc/letsencrypt
aws s3 cp /home/ubuntu/certificates.tar.gz s3://$CERT_BUCKET_NAME/
cd "$(pwd)"
docker compose down
docker compose up -d
EOF
sudo chown root:root /home/ubuntu/renew.sh
sudo chmod +x /home/ubuntu/renew.sh
until sudo /home/ubuntu/renew.sh
do
  echo "Trying again"
  sleep 60
done
tmp_crontab=$(mktemp)
echo "0 */12 * * * /home/ubuntu/renew.sh >> /var/log/renew.log 2>&1" > "$tmp_crontab"
sudo crontab -u root "$tmp_crontab"
rm -f "$tmp_crontab"
