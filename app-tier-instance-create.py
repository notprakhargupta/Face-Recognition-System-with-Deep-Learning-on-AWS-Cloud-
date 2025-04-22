import boto3
import base64

AWS_ACCESS_KEY_ID     = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"

ec2 = boto3.client(
      'ec2', 
      region_name='us-east-1',
      aws_access_key_id = AWS_ACCESS_KEY_ID, 
      aws_secret_access_key = AWS_SECRET_ACCESS_KEY
      )


ami_id = ""

user_data = '''#!/bin/bash
python3 apptier.py &
'''

instance = ec2.run_instances(
           ImageId=ami_id,
           MinCount=1,
           MaxCount=1,
           InstanceType="t2.micro",
           KeyName="development",
           UserData=user_data,
           TagSpecifications=[{'ResourceType':'instance',
                               'Tags': [{
                                'Key': 'Name',
                                'Value': 'app-instance' }]}]) 




""" instance = ec2.create_instances(
           ImageId=ami_id,
           MinCount=1,
           MaxCount=1,
           InstanceType="t2.micro",
           KeyName="development",
           TagSpecifications=[{'ResourceType':'instance',
                               'Tags': [{
                                'Key': 'Name',
                                'Value': 'web-instance' }]}])  """

