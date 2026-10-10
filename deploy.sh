#!/usr/bin/env bash
# One-command AWS deploy for Silica backend. Requires: awscli configured, your HF token.
# Usage: HF_TOKEN=hf_xxx ./deploy.sh
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
AMI_ID="${AMI_ID:-$(aws ssm get-parameters --names /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id --query 'Parameters[0].Value' --output text --region $REGION)}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.medium}"
KEY_NAME="${KEY_NAME:-silica-backend}"
SEC_GROUP="${SEC_GROUP:-silica-backend-sg}"

echo "==> Silica backend deploy to AWS ($REGION, $INSTANCE_TYPE)"
[ -z "${HF_TOKEN:-}" ] && { echo "ERROR: set HF_TOKEN (huggingface.co/settings/tokens)"; exit 1; }

# Key pair
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION >/dev/null 2>&1; then
  aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text --region $REGION > ~/.ssh/$KEY_NAME.pem
  chmod 600 ~/.ssh/$KEY_NAME.pem
  echo "Created key pair ~/.ssh/$KEY_NAME.pem"
fi
# Security group: 22 (your IP), 80/443 (world)
SG_ID=$(aws ec2 create-security-group --group-name $SEC_GROUP --description "Silica backend" --query 'GroupId' --output text --region $REGION 2>/dev/null || aws ec2 describe-security-groups --group-names $SEC_GROUP --query 'SecurityGroups[0].GroupId' --output text --region $REGION)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr $(curl -s ifconfig.me)/32 --region $REGION 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $REGION 2>/dev/null || true

# Launch instance with user-data that installs everything and runs the backend
cat > /tmp/silica-userdata.sh <<EOF
#!/bin/bash
apt-get update -y && apt-get install -y docker.io git
git clone https://github.com/SuhasHanamannavar/silica.git /opt/silica
cd /opt/silica
docker build -t silica .
docker run -d --name silica -p 80:8000 -e HF_TOKEN=$HF_TOKEN --restart unless-stopped silica
EOF
INSTANCE_ID=$(aws ec2 run-instances --image-id $AMI_ID --instance-type $INSTANCE_TYPE --key-name $KEY_NAME --security-group-ids $SG_ID --user-data file:///tmp/silica-userdata.sh --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=silica-backend}]" --query 'Instances[0].InstanceId' --output text --region $REGION)
echo "Launched instance: $INSTANCE_ID"
echo "Waiting for public IP..."
sleep 30
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $REGION)
echo "========================================="
echo "Silica backend deploying at: http://$PUBLIC_IP"
echo "(TLS: point a subdomain at this IP, then run Caddy/Let's Encrypt on the box)"
echo "Update Vercel env var SILICA_API_URL=http://$PUBLIC_IP"
echo "SSH: ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo "========================================="
