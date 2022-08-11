from cdip_connector.core.portal_api import PortalApi
class TestPortalApi():

    def test_create(self):
        p = PortalApi()
        assert p is not None