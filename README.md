# Image Shortcode Url Generation and Hosting

## Docker (nginx and sftpd)

#### Job 
- Host images with nginx from a single directory `./data`
- SFTPd with access to `./data` for managing image files

---

```shell
git clone https://github.com/anxdpanic/image-short-codes
cd docker

# generate encrypted sftp password, and ssh keys
# configure SFTP_USERNAME, USER_UID, and USER_GID in .env
./run-first.sh

docker-compose up --build -d
```

---

## Cloudflare Worker (Python)

Requires [NodeJS](https://nodejs.org/en/download)

#### Job 
- Handle incoming http requests for shortcodes
- Manage Cloudflare D1 database with shortcode <-> url references based on the http request (authentication header required)
- Resolve shortcode to it's url (hosted by the nginx docker) and display the image

---

```shell
git clone https://github.com/anxdpanic/image-short-codes
cd cloudflare_worker/image-short

# configure settings in .toml
# [vars]
# CF_WORKER_BASE_URL = "https://img.example.com"
# RAW_IMG_BASE_URL = "https://images.example.com"

# [[d1_databases]]
# database_id = ""

cp wrangler.toml.template wrangler.toml
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

---

## Image Watchdog

#### Job 
- Monitor a single folder for changes to image files
- Mirror those changes to the sftp server to be hosted by nginx
- Manage shortcodes through the cloudflare worker via http requests
- Send Discord notification with new shortcodes

---

```shell
git clone https://github.com/anxdpanic/image-short-codes
cd watchdog

# configure settings for watchdog, discord webhook settings are optional
cp config.json.template config.json
nano config.json

# install
pip install .
# confirm working
watchdog-imgshort -f config.json
# run in the background
screen -dmS ImageWatchdog watchdog-imgshort -f config.json
```

---
