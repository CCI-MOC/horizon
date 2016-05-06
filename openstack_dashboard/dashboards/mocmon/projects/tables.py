# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import forms
from horizon import tables

from openstack_dashboard import policy


class TenantFilterAction(tables.FilterAction):
    def filter(self, table, tenants, filter_string):
        """Really naive case-insensitive search."""
        # FIXME(gabriel): This should be smarter. Written for demo purposes.
        q = filter_string.lower()

        def comp(tenant):
            if q in tenant.name.lower():
                return True
            return False

        return filter(comp, tenants)

class HostsFilterAction(tables.FilterAction):

   def filter(self, table, vms, filter_string):
        """Naive case-insensitive search."""
        query = filter_string.lower()

        return [item for item in vms
                if query in item.host_name.lower()]


class TenantsTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Name'),
                         link=("horizon:mocmon:projects:detail"),
                         form_field=forms.CharField(max_length=64)
                         )
    id = tables.Column('id', verbose_name=_('Project ID'))


    def get_project_detail_link(self, project):
        # this method is an ugly monkey patch, needed because
        # the column link method does not provide access to the request
        if policy.check((("identity", "identity:get_project")),
                       self.request, target={"project": project}):
            return reverse("horizon:mocmon:projects:detail",
                           args=(project.id,))
        return None

    def __init__(self, request, data=None, needs_form_wrapper=None, **kwargs):
        super(TenantsTable,
              self).__init__(request, data=data,
                             needs_form_wrapper=needs_form_wrapper,
                             **kwargs)
        # see the comment above about ugly monkey patches
        #self.columns['name'].get_link_url = self.get_project_detail_link


    class Meta(object):
        name = "tenants"
        verbose_name = _("Projects")
        table_actions = (TenantFilterAction,)
        pagination_param = "tenant_marker"


class VMsTable(tables.DataTable):
    """
    This class is for the table view that shows all the VMs and its physical hosts
    """
    name = tables.Column('name', verbose_name=_('Instance Name'),
                         form_field=forms.CharField(max_length=64)
                         )
    id = tables.Column('id', verbose_name=_('Instance ID'))
    host_name = tables.Column('host_name',
                              link=("horizon:mocmon:projects:detail"),
                              verbose_name=_('Host Name'))
    created_at = tables.Column('created_at',verbose_name=_('Creation'))
    deleted_at = tables.Column(lambda obj: getattr(obj, 'deleted_at', None),verbose_name=_('Deletion'))


    def get_host_detail_link(self,datum):
        if not hasattr(datum, 'deleted_at'):
            url = "/mocmon/{}".format(datum.host_name)
            print url
            return url
        return None


    def __init__(self, request, data=None, needs_form_wrapper=None, **kwargs):
        super(VMsTable,
              self).__init__(request, data=data,
                             needs_form_wrapper=needs_form_wrapper,
                             **kwargs)
        # see the comment above about ugly monkey patches
        self.columns['host_name'].get_link_url = self.get_host_detail_link
    class Meta(object):
        name = "vms"
        verbose_name = _("Projects")
        table_actions=(HostsFilterAction,)


