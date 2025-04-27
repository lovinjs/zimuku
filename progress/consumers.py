import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .utils.generate_zimuku import GenerateZimuku


class ProgressConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name = 'progress'

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        type = text_data_json['type']
        content = text_data_json['content']

        if type == 'startProcess':
            print('startProcess:')
            generate_zimuku = GenerateZimuku(content, websocket=self)
            generate_zimuku.generate_zimuku_task()
        else:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'heart',
                    'content': content
                }
            )

    def heart(self, event):
        print(event)
        content = event['content']

        self.send(text_data=json.dumps({
            'type': 'heart',
            'content': content
        }))
