import exception
from logger import log

from completers import ClusterCompleter


class CmdTerminate(ClusterCompleter):
    """
    terminate [options] <cluster_tag> ...

    Terminate a running or stopped cluster

    Example:

        $ starcluster terminate mycluster

    This will terminate a currently running or stopped cluster tagged
    "mycluster".

    All nodes will be terminated, all spot requests (if any) will be
    cancelled, and the cluster's security group will be removed. If the
    cluster uses EBS-backed nodes then each node's root volume will be
    deleted.  If the cluster uses "cluster compute" instance types the
    cluster's placement group will also be removed.
    """
    names = ['terminate']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just terminate the cluster")

    def _terminate_cluster(self, cluster_name):
        cl = self.cm.get_cluster(cluster_name, require_keys=False)
        if not self.opts.confirm:
            action = 'Terminate'
            if cl.is_ebs_cluster():
                action = 'Terminate EBS'
        cl.terminate_cluster()

    def _terminate_manually(self, cluster_name):
        cl = self.cm.get_cluster(cluster_name, load_receipt=False,
                                 require_keys=False)
        insts = cl.cluster_group.instances()
        for inst in insts:
            log.info("Terminating %s" % inst.id)
            inst.terminate()
        cl.terminate_cluster()

    def terminate(self, cluster_name):
        try:
            self._terminate_cluster(cluster_name)
        except exception.IncompatibleCluster:
            self._terminate_manually(cluster_name)

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for cluster_name in args:
            try:
                self.terminate(cluster_name)
            except EOFError:
                print 'Interrupted, exiting...'
                return
