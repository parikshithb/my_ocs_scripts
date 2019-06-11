import logging
from pdb import set_trace
import yaml
from kubernetes import client, config
from openshift.dynamic import DynamicClient
from ocs.defaults import ROOK_CLUSTER_NAMESPACE
from ocs import ocp, pod

k8s_client = config.new_client_from_config()
dyn_client = DynamicClient(k8s_client)

log = logging.getLogger(__name__)


def create_block_pool(client, pool_name, replication_size, namespace):
    """

    :param client:
    :param poolname:
    :param size:
    :param namespace:
    :return:
    """
    pool_body = (
        f"""
        apiVersion: ceph.rook.io/v1
        kind: CephBlockPool
        metadata:
          name: {pool_name}
          namespace: {namespace}
        spec:
          # The failure domain will spread the replicas of the data across different failure zones
          failureDomain: host
          # For a pool based on raw copies, specify the number of copies. A size of 1 indicates no redundancy.
          replicated:
            size: {replication_size}
          # A key/value list of annotations
          annotations:
          #  key: value
        """
    )
    pool_dict = yaml.safe_load(pool_body)
    log.info(f"Creating a new Replicated pool")
    ret = client.create(body=pool_dict)
    set_trace()
    log.info(f"Returned value is:\n{ret}")
    return ret


def create_secret(client, admin):
    """

    :param client:
    :return:
    """

    secret_body = (
        f"""
        apiVersion: v1
        kind: Secret
        metadata:
          name: csi-rbd-secret
          namespace: default
        data:
          # Key value corresponds to a user name defined in Ceph cluster
          admin: {admin}
          # Key value corresponds to a user name defined in Ceph cluster
          #kubernetes: BASE64-ENCODED-PASSWORD
          # if monValueFromSecret is set to "monitors", uncomment the
          # following and set the mon there
          #monitors: BASE64-ENCODED-Comma-Delimited-Mons
        """
    )
    secret_dict = yaml.safe_load(secret_body)
    log.info(f"Creating secret")
    ret = client.create(body=secret_dict)
    set_trace()
    log.info(f"Returned value is:\n{ret}")
    return ret


def create_storagecalss(client, monitors, pool_name, sc_name):
    sc_body = (
        f"""
        apiVersion: storage.k8s.io/v1
        kind: StorageClass
        metadata:
           name: {sc_name}
        provisioner: rbd.csi.ceph.com
        parameters:
            # Comma separated list of Ceph monitors
            # if using FQDN, make sure csi plugin's dns policy is appropriate.
            monitors: {monitors}:6789

            # if "monitors" parameter is not set, driver to get monitors from same
            # secret as admin/user credentials. "monValueFromSecret" provides the
            # key in the secret whose value is the mons
            #monValueFromSecret: "monitors"

            # Ceph pool into which the RBD image shall be created
            pool: {pool_name}

            # RBD image format. Defaults to "2".
            imageFormat: "2"

            # RBD image features. Available for imageFormat: "2". CSI RBD currently supports only `layering` feature.
            imageFeatures: layering

            # The secrets have to contain Ceph admin credentials.
            csi.storage.k8s.io/provisioner-secret-name: csi-rbd-secret
            csi.storage.k8s.io/provisioner-secret-namespace: default
            csi.storage.k8s.io/node-publish-secret-name: csi-rbd-secret
            csi.storage.k8s.io/node-publish-secret-namespace: default

            # Ceph users for operating RBD
            adminid: admin
            userid: kubernetes
            # uncomment the following to use rbd-nbd as mounter on supported nodes
            #mounter: rbd-nbd
        reclaimPolicy: Delete           
        """
    )
    sc_dict = yaml.safe_load(sc_body)
    log.info(f"Creating StorageClass")
    ret = client.create(body=sc_dict)
    set_trace()
    log.info(f"Returned value is:\n{ret}")
    return ret


