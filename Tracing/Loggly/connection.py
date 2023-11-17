import requests

class LogglyConnection(object):

    def __init__(self, token):
        self.base_url = f"http://logs-01.loggly.com/inputs/{token}/tag/http/"
    def _loggly_post(self, post_data):
        try:
            headers = {'Content-type': 'text/plain'}
            requests.post(
                url=self.base_url,
                data=post_data,
                headers=headers)
        except Exception as e:
            print(f"Exception during logging {e}")
    def create_input(self, message):
        self._loggly_post(message)

