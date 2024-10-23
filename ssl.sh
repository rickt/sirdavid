#! /bin/bash

sudo cp /etc/letsencrypt/live/cloud.rickt.dev/{cert,chain,fullchain,privkey}.pem cloud.rickt.dev/
chown rickt:rickt cloud.rickt.dev/*pem
echo " done."
