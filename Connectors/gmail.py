import json
import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText

class Gmail:


    def __init__(self):
        self._scopes = ['https://mail.google.com/']
        self._our_email = 'hacky1610@gmail.com'
        self._init_config()


    def _init_config(self, client_id:str):

        file = './Gmail/gmail.json.json'

        with open(file, 'r') as file:
            data = json.load(file)

        data['client_id'] = client_id

        with open(file, 'w') as file:
            json.dump(data, file, indent=2)

    def _gmail_authenticate(self):
        creds = None
        # the file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)
        # if there are no (valid) credentials availablle, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('Connectors/Gmail/gmail.json', self._scopes)
                creds = flow.run_local_server(port=0)
            # save the credentials for the next run
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)
        return build('gmail', 'v1', credentials=creds)

    def _build_message(self,destination, obj, body):
        message = MIMEText(body)
        message['to'] = destination
        message['from'] = self._our_email
        message['subject'] = obj

        return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}

    def send_mail(self,service, destination, obj, body):
        return self._service.users().messages().send(
            userId="me",
            body=self._build_message(destination, obj, body)
        ).execute()
