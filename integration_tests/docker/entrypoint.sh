#!/bin/bash

cleanup ()
{
  kill -s SIGTERM $!
  exit 0
}

trap cleanup SIGINT SIGTERM

while true
do
  sleep 60 &
  wait $!
done
