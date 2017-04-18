#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto3
import click
import sys
import logging
import json
import os

# Setup logging using standard error.
logging.basicConfig(stream=sys.stderr,
                    level=logging.CRITICAL)


def create_session(region, aws_type="ec2"):
    resource = boto3.resource(aws_type, region_name=region)
    return resource


def get_regions(region, aws_type="ec2"):
    client = boto3.client(aws_type, region_name=region)
    regions = [region['RegionName'] for region in
               client.describe_regions()['Regions']]
    return regions


def get_filtered(resource_query, filter_payload):
    filtered_result = resource_query(Filters=filter_payload)
    return filtered_result


def generate_output_from_filtered(filtered_data, region, **extra_kv):
    output = list()
    for item in filtered_data:
        iteration = dict()
        if item.tags:
            for index in range(len(item.tags)):
                iteration[item.tags[index]['Key']] = item.tags[index]['Value']
        for key, value in extra_kv.iteritems():
            func = "item." + value
            # Using eval is never a good idea.
            iteration[key] = str(eval(func))
        iteration['id'] = str(item.id)
        iteration['region'] = str(region)
        output.append(iteration)

    return output


def destroy_resources(aws_resource, query_list, dry_run, resource_type,
                      delete_method):
    for item in query_list:
        if dry_run:
            click.secho("Will be destroyed: {0}".format(item['id']))
        else:
            target = getattr(aws_resource, resource_type)(item['id'])
            response = getattr(target, delete_method)()
            click.secho("Destroyed: {0}".format(item['id']))
            click.secho("Response: {0}\n".format(json.dumps(response)))


@click.command()
@click.option('--aws-secret',
              envvar='AWS_SECRET_ACCESS_KEY',
              prompt=True,
              hide_input=True,
              help='AWS secret key. (AWS_SECRET_ACCESS_KEY)')
@click.option('--aws-id',
              envvar='AWS_ACCESS_KEY_ID',
              prompt=True,
              hide_input=True,
              help='AWS key id. (AWS_ACCESS_KEY_ID)')
@click.option('--aws-region',
              '-r',
              default='us-east-1',
              help='AWS region to query. (us-east-1)')
@click.option('--service',
              '-s',
              default='instances-off',
              type=click.Choice(['instances-off',
                                 'volumes-off',
                                 'instances-on',
                                 'volumes-on'
                                 ]),
              help='AWS resource type to query. (instances-off)')
@click.option('--destroy',
              is_flag=True,
              help='Destroy "off" resources.')
@click.option('--dry-run',
              is_flag=True,
              help='Used with --destroy.')
@click.option('--list-regions',
              is_flag=True,
              help='List available AWS regions.')
@click.option('--debug',
              is_flag=True,
              help='Enable debug.')
def main(aws_secret, aws_id, aws_region, service, destroy, dry_run,
         list_regions, debug):
    """Snooper provides a simple way for finding AWS resources.

    Currently supporting:

    [instances-off] = EC2 stopped instances

    [volumes-off] = EBS unused volumes

    [instances-on] = EC2 running instances

    [volumes-on] = EBS in use volumes

    [--destroy] = Destroy unused/stopped resources

    Note: AWS credentials may and should be available as environment variables.
    """
    try:
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

        if aws_id and aws_secret:
            os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret
            os.environ["AWS_ACCESS_KEY_ID"] = aws_id

        if list_regions:
            click.secho(
                ' '.join(get_regions(region=aws_region, aws_type="ec2")),
                fg='green')
            exit(code=0)

        if service == 'instances-off':
            filter_instances_stopped = [{
                'Name': 'instance-state-name',
                'Values': ['stopped']
            }]

            ec2 = create_session(region=aws_region, aws_type="ec2")
            formatted_query_result = generate_output_from_filtered(
                get_filtered(ec2.instances.filter, filter_instances_stopped),
                region=aws_region, id='id', launch_time='launch_time.date()')
            if destroy:
                destroy_resources(ec2, formatted_query_result, dry_run,
                                  resource_type='Instance',
                                  delete_method='terminate')
            else:
                click.secho(json.dumps(formatted_query_result), fg='green')

        if service == 'volumes-off':
            filter_volumes_available = [{
                'Name': 'status',
                'Values': ['available']
            }]

            ec2 = create_session(region=aws_region, aws_type="ec2")
            formatted_query_result = generate_output_from_filtered(
                get_filtered(ec2.volumes.filter, filter_volumes_available),
                region=aws_region, id='id', create_time='create_time.date()')
            if destroy:
                destroy_resources(ec2, formatted_query_result, dry_run,
                                  resource_type='Volume',
                                  delete_method='delete')
            else:
                click.secho(json.dumps(formatted_query_result), fg='green')

        if service == 'volumes-on':
            filter_volumes_available = [{
                'Name': 'status',
                'Values': ['in-use']
            }]

            ec2 = create_session(region=aws_region, aws_type="ec2")
            formatted_query_result = generate_output_from_filtered(
                get_filtered(ec2.volumes.filter, filter_volumes_available),
                region=aws_region, id='id', create_time='create_time.date()')
            click.secho(json.dumps(formatted_query_result), fg='green')

        if service == 'instances-on':
            filter_instances_stopped = [{
                'Name': 'instance-state-name',
                'Values': ['running']
            }]

            ec2 = create_session(region=aws_region, aws_type="ec2")
            formatted_query_result = generate_output_from_filtered(
                get_filtered(ec2.instances.filter, filter_instances_stopped),
                region=aws_region, id='id', launch_time='launch_time.date()')
            click.secho(json.dumps(formatted_query_result), fg='green')

    except Exception as e:
        logging.critical(str(e))
        click.secho('==> Try enabling debug for more information.', nl=True,
                    fg='red')
        sys.exit(42)


if __name__ == '__main__':
    main()
