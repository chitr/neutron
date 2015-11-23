#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging

from neutron import context
from neutron.db import agents_db
from neutron.db import db_base_plugin_v2
from neutron.extensions import agent
from neutron.extensions import availability_zone as az_ext
from neutron.tests.common import helpers
from neutron.tests.unit.db import test_db_base_plugin_v2


LOG = logging.getLogger(__name__)


class AZExtensionManager(object):

    def get_resources(self):
        agent.RESOURCE_ATTRIBUTE_MAP['agents'].update(
            az_ext.EXTENDED_ATTRIBUTES_2_0['agents'])
        return (az_ext.Availability_zone.get_resources() +
                agent.Agent.get_resources())

    def get_actions(self):
        return []

    def get_request_extensions(self):
        return []


# This plugin class is just for testing
class AZTestPlugin(db_base_plugin_v2.NeutronDbPluginV2,
                   agents_db.AgentDbMixin):
    supported_extension_aliases = ["agent", "availability_zone"]


class AZTestCommon(test_db_base_plugin_v2.NeutronDbPluginV2TestCase):
    def _register_azs(self):
        self.agent1 = helpers.register_dhcp_agent(host='host1', az='nova1')
        self.agent2 = helpers.register_dhcp_agent(host='host2', az='nova2')
        self.agent3 = helpers.register_l3_agent(host='host2', az='nova2')
        self.agent4 = helpers.register_l3_agent(host='host3', az='nova3')
        self.agent5 = helpers.register_l3_agent(host='host4', az='nova2')


class TestAZAgentCase(AZTestCommon):
    def setUp(self):
        plugin = ('neutron.tests.unit.extensions.'
                  'test_availability_zone.AZTestPlugin')
        ext_mgr = AZExtensionManager()
        super(TestAZAgentCase, self).setUp(plugin=plugin, ext_mgr=ext_mgr)

    def test_list_availability_zones(self):
        self._register_azs()
        helpers.set_agent_admin_state(self.agent3['id'], admin_state_up=False)
        helpers.set_agent_admin_state(self.agent4['id'], admin_state_up=False)
        expected = [
            {'name': 'nova1', 'resource': 'network', 'state': 'available'},
            {'name': 'nova2', 'resource': 'network', 'state': 'available'},
            {'name': 'nova2', 'resource': 'router', 'state': 'available'},
            {'name': 'nova3', 'resource': 'router', 'state': 'unavailable'}]
        res = self._list('availability_zones')
        azs = res['availability_zones']
        self.assertItemsEqual(expected, azs)
        # not admin case
        ctx = context.Context('', 'noadmin')
        res = self._list('availability_zones', neutron_context=ctx)
        azs = res['availability_zones']
        self.assertItemsEqual(expected, azs)

    def test_list_agent_with_az(self):
        helpers.register_dhcp_agent(host='host1', az='nova1')
        res = self._list('agents')
        self.assertEqual('nova1',
            res['agents'][0]['availability_zone'])

    def test_validate_availability_zones(self):
        self._register_azs()
        ctx = context.Context('', 'tenant_id')
        self.plugin.validate_availability_zones(ctx, 'network',
                                                ['nova1', 'nova2'])
        self.plugin.validate_availability_zones(ctx, 'router',
                                                ['nova2', 'nova3'])
        self.assertRaises(az_ext.AvailabilityZoneNotFound,
                          self.plugin.validate_availability_zones,
                          ctx, 'router', ['nova1'])
