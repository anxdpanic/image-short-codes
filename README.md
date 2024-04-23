# Image Shortcode Url Generation and Hosting

### Docker (nginx and sftp)
```shell
git clone https://github.com/anxdpanic/image-short-codes
cd docker

# generate encrypted sftp password, and ssh keys
# configure SFTP_USERNAME, USER_UID, and USER_GID in .env
./run-first.sh

docker-compose up --build -d
```

### Cloudflare Worker (Python)
- Install [NodeJS](https://nodejs.org/en/download)

```shell
git clone https://github.com/anxdpanic/image-short-codes
cd cloudflare_worker/image-short

# configure settings in .toml
# [vars]
# CF_WORKER_BASE_URL = "https://img.example.com"
# RAW_IMG_BASE_URL = "https://images.example.com"

# [[d1_databases]]
# binding = "image_db"
# database_name = "images"
# database_id = ""

nano wrangler.toml

# install wrangler
npm install wrangler@latest
# or
yarn add wrangler@latest

# add authentication token as a secret on cloudflare
npx wrangler@latest add secret AUTHENTICATION_TOKEN

# deploy worker
npx wrangler@latest deploy
```

### Local Filesystem Watchdog
```shell
git clone https://github.com/anxdpanic/image-short-codes
cd watchdog

# configure settings for watchdog, discord webhook settings are optional
nano config.json

# install
pip install .

# run
watchdog-imgshort -f config.json
```
