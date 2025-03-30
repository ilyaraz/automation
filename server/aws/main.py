#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformVariable, Token
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.instance import Instance, InstanceMetadataOptions
from cdktf_cdktf_provider_aws.internet_gateway import InternetGateway
from cdktf_cdktf_provider_aws.s3_bucket import S3Bucket
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.vpc import Vpc
from cdktf_cdktf_provider_aws.iam_policy import IamPolicy
from cdktf_cdktf_provider_aws.iam_role import IamRole
from cdktf_cdktf_provider_aws.iam_instance_profile import IamInstanceProfile
from cdktf_cdktf_provider_aws.default_route_table import DefaultRouteTable, DefaultRouteTableRoute
from cdktf_cdktf_provider_aws.security_group import SecurityGroup, SecurityGroupIngress, SecurityGroupEgress 
from cdktf_cdktf_provider_aws.data_aws_ami import DataAwsAmi, DataAwsAmiFilter 
from cdktf_cdktf_provider_aws.data_aws_iam_policy_document import DataAwsIamPolicyDocument
from cdktf_cdktf_provider_aws.data_aws_s3_bucket import DataAwsS3Bucket
from cdktf_cdktf_provider_cloudinit.provider import CloudinitProvider
from cdktf_cdktf_provider_cloudinit.data_cloudinit_config import DataCloudinitConfig, DataCloudinitConfigPart
from cdktf_cdktf_provider_aws.ebs_volume import EbsVolume
from cdktf_cdktf_provider_aws.volume_attachment import VolumeAttachment
import json

AWS_REGION = 'us-west-2'
CERT_BUCKET_NAME = 'json-logger-certificates'
BUNDLES_BUCKET_NAME = 'json-logger-deployment-bundles'
DB_BACKUP_BUCKET_NAME = 'json-logger-db-backup'
INSTANCE_TYPE = 't3.micro'
DISK_SIZE = 20

def init_aws(stack):
  AwsProvider(stack, 'aws',
    region=AWS_REGION)

class BucketsStack(TerraformStack):
  def __init__(self, scope: Construct, id: str):
    super().__init__(scope, id)
    self._init_providers()
    self._create_buckets()

  def _init_providers(self):
    init_aws(self)

  def _create_buckets(self):
    S3Bucket(self, 'cert_bucket',
      bucket=CERT_BUCKET_NAME)
    S3Bucket(self, 'bundles_bucket',
      bucket=BUNDLES_BUCKET_NAME)
    S3Bucket(self, 'db_backup_bucket',
      bucket=DB_BACKUP_BUCKET_NAME)


