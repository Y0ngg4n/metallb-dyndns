import kubernetes
from kubernetes import client, config
import dns.resolver
import ipaddr


def check_public_ip():
    my_resolver = dns.resolver.Resolver()
    # Cloudflares DNS Server
    my_resolver.nameservers = ['2606:4700:4700::1111']
    # Get IP from cloudflare chaosnet TXT record
    # https://community.cloudflare.com/t/can-1-1-1-1-be-used-to-find-out-ones-public-ip-address/14971/6
    result = my_resolver.resolve("whoami.cloudflare", "TXT", "CH", tcp=True, lifetime=15)
    response = result.response
    answer = response.answer
    ExternalIP = str(list(answer[0])[0]).replace('"', '')
    return getIPv6Prefix(ExternalIP, 128)


# Returns the IPv6 prefix
def getIPv6Prefix(ipv6Addr, prefixLen):
    prefix = ""
    curPrefixLen = 0
    ipv6Parts = ipv6Addr.split(":")
    for part in ipv6Parts:
        if not prefix == "":  # if it's not empty
            prefix = prefix + ":"
        prefix = prefix + part
        curPrefixLen += 32
        if int(curPrefixLen) >= int(prefixLen):
            return prefix
    return prefix


def getIPv6Interface(ipv6Addr, interfaceLen):
    interface = ""
    curPrefixLen = 0
    ipv6Parts = ipv6Addr.split(":")
    for part in ipv6Parts:
        if curPrefixLen < 256 - interfaceLen:
            curPrefixLen += 32
            continue
        if not interface == "":  # if it's not empty
            interface = interface + ":"
        interface = interface + part
        curPrefixLen += 32
        if int(curPrefixLen) >= int(256):
            return interface
    return interface


def patchMetallb(new_prefix):
    configuration = config.load_kube_config(config_file="/home/yonggan/Nextcloud/Yggdrasil/NewKubernetes/kubeconfig")
    with kubernetes.client.ApiClient(configuration) as api_client:
        api_instance = kubernetes.client.CustomObjectsApi(api_client)
        # print(api_instance.get_api_resources(group="metallb.io", version="v1beta1"))
        ipPool = api_instance.get_namespaced_custom_object(group="metallb.io", version="v1beta1",
                                                           namespace="system", name="pool-1",
                                                           plural="ipaddresspools")
        adresses = ipPool["spec"]["addresses"]
        newAdresses = []
        for adress in adresses:
            range = adress.split("-")
            if adress.find(":") == -1:
                newAdresses.append(adress)
            else:
                first_old_interface = getIPv6Interface(range[0], 128)
                second_old_interface = getIPv6Interface(range[1], 128)
                newAdresses.append(new_prefix + first_old_interface + "-" + new_prefix + second_old_interface)
        print(newAdresses)



if __name__ == '__main__':
    prefix = check_public_ip()
    patchMetallb(prefix)
