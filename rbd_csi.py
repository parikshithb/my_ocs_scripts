"""
Test for creating a pvc with default RBD StorageClass - CSI
"""
import os
import base64
import pytest
from ocsci import tier1, ManageTest
from ocs import defaults
from kubernetes import client, config
from ocs import pod
import yaml
from utility import utils, templating
from ocs import ocp
from ocsci import EcosystemTest, tier1
import logging

log = logging.getLogger(__name__)

RBD_POOL_YAML = os.path.join("templates/ocs-deployment/csi/rbd", "pool.yaml")
SC_RBD_YAML = os.path.join("templates/ocs-deployment/csi/rbd",
                           "storageclass-csi-rbd.yaml")
SECRET_RBD_YAML = os.path.join("templates/ocs-deployment/csi/rbd",
                               "secret_rbd.yaml")
PVC_RBD_YAML = os.path.join("templates/ocs-deployment/csi/rbd",
                            "pvc-rbd.yaml")
TEMP_YAML_FILE = 'test_csi_rbd.yaml'

SC = ocp.OCP(
    kind='StorageClass', namespace=defaults.ROOK_CLUSTER_NAMESPACE
)
POOL = ocp.OCP(
    kind='CephBlockPool', namespace=defaults.ROOK_CLUSTER_NAMESPACE
)
SECRET = ocp.OCP(
    kind='Secret', namespace="default"
)
PVC = ocp.OCP(
    kind='PersistentVolumeClaim', namespace=defaults.ROOK_CLUSTER_NAMESPACE
)


@pytest.fixture(scope='class')
def test_fixture(request):
    """
    Create disks
    """
    self = request.node.cls

    def finalizer():
        teardown(self)
    request.addfinalizer(finalizer)
    setup(self)


def setup(self):
    """
    Setting up the environment for the test
    """
    assert create_rbd_pool(self.pool_name)
    assert validate_pool_creation(self.pool_name)
    admin_key = get_client_admin_keyring()
    assert create_secret_rbd(admin_key)


def teardown(self):
    """
    Tearing down the environment
    """
    assert delete_rbd_pool(self.pool_name)
    assert delete_secret_rbd(self.secret_name)
    assert delete_storageclass_rbd(self.sc_name)
    assert delete_pvc(self.pvc_name)

    utils.delete_file(TEMP_YAML_FILE)


def create_rbd_pool(pool_name):
    """
    Create Blockpool with default values
    """
    pool_data = {}
    pool_data['pool_name'] = pool_name
    file_y = templating.generate_yaml_from_jinja2_template_with_data(
        RBD_POOL_YAML, **pool_data
    )
    with open(TEMP_YAML_FILE, 'w') as yaml_file:
        yaml.dump(file_y, yaml_file, default_flow_style=False)
    log.info(f"Creating a new CephBlockPool with default name")
    assert POOL.create(yaml_file=TEMP_YAML_FILE)
    return True


def create_storageclass_rbd():
    """
    This Creates a default CSI StorageClass
    """
    file_y = templating.generate_yaml_from_jinja2_template_with_data(
        SC_RBD_YAML
    )
    with open(TEMP_YAML_FILE, 'w') as yaml_file:
        yaml.dump(file_y, yaml_file, default_flow_style=False)
    log.info(f"Creating a RBD StorageClass with default values")
    assert SC.create(yaml_file=TEMP_YAML_FILE)
    return True


def validate_pool_creation(pool_name):
    """
    Check whether default blockpool is created or not at ceph and as well
    OCS side

    :param pool_name:
    :return:
    """
    ceph_validate = False
    cmd = ocp.exec_ceph_cmd('ceph osd lspools')
    for item in cmd:
        if item['poolname'] == pool_name:
            log.info(f"{pool_name} pool is created successfully at CEPH side")
            ceph_validate = True
        else:
            log.error(f"{pool_name} pool failed to get created at CEPH side")
    assert POOL.get(resource_name='poolname')
    if ceph_validate:
        log.info("Pool got created successfully from Ceph and OCS side")
        return True
    else:
        return False


def validate_storageclass(sc_name):
    """
    Validate if storageClass is been created or not
    """
    assert SC.get(resource_name=sc_name)
    log.info("Rbd storageclass got created successfully")
    return True


def create_secret_rbd(admin_key):
    """
    This will create Secret file which will be used for creating StorageClass

    :return:
    """
    secret_data = {}
    secret_data['base64_encoded_admin_password'] = admin_key
    assert create_secret_rbd(**secret_data)

    file_y = templating.generate_yaml_from_jinja2_template_with_data(
        SECRET_RBD_YAML, **secret_data
    )
    with open(TEMP_YAML_FILE, 'w') as yaml_file:
        yaml.dump(file_y, yaml_file, default_flow_style=False)
    assert SECRET.create(yaml_file=TEMP_YAML_FILE)
    return True


def get_client_admin_keyring():
    """
    This will fetch client admin keyring from Ceph

    :return:
    """
    out = ocp.exec_ceph_cmd('ceph auth get-key client.admin')
    pp = out.get('key')
    admin_key_byte = base64.b64encode(pp.encode("utf-8"))
    return str(admin_key_byte, "utf-8")


def create_pvc(pvc_name):
    """
    This will create PVC with default value

    :return:
    """
    pvc_data = {}
    pvc_data['pvc_name'] = pvc_name
    file_y = templating.generate_yaml_from_jinja2_template_with_data(
        PVC_RBD_YAML, **pvc_data
    )
    with open(TEMP_YAML_FILE, 'w') as yaml_file:
        yaml.dump(file_y, yaml_file, default_flow_style=False)
    assert PVC.create(yaml_file=TEMP_YAML_FILE)
    return PVC.wait_for_resource(
        condition='Bound', resource_name=pvc_name
    )


def delete_rbd_pool(pool_name):
    log.info("Deleting Rbd pool")
    assert POOL.delete(resource_name=pool_name)
    return True


def delete_storageclass_rbd(sc_name):
    log.info("Deleting Storageclass")
    assert SC.delete(resource_name=sc_name)
    return True


def delete_secret_rbd(secret_name):
    log.info("Deleting Secret")
    assert SECRET.delete(resource_name=secret_name)
    return True


def delete_pvc(pvc_name):
    log.info("Deleting PVC")
    assert PVC.delete(resource_name=pvc_name)
    return True


@tier1
@pytest.mark.usefixtures(
    test_fixture.__name__,
)
class TestCaseOCS347(EcosystemTest):
    pool_name = "my-pool"
    pvc_name = "rbd-pvc"
    sc_name = "ocsci-csi-rbd-sc"
    secret_name = "csi-rbd-secret"

    def test_347(self):

        assert create_storageclass_rbd()
        assert validate_storageclass(self.sc_name)
        assert create_pvc(self.pvc_name)
