import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(
    AsyncWebsocketConsumer
):

    async def connect(self):

        self.room = "support_room"

        await self.channel_layer.group_add(
            self.room,
            self.channel_name
        )

        await self.accept()

    async def disconnect(
        self,
        close_code
    ):

        await self.channel_layer.group_discard(
            self.room,
            self.channel_name
        )

    async def receive(
        self,
        text_data
    ):

        data = json.loads(text_data)

        await self.channel_layer.group_send(

            self.room,

            {
                "type": "chat_message",
                "message": data["message"],
                "sender": data["sender"],
            }
        )

    async def chat_message(
        self,
        event
    ):

        await self.send(
            text_data=json.dumps(event)
        )