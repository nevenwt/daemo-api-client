import requests
import json

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, connectWS


class DaemoClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print(response)

    def onOpen(self):
        print "WebSocket connection opened."
        def send():        
            self.sendMessage(self.factory.message.encode('utf8'))

        send()

    def onMessage(self, payload, isBinary):
        if not isBinary:
            response = json.loads(payload.decode('utf8'))
            if response.get('project_id', False):
                data = response.get('data', None)
                if hasattr(self.factory, 'accept'):
                    if self.factory.accept(data):
                        if hasattr(self.factory, 'completion'):
                            self.factory.completion(data)
                    else:
                        #Some message to server saying the task was not accepted
                        self.sendMessage(u'{"project_id":1234, "data": "{"accept": False}"}')

    def onClose(self, wasClean, code, reason):
        print "WebSocket connection closed: {0}".format(reason)


AUTH_ERROR = "Authentication credentials were not provided."

class DaemoClient:
    def __init__(self, host, port, client_id, access_token, refresh_token):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.session = requests.session()
        headers = {'Authorization': 'Bearer {}'.format(self.access_token)}
        self.factory = WebSocketClientFactory('ws://' + self.host + ':' + str(self.port), headers=headers)
        # factory = WebSocketClientFactory('ws://' + self.host + '/ws/api-client?subscribe-user', headers=headers)
        self.factory.protocol = DaemoClientProtocol
        reactor.connectTCP(self.host, self.port, self.factory)

    def post_request(self, path, data):
        headers = {"Authorization": "Bearer " + self.access_token, "Content-Type": 'application/json'}
        response = self.session.post(self.host + path, data=data, headers=headers)
        if response.get('detail', '') == AUTH_ERROR:
            self.refresh()
            headers = {"Authorization": "Bearer " + self.access_token, "Content-Type": 'application/json'}
            response = self.session.post(self.host + path, data=data, headers=headers)
        return response

    def get_request(self, path):
        headers = {"Authorization": "Bearer " + self.access_token}
        response = self.session.get(url=self.host + path, headers=headers)
        if response.get('detail', '') == AUTH_ERROR:
            self.refresh()
            headers = {"Authorization": "Bearer " + self.access_token}
            response = self.session.get(url=self.host + path, headers=headers)
        return response

    def refresh(self):
        data = {'client_id': self.client_id, 'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token}
        response = self.session.post(self.host + 'api/oauth2-ng/token/', data=data)
        if 'error' in response:
            print "There was an error refreshing your access token."
            print "Please contact customer service or generate a new token on Daemo."
            exit()
        else:
            print "Successfully generated a new access token."
            self.access_token = response.get('access_token', '')
            self.refresh_token = response.get('refresh_token', '')

    def launch_task(self, project_id, data, accept, completion, stream=False):
        self.factory.message = data
        self.factory.accept = accept
        self.factory.completion = completion
        reactor.run()


if __name__ == '__main__':
    import sys
    from twisted.python import log

    log.startLogging(sys.stdout)

    def accept(x):
        return True
    
    def completion(x):
        print "we have completed this task"
        return x

    daemo = DaemoClient("127.0.0.1", 9000, 'asdf', 'asdf', 'asdf')
    daemo.launch_task(1234, '{"project_id": 1234, "data": "asdf"}', accept, completion)



