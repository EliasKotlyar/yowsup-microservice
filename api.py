from flask import Flask, request
from flasgger import Swagger
from nameko.standalone.rpc import ClusterRpcProxy
from flasgger.utils import swag_from
import logging
app = Flask(__name__)
Swagger(app)
CONFIG = {'AMQP_URI': "amqp://guest:guest@localhost"}


@app.route('/send', methods=['POST'])
@swag_from('docs/send.yml')
def send():
    logger = app.logger
    type = request.json.get('type')
    body = request.json.get('body')
    address = request.json.get('address')
    logger.info('Get message: %s,%s,%s' % (type,body,address))

    with ClusterRpcProxy(CONFIG) as rpc:
        # asynchronously spawning and email notification
        rpc.yowsup.send(type,body,address)

    msg = "The message was sucessfully sended to the queue"
    return msg, 200

app.run(debug=True)