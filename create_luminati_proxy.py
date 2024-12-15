import boto3
import paramiko
import time

# Konfigurasi AWS
aws_region = 'us-east-1'  # Ganti dengan region yang sesuai
ami_id = 'ami-0e2c8caa4b6378d8c'  # Ganti dengan ID AMI (misalnya Ubuntu 20.04)
instance_type = 't2.micro'  # Pilih tipe instance yang sesuai
key_name = 'PEH'  # Ganti dengan nama key pair AWS Anda
security_group = 'sg-0a9cbad48c2b3455f'  # Ganti dengan security group yang sesuai
instance_name = 'Proxy-Residensial-EC2'

# Konfigurasi Luminati (Bright Data)
LUMINATI_USERNAME = 'brd-customer-hl_547a0507-zone-residential_proxy1'
LUMINATI_PASSWORD = 'tz9rox7m97if'

# AMI ID untuk Ubuntu 20.04 LTS (dapat berbeda sesuai region)
AMI_ID = 'ami-0e2c8caa4b6378d8c'  # Pastikan ini sesuai dengan region yang kamu pilih
INSTANCE_TYPE = 't2.micro'  # Tipe instance EC2

# Membuat koneksi ke AWS
ec2_client = boto3.client(
    'ec2',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME
)

# Fungsi untuk membuat EC2 instance
def create_instance():
    response = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=[security_group],
        SubnetId=subnet_id,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': instance_name}]
        }]
    )

    instance_id = response['Instances'][0]['InstanceId']
    print(f"Instance created: {instance_id}")
    return instance_id

# Fungsi untuk menunggu instance EC2 siap
def wait_for_instance(instance_id):
    print("Menunggu instance untuk siap...")
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print(f"Instance EC2 dengan ID {instance_id} sudah berjalan.")
    return instance_id

# Mendapatkan IP publik instance EC2
def get_instance_public_ip(instance_id):
    instance = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"IP publik EC2 instance: {public_ip}")
    return public_ip

# Fungsi untuk mengonfigurasi Squid Proxy di EC2
def configure_squid_proxy(public_ip):
    print("Mengonfigurasi Squid Proxy...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(public_ip, username='ubuntu', key_filename=KEY_PAIR_NAME)
    
    # Update sistem dan install Squid
    commands = [
        "sudo apt update && sudo apt upgrade -y",
        "sudo apt install squid -y"
    ]
    
    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print(stdout.read().decode())
    
    # Konfigurasi Squid untuk menerima koneksi
    squid_conf = """
    http_port 3128
    acl allowed_ips src 0.0.0.0/0
    http_access allow allowed_ips
    """
    
    # Update konfigurasi Squid
    stdin, stdout, stderr = ssh_client.exec_command(f'echo "{squid_conf}" | sudo tee /etc/squid/squid.conf')
    print(stdout.read().decode())
    
    # Restart Squid untuk menerapkan perubahan
    stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl restart squid")
    print(stdout.read().decode())
    
    ssh_client.close()

# Fungsi untuk mengonfigurasi Luminati Proxy di Squid
def configure_luminati_proxy(public_ip):
    print("Mengonfigurasi Luminati Proxy...")
    
    # Format URL untuk Luminati Proxy
    luminati_proxy = f"http://{LUMINATI_USERNAME}-country-us:{LUMINATI_PASSWORD}@zproxy.luminati.io:22225"
    print(f"Pengaturan proxy Luminati: {luminati_proxy}")
    
    # SSH ke EC2 dan konfigurasi Squid untuk menggunakan Luminati sebagai proxy upstream
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(public_ip, username='ubuntu', key_filename=KEY_PAIR_NAME)

    luminati_config = f"""
    cache_peer zproxy.luminati.io parent 22225 0 no-query default
    never_direct allow all
    """

    # Menambahkan pengaturan Luminati ke file konfigurasi Squid
    stdin, stdout, stderr = ssh_client.exec_command(f"echo '{luminati_config}' | sudo tee -a /etc/squid/squid.conf")
    print(stdout.read().decode())

    # Restart Squid untuk menerapkan perubahan
    stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl restart squid")
    print(stdout.read().decode())

    ssh_client.close()

# Fungsi utama untuk menjalankan proses
def main():
    # 1. Buat EC2 instance
    instance_id = create_ec2_instance()

    # 2. Tunggu hingga instance siap
    instance_id = wait_for_instance(instance_id)

    # 3. Dapatkan IP publik dari EC2 instance
    public_ip = get_instance_public_ip(instance_id)

    # 4. Konfigurasi Squid Proxy
    configure_squid_proxy(public_ip)

    # 5. Konfigurasi Luminati Proxy untuk digunakan Squid
    configure_luminati_proxy(public_ip)

    print(f"Proxy sekarang berjalan pada {public_ip}:3128 dan menggunakan Luminati sebagai proxy upstream.")

if __name__ == "__main__":
    main()
