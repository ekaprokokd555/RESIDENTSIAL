import boto3
import time
import paramiko
import json

# AWS Credentials
AWS_ACCESS_KEY = 'your-aws-access-key'
AWS_SECRET_KEY = 'your-aws-secret-key'
REGION_NAME = 'us-east-1'  # Ganti dengan region pilihan kamu

# Luminati API Credentials
LUMINATI_USERNAME = 'brd-customer-hl_547a0507-zone-residential_proxy1'
LUMINATI_PASSWORD = 'tz9rox7m97if'

# Nama Key Pair untuk EC2 instance
KEY_PAIR_NAME = 'PEH.pem'

# Nama instance EC2 dan jenis
INSTANCE_TYPE = 't2.micro'
AMI_ID = 'ami-0e2c8caa4b6378d8c'  # Ubuntu 20.04 LTS AMI ID (periksa sesuai region kamu)

# Inisialisasi boto3 client
ec2_client = boto3.client(
    'ec2', 
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME
)

# Membuat EC2 instance
def create_ec2_instance():
    print("Creating EC2 instance...")
    response = ec2_client.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        KeyName=KEY_PAIR_NAME,
        SecurityGroups=['sg-0a9cbad48c2b3455f'],
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"EC2 instance {instance_id} is being created...")
    return instance_id

# Menunggu EC2 instance siap
def wait_for_instance(instance_id):
    print("Waiting for instance to be running...")
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print(f"Instance {instance_id} is running.")
    return instance_id

# Mendapatkan public IP EC2 instance
def get_instance_public_ip(instance_id):
    instance = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"Public IP of EC2 instance: {public_ip}")
    return public_ip

# Mengonfigurasi Squid Proxy di EC2 instance
def configure_squid_proxy(public_ip):
    print("Configuring Squid Proxy...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh_client.connect(public_ip, username='ubuntu', key_filename=KEY_PAIR_NAME)
    
    # Update dan install Squid
    commands = [
        "sudo apt update && sudo apt upgrade -y",
        "sudo apt install squid -y",
    ]
    
    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print(stdout.read().decode())
    
    # Mengonfigurasi Squid untuk menerima koneksi
    squid_conf = """
    http_port 3128
    acl allowed_ips src 0.0.0.0/0
    http_access allow allowed_ips
    """
    
    # Update konfigurasi Squid
    stdin, stdout, stderr = ssh_client.exec_command('echo "{}" | sudo tee /etc/squid/squid.conf'.format(squid_conf))
    print(stdout.read().decode())
    
    # Restart Squid untuk menerapkan konfigurasi baru
    stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl restart squid")
    print(stdout.read().decode())
    
    ssh_client.close()

# Mengonfigurasi Luminati Proxy (Bright Data) untuk digunakan pada Squid
def configure_luminati_proxy():
    # Format proxy url untuk Luminati
    luminati_proxy = f"http://{LUMINATI_USERNAME}-country-us:{LUMINATI_PASSWORD}@zproxy.luminati.io:22225"
    print(f"Using Luminati Proxy: {luminati_proxy}")

    # Mengonfigurasi Squid untuk menggunakan proxy Luminati sebagai upstream proxy
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(public_ip, username='ubuntu', key_filename=PEH)

    luminati_config = f"""
    cache_peer zproxy.luminati.io parent 22225 0 no-query default
    never_direct allow all
    """

    # Menambahkan konfigurasi Luminati ke Squid
    stdin, stdout, stderr = ssh_client.exec_command(f"echo '{luminati_config}' | sudo tee -a /etc/squid/squid.conf")
    print(stdout.read().decode())

    # Restart Squid untuk menerapkan perubahan
    stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl restart squid")
    print(stdout.read().decode())

    ssh_client.close()

if __name__ == "__main__":
    # Step 1: Create EC2 instance
    instance_id = create_ec2_instance()

    # Step 2: Wait for EC2 instance to be ready
    instance_id = wait_for_instance(instance_id)

    # Step 3: Get EC2 public IP
    public_ip = get_instance_public_ip(instance_id)

    # Step 4: Configure Squid Proxy
    configure_squid_proxy(public_ip)

    # Step 5: Configure Luminati Proxy
    configure_luminati_proxy()

    print(f"Proxy is now running on {public_ip}:3128 and using Luminati as upstream proxy.")
