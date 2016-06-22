import requests

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, connectWS


class DaemoClientProtocol(WebSocketClientProtocol):
    def send_data(self, data):
        self.sendMessage(data.encode('utf8'))

    def onConnect(self, response):
        print(response)

    def onOpen(self):
        print "WebSocket connection open."

    def onMessage(self, payload, isBinary):
        if not isBinary:
            print("Recv: {}".format(payload.decode('utf8')))

    def onClose(self, wasClean, code, reason):
        print "Connection closed: {0}".format(reason)


AUTH_ERROR = "Authentication credentials were not provided."

class DaemoClient:
    def __init__(self, host, port, client_id, access_token, refresh_token):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.projects = dict()
        self.session = requests.session()
        headers = {'Authorization': 'Bearer {}'.format(self.access_token)}
        factory = WebSocketClientFactory('ws://' + self.host + ':' + str(self.port))
        # factory = WebSocketClientFactory('ws://' + self.host + '/ws/api-client?subscribe-user', headers=headers)
        factory.protocol = DaemoClientProtocol
        connectWS(factory)
        reactor.connectTCP(self.host, self.port, factory)
        reactor.run()

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
        self.projects[project_id] = {'data': data, 'accept': accept, 'completion': completion, 'stream': stream}
        if stream:
            r = self.post_request(path='api/project/create-full/', data=data, stream=stream)
            for result in r: #as they come -- spawn subprocess to monitor events
                if result: #check to see if its actually something
                    action = accept(result)
                    if action:
                        completion(result)
                    #post action to take on the task
        else:
            while True:
                results = self.post_request(path='api/project/create-full/', data=data, stream=stream)
                #spawn and monitor as before except here we wait until server closes connection
                for result in results:
                    if result:
                        action = accept(result)
                        #post action to take on the task
            map(results, completion) #something like this

if __name__ == '__main__':
    daemo = DaemoClient("127.0.0.1", 9000, 'asd', 'asdf', 'asdf')



