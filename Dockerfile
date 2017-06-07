FROM python:3

WORKDIR /app

ADD . /app

RUN pip3 install -r requirements.txt
RUN pip install pexpect

EXPOSE 80

CMD ["sh","startall.sh"]
