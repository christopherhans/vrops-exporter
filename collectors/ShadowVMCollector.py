from BaseCollector import BaseCollector
import os, time
from prometheus_client.core import GaugeMetricFamily
from tools.Resources import Resources
from tools.YamlRead import YamlRead


class ShadowVMCollector(BaseCollector):
    def __init__(self):
        self.iteration = 0
        while not self.iteration:
            time.sleep(5)
            self.get_iteration()
            print("waiting for initial iteration")
        print("done: initial query")
        self.statkey_yaml = YamlRead('collectors/statkey.yaml').run()

    def collect(self):
        if os.environ['DEBUG'] >= '1':
            print('ShadowVMs starts with collecting the metrics')

        g = GaugeMetricFamily('vrops_shadowVMs_stats', 'testtext', labels=['datacenter', 'cluster', 'statkey'])

        #make one big request per stat id with all resource id's in its belly
        for target in self.get_vms_by_target():
            token = self.get_target_tokens()
            token = token[target]
            if not token:
                print("skipping " + target + " in ShadowVMCollector, no token")

            uuids = self.target_hosts[target]
            for statkey_pair in self.statkey_yaml["ShadowVMCollector"]:
                statkey_label = statkey_pair['label']
                statkey = statkey_pair['statkey']
                values = Resources.get_latest_stat_multiple(target, token, uuids, statkey)
                if not values:
                    print("skipping statkey " + str(statkey) + " in ShadowVMCollector, no return")
                    continue
                for value_entry in values:
                    #there is just one, because we are querying latest only
                    metric_value = value_entry['stat-list']['stat'][0]['data'][0]
                    vm_id = value_entry['resourceId']
                    g.add_metric(labels=[self.vms[vm_id]['name'], self.vms[vm_id]['cluster'],
                                     self.vms[vm_id]['datacenter'], statkey_label], value=metric_value)
        yield g
