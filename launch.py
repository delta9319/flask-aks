import re
from py_linq import Enumerable
import argparse

from kubernetes import client, config
from kubernetes.client.models import (
    V1Pod,
    V1ObjectMeta,
    V1Container,
    V1PodSpec,
    V1ContainerPort,
    V1Deployment,
    V1DeploymentSpec,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1Service,
    V1ServiceSpec,
    V1ServicePort,
    V1ResourceRequirements,
)


config.load_kube_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


class K8sKeyValue:
    def __init__(self, key: str, value: str = None, printable_value: str = None):
        self.key = key
        self.value = value
        self.printable_value = printable_value if printable_value else value

    def __iter__(self):
        return iter([self])


class AdminAKSCluster:
    def __init__(
        self,
        image_name="flask-helloworld",
        image_tag="v1",
        image_secret=None,
        namespace="default",
        mem_min="64Mi",
        mem_max="128Mi",
        job_max_age=None,
        job_delete_wait=None,
        msg_name="Kubernetes",
    ):
        self.acr = "admincr.azurecr.io"
        self.image_name = image_name
        self.image_tag = image_tag
        self.image_secret = image_secret
        self.namespace = namespace
        self.mem_min = mem_min
        self.mem_max = mem_max
        self.job_max_age = job_max_age
        self.job_delete_wait = job_delete_wait
        self.msg_name = msg_name

    def get_k8s_memory_directive(self, mem):
        mem = re.sub(r"[mM]$", "Mi", mem)
        mem = re.sub(r"[gG]$", "Gi", mem)
        return mem

    def get_k8s_resource_requirements(self, mem):
        reqs = {}
        if mem:
            reqs = {"memory": self.get_k8s_memory_directive(mem)}
        return reqs

    def get_namespaces(self):
        ret = v1.list_namespace(watch=False)
        for i in ret.items:
            print("%s\t%s" % (i.metadata.name, i.status.phase))

    def get_all_pods(self):
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            print(
                "%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name)
            )

    def get_pods_by_namespace(self, namespace):
        ret = v1.list_namespaced_pod(namespace)
        for i in ret.items:
            print(
                "%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name)
            )

    def get_services_by_namespace(self, namespace):
        ret = v1.list_namespaced_service(namespace)
        for i in ret.items:
            if i.status.load_balancer.ingress:
                print(
                    "%s\t%s" % (i.status.load_balancer.ingress[0].ip, i.metadata.name)
                )

    def create_pod(self):
        image_pull_secrets = []
        if self.image_secret:
            image_pull_secrets += [
                client.V1LocalObjectReference(name=self.image_secret)
            ]

        image = f"{self.acr}/{self.image_name}:{self.image_tag}"
        container_env = Enumerable(
            [
                K8sKeyValue(
                    key="MSG_NAME",
                    value=self.msg_name,
                    printable_value=self.msg_name,
                ),
            ]
        )
        resources = V1ResourceRequirements(
            limits=self.get_k8s_resource_requirements(self.mem_max),
            requests=self.get_k8s_resource_requirements(self.mem_min),
        )
        pod = V1Pod(
            metadata=V1ObjectMeta(
                name=f"{self.image_name}-pod", labels={"app": f"app-{self.image_name}"}
            ),
            spec=V1PodSpec(
                restart_policy="Never",
                image_pull_secrets=image_pull_secrets,
                containers=[
                    V1Container(
                        name=f"container-{self.image_name}",
                        image=image,
                        ports=[V1ContainerPort(container_port=5000)],
                        env=container_env.select(
                            lambda e: client.V1EnvVar(name=e.key, value=e.value)
                        ).to_list(),
                        resources=resources,
                    )
                ],
            ),
        )
        v1.create_namespaced_pod(namespace=self.namespace, body=pod)
        print(f"{self.image_name}-pod deployed.")

    def create_service(self):
        service = V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(
                name=f"{self.image_name}-svc", labels={"app": f"app-{self.image_name}"}
            ),
            spec=V1ServiceSpec(
                type="LoadBalancer",
                ports=[V1ServicePort(port=80, protocol="TCP", target_port=5000)],
                selector={"app": f"app-{self.image_name}"},
            ),
        )
        v1.create_namespaced_service(namespace=self.namespace, body=service)
        print(f"{self.image_name}-svc created.")

    def create_deployment(self):
        image = f"{self.acr}/{self.image_name}:{self.image_tag}"
        deployment = V1Deployment(
            api_version="v1",
            kind="Deployment",
            metadata=V1ObjectMeta(name="flask-dep", labels={"app": "flask-helloworld"}),
            spec=V1DeploymentSpec(
                replicas=2,
                selector=V1LabelSelector(match_labels={"app": "flask-helloworld"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "flask-helloworld"}),
                    spec=V1PodSpec(
                        containers=[
                            V1Container(
                                name="flask",
                                image=image,
                                ports=[V1ContainerPort(container_port=5000)],
                            )
                        ]
                    ),
                ),
            ),
        )
        apps_v1.create_namespaced_deployment(namespace=self.namespace, body=deployment)


if __name__ == "__main__":
    # initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument("-i", "--image_name", help="Image Name")
    parser.add_argument("-t", "--image_tag", help="Image Tag")
    parser.add_argument("-s", "--image_secret", help="Image Secret")
    parser.add_argument("-n", "--namespace", help="Namespace")
    parser.add_argument("-mmin", "--mem_min", help="Minimum Memory")
    parser.add_argument("-mmax", "--mem_max", help="Max Memory")
    parser.add_argument("-m", "--msg_name", help="Message")
    # Read arguments from command line
    args = parser.parse_args()

    cluster = AdminAKSCluster(
        image_name=args.image_name,
        image_tag=args.image_tag,
        image_secret=args.image_secret,
        namespace=args.namespace,
        mem_min=args.mem_min,
        mem_max=args.mem_max,
        msg_name=args.msg_name,
    )

    cluster.create_pod()
    cluster.get_pods_by_namespace("default")
    cluster.create_service()
    cluster.get_services_by_namespace("default")
