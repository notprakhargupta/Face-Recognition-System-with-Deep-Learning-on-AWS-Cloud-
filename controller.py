#!/usr/bin/env python3.10

import math
import boto3
import time
from settings import *
import base64

session = boto3.Session(aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
sqs_client = session.client('sqs', region_name="us-east-1")
ec2_client = session.client('ec2', region_name="us-east-1")

WEB_TIER = "WEB_TIER"
APP_TIER = "APP_TIER"
APP_TIER_AMI = "APP_TIER_AMI"
SECURITY_GROUP_ID = "SECURITY_GROUP_ID"

user_data_script = """#!/bin/bash
# Use 'ec2-user'
sudo -u ec2-user -i /bin/bash <<'EOF'
cd /home/ec2-user/app-tier-sol/
python3 main.py > /home/ec2-user/app-tier-sol/main.log 2>&1
EOF
"""


def get_running_instances():
    try:
        response = ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running','pending']}])
        instances = [instance['InstanceId'] for reservation in response['Reservations'] for instance in reservation['Instances']]
        return instances
    except Exception as e:
        print(f'Error getting the running instances: {e}')

def get_queue_length(queue_url):
    try:
        attributes = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['ApproximateNumberOfMessages'])
        return int(attributes['Attributes']['ApproximateNumberOfMessages'])
    except Exception as e:
        print(f"Error getting queue length for {queue_url}: {e}")
        return None

def get_queue_length_not_visible(queue_url):
    try:
        attributes = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['ApproximateNumberOfMessagesNotVisible'])
        return int(attributes['Attributes']['ApproximateNumberOfMessagesNotVisible'])
    except Exception as e:
        print(f"Error getting queue length for {queue_url}: {e}")
        return None

def get_stopped_instances():
    try:
        response = ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped','stopping']}])
        instances = [instance['InstanceId'] for reservation in response['Reservations'] for instance in reservation['Instances']]
        return instances
    except Exception as e:
        print(f'Error getting the stopped instances: {e}')

def start_instance(instance_id):
    try:
        instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance_state = instance_info['Reservations'][0]['Instances'][0]['State']['Name']

        if instance_state == "stopped":
            ec2_client.start_instances(InstanceIds=[instance_id])
        else:
            print(f"Instance {instance_id} is in {instance_state} state and cannot be started.")
    except Exception as e:
        print(f'Error trying to start instance: {e}')

def start_multiple_instances(instance_ids):
    try:
        for instance_id in instance_ids:
            start_instance(instance_id)
    except Exception as e:
        print(f'Error starting multiple instances: {e}')

def terminate_multiple_instances(instance_ids):
    try:
        running_instances = [i for i in instance_ids if ec2_client.describe_instances(InstanceIds=[i])['Reservations'][0]['Instances'][0]['State']['Name'] == 'running']
        if running_instances:
            ec2_client.terminate_instances(InstanceIds=running_instances)
            print(f'Terminated instances: {running_instances}')
    except Exception as e:
        print(f'Error trying to terminate multiple instances: {e}')

def stop_multiple_instances(instance_ids):
    try:
        running_instances = [i for i in instance_ids if ec2_client.describe_instances(InstanceIds=[i])['Reservations'][0]['Instances'][0]['State']['Name'] == 'running']
        if running_instances:
            ec2_client.stop_instances(InstanceIds=running_instances)
    except Exception as e:
        print(f'Error trying to stop multiple instances: {e}')

def get_highest_instance_number():
    try:
        #all_instances = get_running_instances() + get_stopped_instances()
        all_instances = get_running_instances()
        instance_numbers = []

        for instance_id in all_instances:
            instance_tags = ec2_client.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0].get('Tags', [])
            for tag in instance_tags:
                if tag['Key'] == 'Name' and 'app-tier-instance-' in tag['Value']:
                    try:
                        instance_numbers.append(int(tag['Value'].split('-')[-1]))
                    except ValueError:
                        pass

        if instance_numbers:
            return max(instance_numbers)
        else:
            return 1
    except Exception as e:
        print(f'Error trying to get the highest instance number: {e}')

def create_instance():
    try:
        """Creates a new instance using the app-tier's AMI"""
        highest_number = get_highest_instance_number()
        new_instance_name = 'app-tier-instance-' + str(highest_number + 1)
        print("Starting Instance------------------------------------------------------------")
        ec2_client.run_instances(
            ImageId=APP_TIER_AMI,
            InstanceType='t2.micro',
            MinCount=1,
            MaxCount=1,
            KeyName='Project-1Pem',
            SecurityGroupIds=[SECURITY_GROUP_ID],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': new_instance_name
                        }
                    ]
                }
            ],
            UserData=user_data_script
        )
        time.sleep(3)
    except Exception as e:
        print(f'Error trying to create new instance: {e}')


def auto_scale_instances():
    try:
        queue_length = int(
            sqs_client.get_queue_attributes(QueueUrl=SQS_REQUEST_QUEUE_URL, AttributeNames=['ApproximateNumberOfMessages']).get(
                "Attributes").get("ApproximateNumberOfMessages"))
        queue_length_not_visible = int(
            sqs_client.get_queue_attributes(QueueUrl=SQS_REQUEST_QUEUE_URL, AttributeNames=['ApproximateNumberOfMessagesNotVisible']).get(
                "Attributes").get("ApproximateNumberOfMessagesNotVisible"))
        response_queue_length = int(
            sqs_client.get_queue_attributes(QueueUrl=SQS_RESPONSE_QUEUE_URL, AttributeNames=['ApproximateNumberOfMessages']).get(
                "Attributes").get("ApproximateNumberOfMessages"))
        response_queue_length_not_visible = int(
            sqs_client.get_queue_attributes(QueueUrl=SQS_RESPONSE_QUEUE_URL, AttributeNames=['ApproximateNumberOfMessagesNotVisible']).get(
                "Attributes").get("ApproximateNumberOfMessagesNotVisible"))
        print("Request queue length:", queue_length, "Response queue length", response_queue_length)
        print("Request in flight", queue_length_not_visible, "Response in flight", response_queue_length_not_visible)

        running_instances = get_running_instances()
        stopped_instances = get_stopped_instances()

        if(WEB_TIER in running_instances):
            running_instances.remove(WEB_TIER)
        
        if(APP_TIER in running_instances):
            running_instances.remove(APP_TIER)

        if(APP_TIER in stopped_instances):
            stopped_instances.remove(APP_TIER)

        required_instances = 0
        
        if queue_length == 0:
            if len(running_instances) > 0:
                if (((get_queue_length(SQS_RESPONSE_QUEUE_URL)) == 0) and ((get_queue_length(SQS_REQUEST_QUEUE_URL)) == 0) and
                    ((get_queue_length_not_visible(SQS_REQUEST_QUEUE_URL) == 0))):
                    terminate_multiple_instances(running_instances)
        elif queue_length > 49:
            required_instances = 19
        else:
            required_instances = int(math.ceil(queue_length/3))

        if len(running_instances) < required_instances:
            needed_instances = required_instances - len(running_instances)
            if len(stopped_instances) >= needed_instances:
                start_multiple_instances(stopped_instances[:needed_instances])
            else:
                if not ((len(running_instances) + len(stopped_instances)) == required_instances):
                    for _ in range(needed_instances - len(stopped_instances)):
                        create_instance()

    except Exception as e:
        print(f'Error trying to autoscale: {e}')



if __name__ == "__main__":
    #create_instance()
    while True:
        auto_scale_instances()
        time.sleep(12)
