# NEWS 20180327
The **media** branch has image recibe (and some other media) capabilities. Also reconnect and minor imporovements. Thanks to all colaborators.

## Media version docker image
gabrieltandil/yowsup-microservice:media

# yowsup-microservice
This Project provides a microservice which implements an interface to yowsup2. You can Send/Receive Whatsapp-Messages with any language of your choice.

### Prerequisites

Install & Configure the yowsup2 CLI Demo.

Use yowsup-cli to register a Number.

## Without Docker

### Installation (General)

1. Install rabbitmq
2. Install Flask,Nameko,Flasgger,pexpect
3. Install yowsup2

### Installation (on Ubuntu)

```bash
# Install Python Stuff:
sudo apt-get install python3-pip python3-dev
pip3 install nameko
pip3 install flask
pip3 install flasgger
pip3 install pexpect
# git+https://github.com/tgalal/yowsup@master works fine
pip3 install git+https://github.com/tgalal/yowsup@master 

# Install RabbitMQ
apt-get install rabbitmq-server

```


### Configuration

rename *service.yml.sample* to *service.yml* and put your credentials into it.


### Usage

Run the the Service with:
```
startservice.sh
```

Run the the Api with:
```
startapi.sh
```
#### Send
Go to:
http://127.0.0.1:5000/apidocs/index.html

#### Recive
Set the parameter ENDPOINT_RESEND_MESSAGES to the url of your application where you want the messages to be dispatched.
The received messages will be sent to that url in JSON format.
```
{{"from":"{FROM}","to":"{TO}","time":"{TIME}","id":"{MESSAGE_ID}","message":"{MESSAGE}","type":"{TYPE}"}}
```

### Example Messages for other Integrations:

Have a look at swagger documentation.

### Debugging

Run
```
nameko shell
n.rpc.yowsup.send(type="simple", body="This is a test Message!", address="49XXXX")
```

## Using Docker to run in a container

This will automatically setup and run the main service and the API
The service is exposed in port 80

Change the following environment variables with your credentials (after registering on yowsup-cli) in *env.list* file.
Or create a new env.list file

```
USERNAME=<your_account_number>
PASSWORD=<your_password>
TOKEN_RESEND_MESSAGES=<your_token_resend_messages>
ENDPOINT_RESEND_MESSAGES=<your_endpoint_resend_messages>
```
- *TOKEN_RESEND_MESSAGES: any value established by you that will be sent in the request to validate the identity.*
- *ENDPOINT_RESEND_MESSAGES: the url where messages received from the whatsapp network will be sent in the specified json format.*

Then run:

```
docker run --name <name> --env-file env.list -p <hostPort>:80 gabrieltandil/yowsup-microservice:latest
```

And you're all set!! :D

### Build docker image

```
docker build -t yowsup-microservice:latest .
```
