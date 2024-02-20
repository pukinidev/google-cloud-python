from google.cloud import compute_v1
from google.cloud import resourcemanager_v3
from collections import defaultdict
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
instace_client = compute_v1.InstancesClient()
firewall_client = compute_v1.FirewallsClient()
health_client = compute_v1.HealthChecksClient()
request = compute_v1.AggregatedListInstancesRequest()

PROYECT = 'isis2503-monitoria'

def get_project(project_id):
    client = resourcemanager_v3.ProjectsClient()

    request = resourcemanager_v3.GetProjectRequest(
        name=f'projects/{project_id}',
    )
    response = client.get_project(request=request)
        
    if response.project_id == project_id:
        return response.project_id
    else:
        return "Project ID not found!"


# Get IP(Internal and External) from Virtual Machines
def get_ips_instances(request, instace_client):
    request.project = PROYECT
    agg_list = instace_client.aggregated_list(request=request)
    instances_found = agg_list.get("zones/us-central1-a").instances
    instances = {}
    for instance in instances_found:
        ipsettings = {}
        ipsettings["internal_ip"] = instance.network_interfaces[0].network_i_p
        if instance.network_interfaces[0].access_configs[0].nat_i_p != '':
            ipsettings["external_ip"] = instance.network_interfaces[0].access_configs[0].nat_i_p
        instances[instance.name] = ipsettings
    return instances

# Start All Virtual Machines
def start_vm(request, instace_client):
    request.project = PROYECT
    for instance in instace_client.aggregated_list(request=request).get("zones/us-central1-a").instances:
        instace_client.start(project=PROYECT,
                             zone='us-central1-a', instance=instance.name)

# Start Virtual Machine by Name
def start_vm_by_name(request, instace_client, name):
    request.project = PROYECT
    instace_client.start(project=PROYECT,
                         zone='us-central1-a', instance=name)

# Stops All Virtual Machines
def stop_vm(request, instace_client):
    request.project = PROYECT
    for instance in instace_client.aggregated_list(request=request).get("zones/us-central1-a").instances:
        instace_client.stop(project=PROYECT,
                            zone='us-central1-a', instance=instance.name)

# Stops Virtual Machine by Name
def stop_vm_by_name(request, instace_client, name):
    request.project = PROYECT
    instace_client.stop(project=PROYECT,
                        zone='us-central1-a', instance=name)

# Get All Virtual Machines (Information)
def get_all_instances(request, instace_client):
    request.project = PROYECT
    agg_list = instace_client.aggregated_list(request=request)
    all_instances = defaultdict(list)
    for zone, response in agg_list:
        if response.instances:
            all_instances[zone].extend(response.instances)
            print(f" {zone}:")
            for instance in response.instances:
                return instance

# Create a VM
def create_vm(name, tag, instace_client):

    """
    :param name: Name of the VM
    :param tag: Tag of the VM
    :param instace_client: Instance Client
    """

    INSTANCE_NAME = name
    MACHINE_TYPE = 'projects/isis2503-monitoria/zones/us-central1-a/machineTypes/e2-micro'
    SUBNETWORK = 'projects/isis2503-monitoria/regions/us-central1/subnetworks/default'
    SOURCE_IMAGE = 'projects/ubuntu-os-cloud/global/images/ubuntu-2004-focal-v20230907'

    NETWORK_INTERFACE = {
        'subnetwork': SUBNETWORK,
        'access_configs': [
            {
                'name': 'External NAT'
            }

        ],
        "stackType": "IPV4_ONLY",
    }

    config = {
        'name': INSTANCE_NAME,
        'machine_type': MACHINE_TYPE,
        'disks': [
            {
                'boot': True,
                'auto_delete': True,
                'initialize_params': {
                    'source_image': SOURCE_IMAGE,
                    'disk_size_gb': '10',
                    'disk_type': "projects/isis2503-monitoria/zones/us-central1-a/diskTypes/pd-standard"
                },
                "mode": "READ_WRITE",
                "type": "PERSISTENT",

            }
        ],

        'network_interfaces': [NETWORK_INTERFACE],

        "tags": {
            "items": [
                tag,
            ]
        },
    }

    print("Creating instace.....")
    operation = instace_client.insert(
        project=PROYECT,
        zone='us-central1-a',
        instance_resource=config
    )

    operation.result()

# Create Firewall Rule
def create_firewall_rule(name, destiny_tag, port, filter,firewall_client):

    """
    :param name: Name of the firewall rule
    :param destiny_tag: Tag of the VM that will receive the rule
    :param port: Port that will be opened
    :param filter: Type of filter (ranges or tags)
    :param firewall_client: Firewall Client
    
    """

    config = {
        "name": name,
        "self_link": "projects/isis2503-monitoria/global/firewalls",
        "network": "projects/isis2503-monitoria/global/networks/default",
        "direction": "INGRESS",
        "priority": 1000,
        "target_tags": [
            destiny_tag
        ],
        "allowed": [
            {
                "I_p_protocol": "tcp",
                "ports": [
                    port
                ]
            }
        ],
    }

    match filter:
        case "ranges":
            source_range = input("Enter the source range: ")
            config["source_ranges"] = [source_range]
        case "tags":
            source_tag = input("Enter the source tag: ")
            config["source_tags"] = [source_tag]
            
    operation = firewall_client.insert(
        project=PROYECT,
        firewall_resource=config
    )

    operation.result()


# Create Health Check 
def create_health_check(name, health_client):

    config = {
        "name": name,
        "type_": "HTTP",
        "check_interval_sec": 5,
        "healthy_threshold": 2,
        "unhealthy_threshold": 2,
        "timeout_sec": 5,
        "http_health_check":{
            "host": "",
            "port": 80,
            "proxy_header": "NONE",
            "request_path": "/",
            "response": "",
        }
    }
    
    operation = health_client.insert(
        project='isis2503-monitoria',
        health_check_resource=config
    )

    operation.result()

# Create group instances

def create_group_instances():
    pass

# Create Load Balancer