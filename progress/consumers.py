import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .utils.generate_zimuku import GenerateZimuku


class ProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'progress'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        type = text_data_json['type']
        content = text_data_json['content']

        if type == 'startProcess':
            print('startProcess:')
            generate_zimuku = GenerateZimuku(content, websocket=self)
            await generate_zimuku.generate_zimuku_task()
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'heart',
                    'content': content
                }
            )

    async def heart(self, event):
        print(event)
        content = event['content']

        self.send(text_data=json.dumps({
            'type': 'heart',
            'content': content
        }))
