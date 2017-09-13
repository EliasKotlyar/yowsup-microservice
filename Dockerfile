FROM python:latest
LABEL maintainer="gabriel.tandil@gmail.com"

WORKDIR /app

ADD . /app

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install -y apt-utils
RUN apt-get install -y python3-pip python3-dev rabbitmq-server
RUN pip3 install -r requirements.txt

EXPOSE 80

CMD ["sh","startall.sh"]
