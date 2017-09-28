
from utils.dockerutil import DockerUtil
from .baseutil import BaseUtil


class DockerUtilProxy(BaseUtil):
    def get_container_tags(self, cid=None, co=None):
        return None  # Docker tags are fetched directly

    @staticmethod
    def is_detected():
        try:
            if "Version" in DockerUtil().client.version():
                return True
            else:
                return False
        except Exception:
            return False

    def get_host_tags(self):
        return self.docker_util.get_host_tags()
