import errno
import inspect
from time import sleep
import yaml

import os
from flasgger import Swagger
from flasgger.utils import swag_from
from flask import Flask, request
from nameko.standalone.rpc import ClusterRpcProxy

from src.layer import STATUS_FILES_DIRECTORY

app = Flask(__name__)
Swagger(app)

CONFIG = {'AMQP_URI': "pyamqp://guest:guest@localhost"}

TIMEOUT = 0.5
TIMEOUTS_NUMBER = 6
CONFIG_FILE = 'serviceconfig.yml'


@app.route('/send', methods=['POST'])
@swag_from('docs/send.yml')
def send():
    logger = app.logger
    type = request.json.get('type')
    body = request.json.get('body')
    address = request.json.get('address')
    logger.info('Get message: %s,%s,%s' % (type, body, address))

    if not os.path.exists(os.path.dirname(STATUS_FILES_DIRECTORY)):
        try:
            os.makedirs(os.path.dirname(STATUS_FILES_DIRECTORY))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    status_filename = STATUS_FILES_DIRECTORY + 'lock'

    # removing the file if it exists
    try:
        os.remove(status_filename)
    except:
        pass

    status = None
    try:
        with ClusterRpcProxy(CONFIG) as rpc:
            # asynchronously spawning and email notification
            rpc.yowsup.send(type, body, address)

        # trying to wait for success or fail
        timeouts = 0
        while status is None and timeouts < TIMEOUTS_NUMBER:
            timeouts += 1
            try:
                if os.path.isfile(status_filename):
                    status = 'success'

                if status is None:
                    sleep(TIMEOUT)
            except:
                pass
    except Exception as e:
        print('Error sending a message: {}'.format(str(e)))
    finally:
        try:
            os.remove(status_filename)
        except:
            pass

    if status == 'success':
        msg = "The message was successfully sent"
    elif status is None:
        # if the username is in environment variables
        _from = os.getenv('USERNAME')
        # if it is in config file
        if _from is None:
            # get current directory
            current_directory = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            # reading username from config
            full_config_file_path = '{}/{}'.format(current_directory, CONFIG_FILE)
            stream = open(full_config_file_path, "r")
            doc = yaml.load(stream)
            _from = doc['YOWSUP_USERNAME']

        msg = '{{from: "{}", to:"{}", status: "undelivered"}}'.format(_from, address)

    return msg, 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=88)