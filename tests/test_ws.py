from gtagoraapp.details.ws import AgoraWebsocket


class TestWs:
    def test_parse_version(self):
        version_str = '1.2.5'
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 1
        assert version['minor'] == 2
        assert version['path'] == 5
        assert version['snapshot'] is False
        assert version['string'] == version_str

        version_str = '9.3.2-SNAPSHOT'
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 9
        assert version['minor'] == 3
        assert version['path'] == 2
        assert version['snapshot'] is True
        assert version['string'] == version_str

        version_str = '2.1'
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 2
        assert version['minor'] == 1
        assert version['path'] == 0
        assert version['snapshot'] is False
        assert version['string'] == version_str

        version_str = '2'
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 2
        assert version['minor'] == 0
        assert version['path'] == 0
        assert version['snapshot'] is False
        assert version['string'] == version_str

        version_str = '2.1 SNAPSHOT'
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 2
        assert version['minor'] == 1
        assert version['path'] == 0
        assert version['snapshot'] is True
        assert version['string'] == version_str

        version_str = '    0.1.2     '
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 0
        assert version['minor'] == 1
        assert version['path'] == 2
        assert version['snapshot'] is False
        assert version['string'] == version_str

        version_str = '    0.1.2   adasdas  '
        version = AgoraWebsocket.parse_version(version_str)
        assert version['major'] == 0
        assert version['minor'] == 1
        assert version['path'] == 2
        assert version['snapshot'] is False
        assert version['string'] == version_str
