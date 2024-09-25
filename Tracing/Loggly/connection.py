import requests

class LogglyConnection(object):

    def __init__(self, token):
        self.base_url = f"http://logs-01.loggly.com/inputs/{token}/tag/http/"
    def _loggly_post(self, post_data):
        headers = {'Content-type': 'text/plain'}

        try:
            requests.post(
                url=self.base_url,
                data=post_data,
                headers=headers)
        except ConnectionError as e:
            print(f"Verbindungsfehler bei Loggly: {e}")
        except Exception as e:
            print(f"Ein anderer Fehler ist aufgetreten bei Loggly: {e}")

    def create_input(self, message):
        self._loggly_post(message)

