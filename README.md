# yowsup-microservice
This Project provides a microservice which implements an interface to yowsup2. You can Send/Receive Whatsapp-Messages with any language of your choice.

### Prerequisites:

Install & Configure the yowsup2 CLI Demo.

Use yowsup-cli to register a Number.



### Installation(General):

1. Install rabbitmq
2. Install Flask,Nameko,Flasgger
3. Install yowsup2

### Installation(on Ubuntu):

```bash
# Install Python Stuff:
sudo apt-get install python3-pip python3-dev
pip3 install nameko
pip3 install flask
pip3 install flasgger
pip3 install git+https://github.com/tgalal/yowsup@master
# Install RabbitMQ
apt-get install rabbitmq-server

```


### Configuration:

rename "service.yml.sample to "service.yml" and put your credentials into it.

### Usage:

Run the the Service with:
```
startservice.sh
```

Run the the Api with:
```
startapi.sh
```



Go to:
http://127.0.0.1:5000/apidocs/index.html




### Example Messages for other Integrations:

Have a look at swagger documentation.

### Debugging

Run
```
nameko shell
n.rpc.yowsup.send(type="simple", body="This is a test Message!", address="49XXXX")
```

### Using Docker to run in a container

This will automatically setup and run the main service and the API, connected with the RabbitMQ service!

Change the following environment variables with your credentials (after registering on yowsup-cli).

```
environment:
  - USERNAME=<your_account_number>
  - PASSWORD=<your_password>
```

Then run:

```
docker stack deploy -c docker-compose.yml yowsup
```

And you're all set!! :D
