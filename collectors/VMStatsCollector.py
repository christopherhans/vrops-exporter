from BaseCollector import BaseCollector
from prometheus_client.core import GaugeMetricFamily
from tools.Resources import Resources
from tools.helper import yaml_read
from threading import Thread
import os
import json


class VMStatsCollector(BaseCollector):
    def __init__(self):
        self.wait_for_inventory_data()
        # self.post_registered_collector(self.__class__.__name__, g.name)

    def describe(self):
        yield GaugeMetricFamily('vrops_vm_stats', 'testtext')

    def collect(self):
        g = GaugeMetricFamily('vrops_vm_stats', 'testtext',
                              labels=['vccluster', 'datacenter', 'virtualmachine', 'hostsystem', 'project', 'statkey'])
        if os.environ['DEBUG'] >= '1':
            print('VMStatsCollector starts with collecting the metrics')

        project_ids = self.get_project_ids_by_target()
        thread_list = list()
        for target in self.get_vms_by_target():
            project_ids_target = project_ids[target]
            t = Thread(target=self.do_metrics, args=(target, g, project_ids_target))
            thread_list.append(t)
            t.start()
        for t in thread_list:
            t.join()

        yield g

    def do_metrics(self, target, g, project_ids):
        token = self.get_target_tokens()
        token = token[target]
        if not token:
            print("skipping " + target + " in VMStatsCollector, no token")
        uuids = self.target_vms[target]
        with open('uuids','w') as f:
            json.dump(uuids,f)
        statkey_yaml = self.read_collector_config()['statkeys']
        for statkey_pair in statkey_yaml["VMStatsCollector"]:
            statkey_label = statkey_pair['label']
            statkey = statkey_pair['statkey']
            values = Resources.get_latest_stat_multiple(target, token, uuids, statkey)
            if os.environ['DEBUG'] >= '1':
                print(target, statkey)
                print("amount uuids",str(len(uuids)))
                print("fetched     ", str(len(values)))
            if not values:
                print("skipping statkey " + str(statkey) + " in VMStatsCollector, no return")
                continue
            for value_entry in values:
                if 'resourceId' not in value_entry:
                    continue
                # there is just one, because we are querying latest only
                metric_value = value_entry['stat-list']['stat'][0]['data']
                if not metric_value:
                    continue
                vm_id = value_entry['resourceId']
                project_id = "internal"
                if project_ids:
                    for vm_id_project_mapping in project_ids:
                        if vm_id in vm_id_project_mapping:
                            project_id = vm_id_project_mapping[vm_id]
                if vm_id not in self.vms:
                    continue
                g.add_metric(labels=[self.vms[vm_id]['cluster'], self.vms[vm_id]['datacenter'].lower(),
                             self.vms[vm_id]['name'], self.vms[vm_id]['parent_host_name'], project_id, statkey_label],
                             value=metric_value[0])
