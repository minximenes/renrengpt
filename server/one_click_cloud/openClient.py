import os
import time
import json

from concurrent import futures
from datetime import datetime, timedelta
from flask import current_app
from itertools import groupby
from typing import Dict, List, Optional, Set, Tuple

from alibabacloud_tea_openapi import models as openapi_models
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_vpc20160428.client import Client as VpcClient
from alibabacloud_vpc20160428 import models as vpc_models
from alibabacloud_tea_util import models as util_models
# inner import
from one_click_cloud.auth import generatePwd, isVisitor, ifDebugMode, unistrToBase64, base64ToUnistr
from one_click_cloud.openRedis import OpenRedis

class OpenClient:
    def __init__(self):
        pass

    @staticmethod
    def getWorkers(tasknum: int) -> int:
        '''
        get max_workers of ThreadPoolExecutor
        @param: tasknum
        @return: max_workers
        '''
        return tasknum if ifDebugMode() else 2 * os.cpu_count() + 1

    @staticmethod
    def Config(
        key_id: str, key_secret: str, endpoint: str = "ecs"
    ) -> openapi_models.Config:
        """
        create config
        @param: key_id, key_secret, endpoint(default "ecs")
        @return: Config
        """
        config = openapi_models.Config(
            access_key_id=key_id,
            access_key_secret=key_secret,
            endpoint=f"{endpoint}.aliyuncs.com",
            connect_timeout=5000,
            read_timeout=5000,
        )
        return config

    @staticmethod
    def Runtime(timeout: int = 30 * 1000) -> util_models.RuntimeOptions:
        '''
        create runtimeOptions
        @param: milliseconds(30s)
        @return: RuntimeOptions
        '''
        return util_models.RuntimeOptions(
            read_timeout=timeout, connect_timeout=timeout
        )

    @staticmethod
    def describeRegions(
        key_id: str, key_secret: str, tuning: bool = True
    ) -> Dict:
        """
        describe regions
        @param: key_id, key_secret, tuning(default True)
        @return: all regions' id and name
        """
        config = OpenClient.Config(key_id, key_secret)
        client = EcsClient(config)
        runtime = OpenClient.Runtime()

        request = ecs_models.DescribeRegionsRequest(
            resource_type="instance", instance_charge_type="SpotAsPriceGo"
        )
        response = client.describe_regions_with_options(request, runtime)
        # exclude dubai, Indonesia when tuning
        return {
            r.region_id: r.local_name
            for r in response.body.regions.region
            if not (r.region_id in ["me-east-1", "ap-southeast-5"] and tuning)
        }

    @staticmethod
    def describeInstances(
        key_id: str, key_secret: str, region_ids: List[str]
    ) -> List[Dict]:
        """
        describe instances in regions
        @param: key_id, key_secret, region_ids
        @return: instances' dict
        """
        instances, future_rlts = [], []
        tasknum = len(region_ids)
        if tasknum == 0:
            return []

        with futures.ThreadPoolExecutor(max_workers=OpenClient.getWorkers(tasknum)) as executor:
            for region_id in region_ids:
                config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
                client = EcsClient(config)
                runtime = OpenClient.Runtime()

                request = ecs_models.DescribeInstancesRequest(
                    region_id=region_id,
                    instance_charge_type="PostPaid" if not isVisitor(key_id) else "PrePaid"
                )
                future_rlt = executor.submit(client.describe_instances_with_options, request, runtime)
                future_rlts.append(future_rlt)

            for future_rlt in futures.as_completed(future_rlts):
                response = future_rlt.result()
                instances.extend(response.body.instances.instance)

        return [
            {
                "instance_id": instance.instance_id,
                "status": instance.status,
                "region_id": instance.region_id,
                "pubip_addrs": instance.public_ip_address.ip_address,
                "cpu": instance.cpu,
                "mem": int(instance.memory / 1024),
                "bandwidth": instance.internet_max_bandwidth_out,
                "osname": instance.osname,
                "creation_time": instance.creation_time,
                "release_time": instance.auto_release_time,
            }
            for instance in sorted(instances, key=lambda p: p.creation_time, reverse=True)
        ]

    @staticmethod
    def describeInstanceAttribute(
        key_id: str, key_secret: str, region_id: str, instance_id: str
    ) -> Dict:
        """
        describe attributes of instance
        @param: key_id, key_secret, region_id, instance_id
        @return: instance attribute
        """
        config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
        client = EcsClient(config)
        runtime = OpenClient.Runtime()

        # instance attribute
        describe_instance_attribute_request = ecs_models.DescribeInstanceAttributeRequest(
            instance_id=instance_id
        )
        describe_instance_attribute_response = client.describe_instance_attribute_with_options(
            describe_instance_attribute_request, runtime
        )
        instance = describe_instance_attribute_response.body
        # system disk
        describe_disks_request = ecs_models.DescribeDisksRequest(
            region_id=region_id, instance_id=instance_id, disk_type="system"
        )
        describe_disks_response = client.describe_disks_with_options(
            describe_disks_request, runtime
        )
        disk0 = describe_disks_response.body.disks.disk[0]
        # user data
        describe_user_data_request = ecs_models.DescribeUserDataRequest(
            region_id=region_id, instance_id=instance_id
        )
        describe_user_data_response = client.describe_user_data_with_options(
            describe_user_data_request, runtime
        )
        user_data_base64 = describe_user_data_response.body.user_data
        return {
            "instance_id": instance_id,
            "status": instance.status,
            "region_id": region_id,
            "zone_id": instance.zone_id,
            "pubip_addrs": instance.public_ip_address.ip_address,
            "instance_type": instance.instance_type,
            "cpu": instance.cpu,
            "mem": int(instance.memory / 1024),
            "bandwidth": instance.internet_max_bandwidth_out,
            "disk_category": disk0.category,
            "disk_size": disk0.size,
            "price": OpenClient.describePrice(
                key_id,
                key_secret,
                region_id,
                instance.zone_id,
                instance.instance_type,
                instance.internet_max_bandwidth_out,
                instance.image_id,
                [disk0.category],
            )[1],
            "creation_time": instance.creation_time,
            "user_data": user_data_base64,
        }

    @staticmethod
    def describePrice(
        key_id: str, key_secret: str, region_id: str, zone_id: str,
        instance_type: str, bandwidth: int, image_id: str,
        disk_categorys: List[str] = [
            "cloud_efficiency", "cloud_essd_entry"
        ], cpu: Optional[int] = None, mem: Optional[float] = None, is_spot: bool = True
    ) -> Tuple:
        """
        describe instance price
        @param: key_id, key_secret, region_id, zone_id,
                instance_type, bandwidth, image_id,
                disk_categorys,
                # "cloud_efficiency", "cloud_auto", "cloud_ssd", "cloud_essd", "cloud_essd_entry"
                cpu(unused), mem(unused), is_spot(default True)
        @return: disk category and instance price
        """
        config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
        client = EcsClient(config)
        runtime = OpenClient.Runtime()

        category_prices = []
        for disk_category in disk_categorys:
            request_paras = dict(
                region_id=region_id,
                resource_type="instance",
                instance_type=instance_type,
                io_optimized="optimized",
                instance_network_type="vpc",
                # bandwidth
                internet_charge_type="PayByBandwidth",
                internet_max_bandwidth_out=bandwidth,
                # system disk
                image_id=image_id,
                system_disk=ecs_models.DescribePriceRequestSystemDisk(
                    size=20, category=disk_category
                ),
                zone_id=zone_id,
            )
            if is_spot:
                request_paras.update(dict(
                    spot_strategy="SpotAsPriceGo",
                    spot_duration=0,
                ))
            else:
                request_paras.update(dict(
                    # prepaid
                    price_unit="Year",
                ))
            request = ecs_models.DescribePriceRequest(**request_paras)
            try:
                response = client.describe_price_with_options(request, runtime)
                category_prices.append(
                    (disk_category, response.body.price_info.price.trade_price)
                )
            except Exception:
                continue

        if len(category_prices) == 0:
            return ("", -1)
        else:
            return min(category_prices, key=lambda p: p[1])

    @staticmethod
    def deleteInstance(
        key_id: str, key_secret: str, region_id: str, instance_id: str
    ):
        """
        delete instance
        @param: key_id, key_secret, region_id, instance_id
        """
        ecs_client = EcsClient(OpenClient.Config(key_id, key_secret, f"ecs.{region_id}"))
        vpc_client = VpcClient(OpenClient.Config(key_id, key_secret, f"vpc.{region_id}"))
        runtime = OpenClient.Runtime()
        # retrieve instance info
        describe_instance_attribute_request = ecs_models.DescribeInstanceAttributeRequest(
            instance_id=instance_id
        )
        describe_instance_attribute_response = ecs_client.describe_instance_attribute_with_options(
            describe_instance_attribute_request, runtime
        )
        instance = describe_instance_attribute_response.body
        v_switch_id = instance.vpc_attributes.v_switch_id
        vpc_id = instance.vpc_attributes.vpc_id
        security_group_id = instance.security_group_ids.security_group_id[0]
        # delete instance
        delete_instance_request = ecs_models.DeleteInstanceRequest(
            instance_id=instance_id, force=True
        )
        ecs_client.delete_instance_with_options(delete_instance_request, runtime)
        # delete security_group
        delete_security_group_request = ecs_models.DeleteSecurityGroupRequest(
            region_id=region_id, security_group_id=security_group_id
        )
        if not OpenClient.waitforDeletion(
            (ecs_client.delete_security_group_with_options, delete_security_group_request, runtime)
        ):
            return
        # delete v_switch
        delete_vswitch_request = vpc_models.DeleteVSwitchRequest(
            region_id=region_id, v_switch_id=v_switch_id
        )
        if not OpenClient.waitforDeletion(
            (vpc_client.delete_vswitch_with_options, delete_vswitch_request, runtime)
        ):
            return
        # delete vpc
        delete_vpc_request = vpc_models.DeleteVpcRequest(
            region_id=region_id, vpc_id=vpc_id, force_delete=True
        )
        if not OpenClient.waitforDeletion(
            (vpc_client.delete_vpc_with_options, delete_vpc_request, runtime)
        ):
            return

    @staticmethod
    def waitforDeletion(params: Tuple) -> bool:
        """
        wait previous task finished until 30s
        @param: tuple of function handler, parameters
        @return: true when success or false when timeout
        """
        func_name, para1, para2 = params
        starttm = time.perf_counter()
        while True:
            try:
                func_name(para1, para2)
                return True
            except Exception as error:
                if error.code.startswith("DependencyViolation"):
                    if time.perf_counter() - starttm > 30:
                        return False
                    time.sleep(5)
                else:
                    raise error

    @staticmethod
    def querySpecs(
        key_id: str, key_secret: str, region_ids: List[str],
        cpus: List[int], mems: List[float], bandwidth: int, is_spot: bool
    ) -> List[Dict]:
        """
        query spec list
        @param: key_id, key_secret, region_range, cpus, mems, bandwidth, is_spot
        @return: spec list
        """
        instance_types = OpenClient.describeAvailableInstances(
            key_id, key_secret, region_ids, cpus, mems, is_spot
        )
        if len(instance_types) > 0:
            specs = OpenClient.comparePrice(
                key_id, key_secret, instance_types, bandwidth
            )
            # get 1st in group of same price and region
            return [
                next(group)
                for _, group in groupby(specs, key=lambda p: (p["price"], p["region_id"]))
            ]
        else:
            return []

    @staticmethod
    def describeAvailableInstances(
        key_id: str, key_secret: str, region_ids: List[str],
        cpus: List[int], mems: List[float], is_spot: bool
    ) -> List[Dict]:
        """
        describe instance type in given regions
        @param: key_id, key_secret, region_ids, cpus, mems, is_spot
        @return: instance_types
        """
        instance_types, future_rlts = [], {}
        tasknum = len(region_ids) * len(cpus) * len(mems)

        with futures.ThreadPoolExecutor(max_workers=OpenClient.getWorkers(tasknum)) as executor:
            for region_id in region_ids:
                for vCPU, memGiB in ((x, y) for x in cpus for y in mems):
                    config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
                    client = EcsClient(config)
                    runtime = OpenClient.Runtime()

                    request_paras = dict(
                        region_id=region_id,
                        destination_resource="InstanceType",
                        cores=vCPU,
                        memory=memGiB,
                        io_optimized="optimized",
                        network_category='vpc',
                    )
                    if is_spot:
                        request_paras.update(dict(
                            instance_charge_type="PostPaid",
                            spot_strategy="SpotAsPriceGo",
                        ))
                    else:
                        request_paras.update(dict(
                            instance_charge_type="PrePaid",
                        ))
                    request = ecs_models.DescribeAvailableResourceRequest(**request_paras)
                    future_rlt = executor.submit(client.describe_available_resource_with_options, request, runtime)
                    future_rlts[future_rlt] = (region_id, vCPU, memGiB)

            for future_rlt in futures.as_completed(future_rlts):
                region_id, vCPU, memGiB = future_rlts[future_rlt]
                response = future_rlt.result()
                available_zones = response.body.available_zones.available_zone
                for zone in list(filter(lambda z: z.status_category == "WithStock", available_zones)):
                    for resource in zone.available_resources.available_resource:
                        supported_resources = resource.supported_resources.supported_resource
                        for supported_res in list(filter(lambda s: s.status_category == "WithStock", supported_resources)):
                            instance_types.append({
                                "region_id": region_id,
                                "zone_id": zone.zone_id,
                                "instance_type": supported_res.value,
                                "cpu": vCPU,
                                "mem": memGiB,
                                "is_spot": is_spot,
                            })

        return instance_types

    @staticmethod
    def comparePrice(
        key_id: str, key_secret: str, instance_types: List[Dict], bandwidth: int, amount: int = 200
    ) -> List[Dict]:
        """
        compare instance price
        @param: key_id, key_secret, instance info, bandwidth, amount(default 200)
        @return: instances of given amount at lowest price
        """
        # image id
        region_ids = set([instance_tp["region_id"] for instance_tp in instance_types])
        image_ids = OpenClient.retrieveUbuntuImages(key_id, key_secret, region_ids)
        # price
        instance_prices, future_rlts = [], {}
        tasknum = len(instance_types)

        with futures.ThreadPoolExecutor(max_workers=OpenClient.getWorkers(tasknum)) as executor:
            for instance_tp in instance_types:
                image_id = image_ids[instance_tp["region_id"]]
                future_rlt = executor.submit(
                    OpenClient.describePrice,
                    key_id=key_id,
                    key_secret=key_secret,
                    **instance_tp,
                    bandwidth=bandwidth,
                    image_id=image_id,
                )
                future_rlts[future_rlt] = {
                    **instance_tp, "bandwidth": bandwidth, "image_id": image_id
                }

            for future_rlt in futures.as_completed(future_rlts):
                instance_tp_plus = future_rlts[future_rlt]
                disk_category, price = future_rlt.result()
                instance_prices.append(
                    {**instance_tp_plus, "disk_category": disk_category, "price": price}
                )

        return sorted(
            list(filter(lambda p: p["price"] > 0, instance_prices)),
            key=lambda p: (p["price"], p["region_id"]),
        )[:amount]

    @staticmethod
    def describeUbuntuImages(
        key_id: str, key_secret: str, region_ids: Set[str]
    ) -> Dict:
        """
        describe ubuntu image
        @param: key_id, key_secret, region_ids
        @return: image_ids
        """
        image_ids, future_rlts = {}, {}
        tasknum = len(region_ids)

        with futures.ThreadPoolExecutor(max_workers=OpenClient.getWorkers(tasknum)) as executor:
            for region_id in region_ids:
                config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
                client = EcsClient(config)
                runtime = OpenClient.Runtime()

                request = ecs_models.DescribeImagesRequest(
                    region_id=region_id, status="Available", image_family="acs:ubuntu_20_04_x64"
                )
                future_rlt = executor.submit(client.describe_images_with_options, request, runtime)
                future_rlts[future_rlt] = region_id

            for future_rlt in futures.as_completed(future_rlts):
                region_id = future_rlts[future_rlt]
                response = future_rlt.result()
                image_ids[region_id] = response.body.images.image[0].image_id

        return image_ids

    @staticmethod
    def retrieveUbuntuImages(
        key_id: str, key_secret: str, region_ids: List[str]
    ) -> Dict:
        '''
        retrieve ubuntu image from redis or api
        @param: key_id, key_secret, region_ids
        @return: image_ids
        '''
        r = OpenRedis("8.137.83.192") if ifDebugMode else OpenRedis()
        ubuntuImage = r.get("ubuntuimage")
        if ubuntuImage:
            return json.loads(ubuntuImage)
        else:
            return OpenClient.describeUbuntuImages(key_id, key_secret, region_ids)

    @staticmethod
    def createInstance(
        key_id: str, key_secret: str, region_id: str, zone_id: str,
        instance_type: str, bandwidth: int, image_id: str, disk_category: str,
        alive_minutes: int, user_data: str
    ) -> str:
        """
        create instance
        @param: key_id, key_secret, region_id, zong_id,
                instance_type, bandwidth, image_id, disk_category,
                alive_minutes, user_data(base64)
        @return: instance_id
        """
        config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
        client = EcsClient(config)
        runtime = OpenClient.Runtime()

        vpc_id, v_switch_id = OpenClient.createDefaultVSwitch(
            key_id, key_secret, region_id, zone_id
        )
        security_group_id = OpenClient.createDefaultSecurityGroup(
            key_id, key_secret, region_id, vpc_id
        )
        auto_release_time = OpenClient.getAliveTime(alive_minutes)
        password = generatePwd(10)

        run_instances_request = ecs_models.RunInstancesRequest(
            amount=1,
            auto_release_time=auto_release_time,
            region_id=region_id,
            v_switch_id=v_switch_id,
            instance_type=instance_type,
            instance_charge_type="PostPaid",
            spot_strategy="SpotAsPriceGo",
            spot_duration=0,
            password=password,
            description=f"root:{password}",
            security_group_id=security_group_id,
            user_data=OpenClient.getUserDataWithWeb(user_data) if user_data else "",
            # bandwidth
            internet_charge_type="PayByBandwidth",
            internet_max_bandwidth_out=bandwidth,
            # system disk
            image_id=image_id,
            system_disk=ecs_models.DescribePriceRequestSystemDisk(
                size=20, category=disk_category
            ),
        )
        run_instances_response = client.run_instances_with_options(
            run_instances_request, runtime
        )
        instance_ids = run_instances_response.body.instance_id_sets.instance_id_set
        return instance_ids[0]

    @staticmethod
    def createDefaultVSwitch(
        key_id: str, key_secret: str, region_id: str, zone_id: str
    ) -> Tuple:
        """
        retrieve or create default vswitch
        @param: key_id, key_secret, region_id, zone_id
        @return: default vpc_id, vswitch_id
        """
        config = OpenClient.Config(key_id, key_secret, f"vpc.{region_id}")
        client = VpcClient(config)
        runtime = OpenClient.Runtime()

        vpc_id = OpenClient.createDefaultVpc(key_id, key_secret, region_id)
        describe_vswitches_request = vpc_models.DescribeVSwitchesRequest(
            region_id=region_id, vpc_id=vpc_id, zone_id=zone_id, is_default=True
        )
        describe_vswitches_respnse = client.describe_vswitches_with_options(
            describe_vswitches_request, runtime
        )
        v_switchs = describe_vswitches_respnse.body.v_switches.v_switch
        if len(v_switchs) == 0:
            # create default v_switch
            create_default_vswitch_request = vpc_models.CreateDefaultVSwitchRequest(
                region_id=region_id, zone_id=zone_id
            )
            create_default_vswitch_response = client.create_default_vswitch_with_options(
                create_default_vswitch_request, runtime
            )
            v_switch_id = create_default_vswitch_response.body.v_switch_id
            # wait for available
            OpenClient.waitforAvailable(key_id, key_secret, (region_id, "vswitch", v_switch_id))
        else:
            v_switch_id = v_switchs[0].v_switch_id

        return (vpc_id, v_switch_id)

    @staticmethod
    def createDefaultVpc(
        key_id: str, key_secret: str, region_id: str
    ) -> str:
        """
        retrieve or create default vpc
        @param: key_id, key_secret, region_id
        @return: default vpc_id
        """
        config = OpenClient.Config(key_id, key_secret, f"vpc.{region_id}")
        client = VpcClient(config)
        runtime = OpenClient.Runtime()

        describe_vpcs_request = vpc_models.DescribeVpcsRequest(
            region_id=region_id, is_default=True
        )
        describe_vpcs_response = client.describe_vpcs_with_options(
            describe_vpcs_request, runtime
        )
        vpcs = describe_vpcs_response.body.vpcs.vpc
        if len(vpcs) == 0:
            # create default vpc
            create_default_vpc_request = vpc_models.CreateDefaultVpcRequest(
                region_id=region_id
            )
            create_default_vpc_response = client.create_default_vpc_with_options(
                create_default_vpc_request, runtime
            )
            vpc_id = create_default_vpc_response.body.vpc_id
            # wait for available
            OpenClient.waitforAvailable(key_id, key_secret, (region_id, "vpc", vpc_id))
            return vpc_id
        else:
            return vpcs[0].vpc_id

    @staticmethod
    def waitforAvailable(key_id: str, key_secret: str, params: Tuple):
        """
        wait for available until 30s
        @param: key_id, key_secret, tuple of region_id, resource_type, resource_id
        """
        region_id, resource_type, resource_id = params
        starttm = time.perf_counter()

        config = OpenClient.Config(key_id, key_secret, f"vpc.{region_id}")
        client = VpcClient(config)
        runtime = OpenClient.Runtime()

        if resource_type == "vpc":
            request = vpc_models.DescribeVpcAttributeRequest(
                region_id=region_id, vpc_id=resource_id
            )
            response = client.describe_vpc_attribute_with_options(request, runtime)
            vpc = response.body
            while vpc.status != "Available":
                if time.perf_counter() - starttm > 30:
                    return
                time.sleep(3)
                response = client.describe_vpc_attribute_with_options(request, runtime)
                vpc = response.body

        elif resource_type == "vswitch":
            request = vpc_models.DescribeVSwitchAttributesRequest(
                region_id=region_id, v_switch_id=resource_id
            )
            response = client.describe_vswitch_attributes_with_options(request, runtime)
            vswitch = response.body
            while vswitch.status != "Available":
                if time.perf_counter() - starttm > 30:
                    return
                time.sleep(3)
                response = client.describe_vswitch_attributes_with_options(request, runtime)
                vswitch = response.body

    @staticmethod
    def createDefaultSecurityGroup(
        key_id: str, key_secret: str, region_id: str, vpc_id: str
    ) -> str:
        """
        retrieve or create security group
        @param: key_id, key_secret, region_id, vpc_id
        @return: security_group_id
        """
        security_group_ids = OpenClient.describeSecurityGroups(key_id, key_secret, region_id)
        if len(security_group_ids) == 0:
            return OpenClient.createSecurityGroup(key_id, key_secret, region_id, vpc_id)
        else:
            return security_group_ids[0]

    @staticmethod
    def describeSecurityGroups(
        key_id: str, key_secret: str, region_id: str, security_group_name: str = "one-click-cloud"
    ) -> List[str]:
        """
        describe security groups
        @param: key_id, key_secret, region_id, security_group_name(default "one-click-cloud")
        @return: security_group_ids
        """
        config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
        client = EcsClient(config)
        runtime = OpenClient.Runtime()

        security_groups_request = ecs_models.DescribeSecurityGroupsRequest(
            region_id=region_id, security_group_name=security_group_name
        )
        security_groups_response = client.describe_security_groups_with_options(
            security_groups_request, runtime
        )
        security_groups = security_groups_response.body.security_groups.security_group
        return [group.security_group_id for group in security_groups]

    @staticmethod
    def createSecurityGroup(
        key_id: str, key_secret: str, region_id: str, vpc_id: str, security_group_name: str = "one-click-cloud"
    ) -> str:
        """
        create security group with initial permissions
        @param: key_id, key_secret, region_id, vpc_id, security_group_name(default "one-click-cloud")
        @return: security_group_id
        """
        config = OpenClient.Config(key_id, key_secret, f"ecs.{region_id}")
        client = EcsClient(config)
        runtime = OpenClient.Runtime()
        # create security group
        create_security_group_request = ecs_models.CreateSecurityGroupRequest(
            region_id=region_id, vpc_id=vpc_id, security_group_name=security_group_name
        )
        create_security_group_response = client.create_security_group_with_options(
            create_security_group_request, runtime
        )
        security_group_id = create_security_group_response.body.security_group_id
        # initialize permissions
        permissions = [
            ecs_models.AuthorizeSecurityGroupRequestPermissions(**v)
            for v in OpenClient.getInitialPermissions()
        ]
        authorize_security_group_request = ecs_models.AuthorizeSecurityGroupRequest(
            region_id=region_id,
            security_group_id=security_group_id,
            permissions=permissions,
        )
        client.authorize_security_group_with_options(
            authorize_security_group_request, runtime
        )
        return security_group_id

    @staticmethod
    def getInitialPermissions() -> List[Dict]:
        """
        get initial permissions
        TCP22, RDP3389, ICMP-1, TCP5000, TCP/UDP8388-8389, TCP1723, TCP10086, UDP500, UDP4500
        @return: list of permissons
        """
        return [
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "22/22",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "SSH",
            },
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "3389/3389",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "RDP",
            },
            {
                "policy": "accept",
                "ip_protocol": "ICMP",
                "port_range": "-1/-1",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "ICMP",
            },
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "5000/5000",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "FlaskHttp",
            },
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "8388/8388",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "shadow",
            },
            {
                "policy": "accept",
                "ip_protocol": "UDP",
                "port_range": "8388/8388",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "shadow",
            },
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "8389/8389",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "shadow",
            },
            {
                "policy": "accept",
                "ip_protocol": "UDP",
                "port_range": "8389/8389",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "shadow",
            },
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "1723/1723",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "pptp",
            },
            {
                "policy": "accept",
                "ip_protocol": "TCP",
                "port_range": "10086/10086",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "v2ray",
            },
            {
                "policy": "accept",
                "ip_protocol": "UDP",
                "port_range": "500/500",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "ikev2",
            },
            {
                "policy": "accept",
                "ip_protocol": "UDP",
                "port_range": "4500/4500",
                "source_cidr_ip": "0.0.0.0/0",
                "description": "ikev2",
            },
        ]

    @staticmethod
    def getAliveTime(alive_minutes: int) -> str:
        """
        get alive time after minutes
        @param: alive_minutes
        @return: UTC+0, format should be yyyy-MM-ddTHH:mm:00Z
        """
        if alive_minutes < 30:
            alive_minutes = 30

        utc_now = datetime.utcnow()
        utc_later = utc_now + timedelta(minutes=alive_minutes)
        return utc_later.strftime('%Y-%m-%dT%H:%M:00Z')

    @staticmethod
    def getUserDataWithWeb(user_data_base64: str) -> str:
        """
        get user data with web service
        @param: user_data_base64
        @return: user_data_base64
        """
        user_data = base64ToUnistr(user_data_base64)
        # web data
        web_path = os.path.join(os.path.dirname(__file__), "user_data_web")
        with open(web_path, "r") as f:
            web_data = f.read()
            return unistrToBase64(f"{user_data}\n\n{web_data}")

if __name__ == "__main__":
    pass
