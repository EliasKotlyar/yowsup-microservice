FROM python:3-stretch
LABEL maintainer="gabriel.tandil@gmail.com"

WORKDIR /app

ADD . /app

RUN apt-get update
RUN apt-get install -y apt-utils
RUN apt-get install -y python3-pip python3-dev
RUN apt-get install -y rabbitmq-server
RUN pip3 install -r requirements.txt

EXPOSE 80

CMD ["sh","startall.sh"]
