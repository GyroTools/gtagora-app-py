import asyncio
import json
import os
import platform
import socket
import _thread
from pathlib import Path
from urllib.parse import urlparse

import pkg_resources
import websockets
from websockets.http import Headers

from gtagoraapp.details.settings import Settings

class AgoraWebsocketMessage:
    def __init__(self, data: dict):
        self.msg = dict()
        self.msg['stream'] = 'App'
        self.msg['data'] = data

    def __str__(self):
        return json.dumps(self.msg)


class AgoraWebsocket:
    def __init__(self, settings: Settings, handler):
        self.settings = settings
        self.handler = handler
        uri = urlparse(self.settings.server)
        self.uri = 'ws://' + uri.hostname
        if uri.port:
            self.uri = f'{self.uri}:{uri.port}'

        self.ping_data = self._get_ping_data()

        self.ping_timeout = 10
        self.timout = 10
        self.sleep_time = 30

        self.logger = handler.logger

    def run(self):
        asyncio.get_event_loop().run_until_complete(self._listen_forever())

    async def _listen_forever(self):
        while True:
            # outer loop restarted every time the connection fails
            try:
                headers = Headers()
                headers['Authorization'] = f'Token {self.settings.session_key}'
                async with websockets.connect(self.uri, extra_headers=headers) as ws:
                    self.logger.info(f'Websocket established with {self.uri}')
                    self.logger.debug(f'Ping response: {json.dumps(self.ping_data)}')
                    await ws.send(str(AgoraWebsocketMessage(self.ping_data)))
                    self.logger.info(f'App is running --> listening for server messages...')
                    while True:
                        # listener loop
                        try:
                            msg = await ws.recv()
                        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                            try:
                                self.logger.warning(f'Connection probably closed (sending ping): {str(e)}')
                                pong = await ws.ping()
                                await asyncio.wait_for(pong, timeout=self.ping_timeout)
                                continue
                            except:
                                self.logger.warning(f'Connection closed (trying again in {self.sleep_time}s): {str(e)}')
                                await asyncio.sleep(self.sleep_time)
                                break  # inner loop
                        asyncio.create_task(self._process_message(msg, ws))
            except socket.gaierror as e:
                self.logger.warning(f'Connection closed: {str(e)}')
                self.logger.warning(f'Trying to reconnect')
                continue
            except ConnectionRefusedError as e:
                self.logger.warning(f'Connection refused: {str(e)}')
                self.logger.warning(f'Trying to reconnect')
                continue

    async def _process_message(self, msg_str, ws):
        try:
            msg = json.loads(msg_str)
            data = msg.get('data')
            stream = msg.get('stream')
            if stream == 'App' and data and self._i_am_receiver(msg):
                command = data.get('command')
                if command == 'hello':
                    self.logger.info(f'Received Hello --> sending ping response')
                    self.logger.debug(f'Ping response: {json.dumps(self.ping_data)}')
                    await ws.send(str(AgoraWebsocketMessage(self.ping_data)))
                if command == 'download' and 'data' in data:
                    download_data = data['data']
                    _thread.start_new_thread(self.handler.download, (download_data.get('files'),))
                if command == 'runTask' and 'data' in data:
                    task_data = data['data']
                    _thread.start_new_thread(self.handler.runTask, (task_data,))
        except:
            pass


    def _i_am_receiver(self, msg):
        receiver = msg.get('receiver')
        if not receiver or receiver == self.settings.app_id:
            return True

        return False


    def _get_ping_data(self):
        system = 'unknown'
        operating_system = platform.system()
        if operating_system == 'Linux' or operating_system == 'Darwin':
            system = 'unix'
        elif operating_system == 'Windows':
            system = 'windows'

        # TODO:
        #version_str = pkg_resources.require("gt-agora-app")[0].version
        version_str = '1.0.0-SNAPSHOT'

        # TODO:
        version_split = version_str.split('-')
        version_split = version_split[0].split('.')
        version = dict()
        version['major'] = int(version_split[0])
        version['minor'] = int(version_split[1])
        version['path'] = int(version_split[2])
        version['snapshot'] = True
        version['string'] = version_str

        command_data = dict()
        command_data['appId'] = self.settings.app_id
        command_data['base_path'] = Path(self.settings.download_path).as_posix()
        command_data['computerName'] = platform.node()
        command_data['path_separator'] = os.path.sep
        command_data['system'] = system
        command_data['version'] = version


        data = dict()
        data['command'] = 'ping'
        data['data'] = command_data

        return data
