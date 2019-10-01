Dockerfile for wazo-call-logd

## Install Docker

To install docker on Linux :

    curl -sL https://get.docker.io/ | sh
 
 or
 
     wget -qO- https://get.docker.io/ | sh

## Build

To build the image, simply invoke

    docker build -t wazo-call-logd github.com/wazo-platform/wazo-call-logd

Or directly in the sources in contribs/docker

    docker build -t wazo-call-logd .
  
## Usage

To run the container, do the following:

    docker run -d -v /conf/call-logd:/etc/wazo-call-logd/conf.d wazo-call-logd

On interactive mode :

    docker run -v /conf/call-logd:/etc/wazo-call-logd/conf.d -it wazo-call-logd bash

After launch wazo-call-logd.

    wazo-call-logd -f -v

## Infos

- Using docker version 1.5.0 (from get.docker.io) on ubuntu 14.04.
- If you want to using a simple webi to administrate docker use : https://github.com/crosbymichael/dockerui

To get the IP of your container use :

    docker ps -a
    docker inspect <container_id> | grep IPAddress | awk -F\" '{print $4}'
