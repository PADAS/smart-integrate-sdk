from gundi_client import PortalApi


class TestPortalApi:
    def test_create(self):
        p = PortalApi()
        assert p is not None
