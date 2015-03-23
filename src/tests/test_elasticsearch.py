from testing.elasticsearch import ElasticSearchServer
import os
import tempfile
import requests
import pytest


# Set this up and tear it down for every function in this test so that we don't
# accidentally have an elasticsearch server running when we mean to close it
# down.
@pytest.fixture(scope='function')
def elasticsearch(request):
    """
    A testing fixture that utilizes manually starting and stopping the elasticsearch
    server.
    """
    es = ElasticSearchServer()
    es.start()
    request.addfinalizer(es.stop)
    return es


def test_elasticsearch_context():
    """
    Verify that using the elasticsearch server as a context block sets up and
    tears down as expected.
    """
    es = ElasticSearchServer()

    with pytest.raises(requests.exceptions.InvalidSchema):
        # invalid dsn
        requests.get(es.dsn())

    previous_dsn = None
    with es as es:
        dsn = es.dsn()
        result = requests.get('http://' + dsn)
        assert result.status_code == 200
        assert dsn is not None
        previous_dsn = dsn

    with pytest.raises(requests.exceptions.ConnectionError):
        # elasticsearch is no longer running
        requests.get('http://' + previous_dsn)


def test_elasticsearch_fixture(elasticsearch):
    """
    Verify that manually starting and stopping the elasticsearch server works
    as expected. This is the most likely scenario in a test scenario.
    """
    assert elasticsearch.dsn() == '%s:%s' % (elasticsearch._bind_host, elasticsearch._bind_port)

    result = requests.get('http://' + elasticsearch.dsn())
    assert result.status_code == 200


def test_elasticsearch_teardown():
    """
    Verify that temporary directories and files are cleaned up after the server
    is stopped.
    """
    es = ElasticSearchServer()
    with es as es:
        result = requests.get('http://' + es.dsn())
        assert result.status_code == 200

    assert not os.path.isdir(es._root)


def test_elasticsearch_existing_dir():
    """
    Verify that when specifying an existing root directory, no cleanup actions
    are performed.
    """
    tmp_dir = tempfile.mkdtemp(suffix='-testing-elastic')

    with ElasticSearchServer(root=tmp_dir) as es:
        result = requests.get('http://' + es.dsn())
        assert result.status_code == 200

    paths = os.listdir(tmp_dir)
    assert 'data' in paths, "elasticsearch data directory should not have been removed."
    assert os.path.isdir(os.path.join(tmp_dir, 'data'))
    assert 'logs' in paths, "elasticsearch logs directory should not have been removed."
    assert os.path.isdir(os.path.join(tmp_dir, 'logs'))
