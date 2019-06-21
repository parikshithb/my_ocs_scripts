"""
Basic test for creating PVC with default StorageClass - RBD-CSI
"""

import logging
import pytest

from ocsci.testlib import tier1, ManageTest
from tests import helpers
from ocs import constants

log = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def test_fixture(request):
    """
    This is a test fixture
    """
    def finalizer():
        teardown()
    request.addfinalizer(finalizer)
    setup()


def setup():
    """
    Setting up the environment - Creating Secret
    """
    global RBD_POOL, RBD_STORAGE_CLASS, RBD_SECRET, CEPHFS_OBJ, \
        CEPHFS_STORAGE_CLASS, CEPHFS_SECRET, RBD_PVC, CEPHFS_PVC
    log.info("Creating RBD Pool")
    RBD_POOL = helpers.create_ceph_block_pool()

    log.info("Creating RBD Secret")
    RBD_SECRET = helpers.create_secret(constants.CEPHBLOCKPOOL)

    log.info("Creating RBD StorageClass")
    RBD_STORAGE_CLASS = helpers.create_storage_class(
        constants.CEPHBLOCKPOOL, RBD_POOL.name, RBD_SECRET.name
    )

    log.info("Creating CephFilesystem")
    CEPHFS_OBJ = helpers.create_cephfilesystem()

    log.info("Creating FS Secret")
    CEPHFS_SECRET = helpers.create_secret(constants.CEPHFILESYSTEM)

    log.info("Creating FS StorageClass")
    CEPHFS_STORAGE_CLASS = helpers.create_storage_class(
        constants.CEPHFILESYSTEM, helpers.get_cephfs_data_pool_name(),
        CEPHFS_SECRET.name
    )

    log.info("Creating RBC PVC")
    RBD_PVC = helpers.create_pvc(sc_name=RBD_STORAGE_CLASS.name)

    log.info("Creating CephFs PVC")
    CEPHFS_PVC = helpers.create_pvc(sc_name=CEPHFS_STORAGE_CLASS.name)


def teardown():
    """
    Tearing down the environment
    """
    log.info("Deleting RBD Secret")
    RBD_SECRET.delete()

    log.info("Deleting RBD StorageClass")
    RBD_STORAGE_CLASS.delete()

    log.info("Deleting RBD Pool")
    RBD_POOL.delete()

    log.info("Deleting CephFS StorageClass")
    CEPHFS_STORAGE_CLASS.delete()

    log.info("Deleting CephFilesystem")
    assert helpers.delete_all_cephfilesystem()

    log.info("Deleting CephFS Secret")
    CEPHFS_SECRET.delete()

    RBD_PVC.delete()

    CEPHFS_PVC.delete()


@tier1
@pytest.mark.usefixtures(
    test_fixture.__name__,
)
class TestCaseOCS373(ManageTest):
    """
    Testing default storage class creation and pvc creation
    with default rbd pool

    https://polarion.engineering.redhat.com/polarion/#/project/
    OpenShiftContainerStorage/workitem?id=OCS-347
    """

    def test_ocs_373(self):
        log.info("test completed")
