import pytest
from server_manager import ServerManager


@pytest.fixture(scope="session")
def server():
    with ServerManager() as sm:
        yield sm
        print("\n" + "="*50)
        print("SERVER LOGS")
        print("="*50)
        sm.print_logs()


@pytest.fixture
def base_url(server):
    return server.get_base_url()
