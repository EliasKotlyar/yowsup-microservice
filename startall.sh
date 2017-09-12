#!/usr/bin/env bash
/etc/init.d/rabbitmq-server start
sleep 30
sh ./startservice.sh & sh ./startapi.sh
