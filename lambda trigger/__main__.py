import json
import base64
import pulumi
from pulumi_aws.cloudwatch import event_target
from pulumi_aws.ecr import repository
import pulumi_docker as docker
from pulumi_aws import ecs, ecr, lambda_, cloudwatch, iam

# project name
project_name = 'pulumi-event-trigger'

repo = ecr.Repository(
    resource_name = '{project_name}-lambda'.format(project_name=project_name),
    image_scanning_configuration = ecr.RepositoryImageScanningConfigurationArgs(
        scan_on_push = True
    ),
    name = '{project_name}-lambda'.format(project_name=project_name)
)

repo_lifecycle_policy = ecr.LifecyclePolicy(
    resource_name = '{project_name}-repository-policy'.format(project_name=project_name),
    repository = repo.name,
    policy = {
        'rules': [
            {
                "rulePriority": 1,
                "description": "Expire images older than 14 days",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "sinceImagePushed",
                    "countUnit": "days",
                    "countNumber": 14
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }
)

def get_registry_info(rid):
    creds = ecr.get_credentials(registry_id=rid)
    decoded = base64.b64decode(creds.authorization_token).decode()
    parts = decoded.split(':')
    if len(parts) != 2:
        raise Exception("Invalid credentials")
    return docker.ImageRegistry(creds.proxy_endpoint, parts[0], parts[1])

image = docker.Image(
    name = '{project_name}-image'.format(project_name=project_name),
    image_name = repo.repository_url,
    build = './',
    skip_push = False,
    registry = repo.registry_id.apply(get_registry_info)
)

# iam role
lambda_role = iam.Role(
    resource_name = '{project_name}-lambda-role'.format(project_name=project_name),
    assume_role_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    })
)

lambda_policy = iam.RolePolicyAttachment(
    resource_name = '{project_name}-lambda-policy'.format(project_name=project_name),
    role = lambda_role.name,
    policy_arn = iam.ManagedPolicy.LAMBDA_FULL_ACCESS
)

cloudwatch_policy = iam.RolePolicyAttachment(
    resource_name = '{project_name}-lambda-cloudwatch-policy'.format(project_name=project_name),
    role = lambda_role.name,
    policy_arn = iam.ManagedPolicy.CLOUD_WATCH_FULL_ACCESS
)

ecs_policy = iam.RolePolicyAttachment(
    resource_name = '{project_name}-lambda-ecs-policy'.format(project_name=project_name),
    role = lambda_role.name,
    policy_arn = iam.ManagedPolicy.AMAZON_ECS_FULL_ACCESS
)

lambda_log = cloudwatch.LogGroup(
    resource_name = '{project_name}-log-group'.format(project_name=project_name),
    retention_in_days = 14,
    name = '{project_name}-logs'.format(project_name=project_name)
)

lambda_function = lambda_.Function(
    resource_name = '{project_name}-function'.format(project_name=project_name),
    package_type = 'Image',
    image_uri = image.image_name,
    timeout = 60,
    role = lambda_role.arn
)

event_role = iam.Role(
    resource_name = '{project_name}-event-role'.format(project_name=project_name),
    assume_role_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            },
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "events.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    })
)

event_lambda = iam.RolePolicyAttachment(
    resource_name = '{project_name}-lambda-event-policy',
    role = event_role.name,
    policy_arn = iam.ManagedPolicy.LAMBDA_FULL_ACCESS
)

event_cloudwatch = iam.RolePolicyAttachment(
    resource_name = '{project_name}-cloudwatch-event-policy',
    role = event_role.name,
    policy_arn = iam.ManagedPolicy.CLOUD_WATCH_EVENTS_FULL_ACCESS
)

event_rule = cloudwatch.EventRule(
    resource_name = '{project_name}-event-rule'.format(project_name=project_name),
    role_arn = event_role.arn,
    schedule_expression = 'cron(0 12 * * ? *)'
)

event_target = cloudwatch.EventTarget(
    resource_name = '{project_name}-event-target'.format(project_name=project_name),
    role_arn = event_role.arn,
    rule = event_rule.name,
    arn = lambda_function.arn
)