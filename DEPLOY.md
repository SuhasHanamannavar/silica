# Deploy Silica backend to AWS (so everyone can use it)

The Silica frontend is on Vercel (static). The EDA backend (`server.py`) needs a
persistent host. One-command deploy:

## Prerequisites
- AWS account with an IAM user having `AmazonEC2FullAccess` (or scoped: ec2, ssm).
- `awscli` installed and configured (`aws configure`).
- A Hugging Face read token: https://huggingface.co/settings/tokens → `HF_TOKEN`.

## Deploy
```bash
chmod +x deploy.sh
HF_TOKEN=hf_your_token ./deploy.sh
```
This creates: a key pair, a security group (SSH from your IP, HTTP/HTTPS from world),
a `t3.medium` Ubuntu EC2 instance, and user-data that installs Docker, clones the
repo, builds the image, and runs the backend on port 80.

After ~3 min the script prints the public IP. Then:
1. **Point a subdomain** (e.g. `api.silica.ai`) at that IP (Route 53 A record).
2. **Enable TLS** on the box: `sudo docker run -d -p 443:443 ... caddy` reverse-proxy
   to the container, or install Caddy directly with `api.silica.ai` (auto Let's Encrypt).
3. **Set Vercel env var** `SILICA_API_URL=https://api.silica.ai` and redeploy the frontend.

## Cost
`t3.medium` + 30 GB EBS ≈ $35–45/month. Stop the instance when not in demo use to save.

## Security
- Rotate the AWS access keys after deploy (they were shared in chat).
- `HF_TOKEN` is passed as a container env var, never committed.
- SSH restricted to your IP; no long-lived keys on the box.
- No user RTL is uploaded to Hugging Face unless you explicitly enable it (privacy default: local-only).

## Verify
```bash
curl http://<public-ip>/api/health        # should show verilator+yosys versions
curl -X POST http://<public-ip>/api/chat -H 'Content-Type: application/json' -d '{"prompt":"Design a 4-bit counter"}'
```
Then open the live site and submit a prompt through the chat interface.
