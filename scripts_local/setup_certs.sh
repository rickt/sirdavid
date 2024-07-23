#! /bin/bash

HOSTNAME="cloud.rickt.dev"

TOPLEVEL="/etc/letsencrypt/live/$HOSTNAME"

echo "TOPLEVEL=$TOPLEVEL"

mkdir -p $HOSTNAME
for FILE in cert chain fullchain privkey
do
	sudo cp $TOPLEVEL/$FILE.pem $HOSTNAME/
done

# EOF