class InfraStack(TerraformStack):
  def __init__(self, scope: Construct, id: str):
    super().__init__(scope, id)
    self._init_providers()
    self._create_variables()
    self._create_network()
    self._create_security_group()
    self._create_ami()
    self._create_cloudinit_config()
    self._enable_s3_bucket_access()
    self._create_instance()
    self._create_volume()

  def _create_variables(self):
    self.domain = TerraformVariable(self, 'domain', type='string')
    self.domain_token = TerraformVariable(self, 'domain_token', type='string', sensitive=True)

  def _init_providers(self):
    init_aws(self)
    CloudinitProvider(self, 'cloudinit')

  def _create_network(self):
    self.vpc = Vpc(self, 'vpc',
      cidr_block = '10.0.0.0/16')
    self.subnet = Subnet(self, 'subnet',
      vpc_id=self.vpc.id,
      cidr_block='10.0.1.0/24',
      map_public_ip_on_launch=True)
    igw = InternetGateway(self, 'internet_gateway',
      vpc_id=self.vpc.id)
    DefaultRouteTable(self, 'default_route_table',
      default_route_table_id=self.vpc.default_route_table_id,
      route=[
        DefaultRouteTableRoute(
          cidr_block='0.0.0.0/0',
          gateway_id=igw.id)])

  def _create_security_group(self):
    self.security_group = SecurityGroup(self, 'security_group',
      vpc_id=self.vpc.id,
      ingress=[
        SecurityGroupIngress(
          from_port=22,
          to_port=22,
          protocol='TCP',
          cidr_blocks=['0.0.0.0/0']),
        SecurityGroupIngress(
          from_port=80,
          to_port=80,
          protocol='TCP',
          cidr_blocks=['0.0.0.0/0']),
        SecurityGroupIngress(
          from_port=443,
          to_port=443,
          protocol='TCP',
          cidr_blocks=['0.0.0.0/0'])],
      egress=[
        SecurityGroupEgress(
          from_port=0,
          to_port=0,
          protocol='-1',
          cidr_blocks=['0.0.0.0/0'])])

  def _create_ami(self):
    self.ami = DataAwsAmi(self, 'ami',
      most_recent=True,
      filter=[
        DataAwsAmiFilter(
          name='name',
          values=['ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*']),
        DataAwsAmiFilter(
          name='virtualization-type',
          values=['hvm'])],
      owners=['099720109477'])

  def _create_cloudinit_config(self):
    with open('setup.sh', 'r') as f:
      setup_content = f.read()
    setup_content = setup_content.replace('${domain}', Token.as_string(self.domain.string_value))
    setup_content = setup_content.replace('${domain_token}', Token.as_string(self.domain_token.string_value))
    with open('cloud-init.yml', 'r') as f:
      cloudinit_content = f.read()
    self.cloudinit_config = DataCloudinitConfig(self, 'cloudinit_config',
      gzip=False,
      base64_encode=False,
      part=[
        DataCloudinitConfigPart(
          filename='setup.sh',
          content_type='text/x-shellscript',
          content=setup_content),
        DataCloudinitConfigPart(
          filename='cloud-init.yml',
          content_type='text/x-cloudconfig',
          content=cloudinit_content)])

  def _enable_s3_bucket_access(self):
    cert_bucket = DataAwsS3Bucket(self, 'cert_bucket',
      bucket=CERT_BUCKET_NAME)
    bundles_bucket = DataAwsS3Bucket(self, 'bundles_bucket',
      bucket=BUNDLES_BUCKET_NAME)
    db_backup_bucket = DataAwsS3Bucket(self, 'db_backup_bucket',
      bucket=DB_BACKUP_BUCKET_NAME)
    instance_assume_role_policy = DataAwsIamPolicyDocument(self, 'instance_assume_role_policy',
      statement=[{
        'actions': ['sts:AssumeRole'],
        'principals': [{
          'type': 'Service',
          'identifiers': ['ec2.amazonaws.com']}]}])
    iam_policy = IamPolicy(self, 'iam_policy',
      policy=json.dumps({
        'Version': '2012-10-17',
        'Statement': [{
          'Effect': 'Allow',
          'Action': ['s3:*'],
          'Resource': [
            cert_bucket.arn,
            f'{cert_bucket.arn}/*']},
        {
          'Effect': 'Allow',
          'Action': ['s3:GetObject', 's3:ListBucket'],
          'Resource': [
            bundles_bucket.arn,
            f'{bundles_bucket.arn}/*']},
        {
          'Effect': 'Allow',
          'Action': ['s3:*'],
          'Resource': [
            db_backup_bucket.arn,
            f'{db_backup_bucket.arn}/*']}
          ]}))
    iam_role = IamRole(self, 'iam_role',
      assume_role_policy=instance_assume_role_policy.json,
      managed_policy_arns=[iam_policy.arn])
    self.iam_instance_profile = IamInstanceProfile(self, 'iam_instance_profile',
      role=iam_role.name)

  def _create_instance(self):
    self.instance = Instance(self, 'instance',
      ami=self.ami.id,
      instance_type=INSTANCE_TYPE,
      subnet_id=self.subnet.id,
      vpc_security_group_ids=[self.security_group.id],
      user_data=self.cloudinit_config.rendered,
      iam_instance_profile=self.iam_instance_profile.name,
      metadata_options=InstanceMetadataOptions(
        http_tokens='optional'))

  def _create_volume(self):
    ebs_volume = EbsVolume(self, 'ebs_volume',
      availability_zone=self.instance.availability_zone,
      size=DISK_SIZE,
      type='gp2')
    VolumeAttachment(self, 'ebs_volume_attachment',
      device_name='xvdh',
      volume_id=ebs_volume.id,
      instance_id=self.instance.id)

app = App()
InfraStack(app, 'infra-stack')
BucketsStack(app, 'buckets-stack')
app.synth()