def create_pvc(client, pvc_name, sc_name, namespace):
    pvc_body = (
        f"""
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: {pvc_name}
          namespace: {namespace}
        spec:
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 1Gi
          storageClassName: {sc_name}
        """
    )
    pvc_dict = yaml.safe_load(pvc_body)
    log.info(f"Creating PVC")
    ret = client.create(body=pvc_dict)
    set_trace()
    log.info(f"Returned value is:\n{ret}")
    return ret


def get_mon():
    OCP = ocp.OCP(
        kind='service', namespace=ROOK_CLUSTER_NAMESPACE
    )
    svc_dict = OCP.get(resource_name="rook-ceph-mon-a")
    monip = svc_dict['spec']['clusterIP']
    return monip


# def exec_cmd_on_pod(pod_name, command):
#     """
#     Execute a command on a pod (e.g. oc rsh)
#
#     Args:
#         pod_name (str): The pod on which the command should be executed
#         command (str): The command to execute on the given pod
#
#     Returns:
#         Munch Obj: This object represents a returned yaml file
#     """
#     cmd_pod_obj = ocp.OCP(kind='pods', namespace=ROOK_CLUSTER_NAMESPACE)
#     rsh_cmd = f"rsh {pod_name} "
#     rsh_cmd += command
#     return cmd_pod_obj.exec_oc_cmd(rsh_cmd)
#
#
# def get_ceph_tools_pod():
#     """
#     Get the Ceph tools pod
#
#     Returns:
#         str: The Ceph tools pod name
#     """
#     ocp_pod_obj = ocp.OCP(kind='pods', namespace=ROOK_CLUSTER_NAMESPACE)
#     ct_pod = ocp_pod_obj.get(resource_name='-l app=rook-ceph-tools').toDict()['items'][0]['metadata']['name']
#     return ct_pod
#

def get_client_admin():
    # """
    #        Execute a Ceph command on the Ceph tools pod
    #
    #        Args:
    #            ceph_cmd (str): The Ceph command to execute on the Ceph tools pod
    #
    #        Returns:
    #            dict: Ceph command output
    #        """
    # # ocp_pod_obj = ocp.OCP(kind='pods', namespace=ROOK_CLUSTER_NAMESPACE)
    # ct_pod = get_ceph_tools_pod()
    # ceph_cmd = "ceph auth get-key client.admin | base64"
    # exec_cmd_on_pod(ct_pod, ceph_cmd).toDict()
    # log.info(a)


    config.load_kube_config()
    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces(
        watch=False,
        label_selector='app=rook-ceph-tools'
    )

    for i in ret.items:
        namespace = i.metadata.namespace
        name = i.metadata.name
        break

    cmd = "ceph auth get-key client.admin | base64"
    po = pod.Pod(name, namespace)

    out, err, ret = po.exec_command(cmd=cmd, timeout=20)
    if out:
        print(out)
        return out.rstrip('\n')
    if err:
        print(err)
    print(ret)


def run(**kwargs):
    """

    :param kwargs:
    :return:
    """
    pool_name = 'mypool'
    size = '2'
    # admin = 'QVFDRnd1ZGNGY1BTR1JBQWcwWmpmMGVQTnpSS1NZdE1SMlZJS0E9PQ=='
    sc_name = 'csi-rbd'
    pvc_name = 'my-pvc'

    replicated_pool_resource = dyn_client.resources.get(api_version='v1', kind='CephBlockPool')
    secret_resource = dyn_client.resources.get(api_version='v1', kind='Secret')
    storageclass_resource = dyn_client.resources.get(api_version='v1', kind='StorageClass')
    pvc_resource = dyn_client.resources.get(api_version='v1', kind='PersistentVolumeClaim')

    set_trace()
    create_block_pool(client=
                      replicated_pool_resource, pool_name=pool_name, replication_size=size,
                      namespace=ROOK_CLUSTER_NAMESPACE
                      )
    create_secret(client=secret_resource, admin=get_client_admin(),
                  )
    create_storagecalss(client=storageclass_resource, monitors=get_mon(),
                        pool_name=pool_name, sc_name=sc_name)
    create_pvc(client=pvc_resource, pvc_name=pvc_name, sc_name=
    sc_name, namespace=ROOK_CLUSTER_NAMESPACE)
