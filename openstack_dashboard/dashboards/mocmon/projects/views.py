# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
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


from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon.utils import memoized
from horizon import views
from horizon import workflows

from openstack_dashboard import api

from openstack_dashboard import policy


from openstack_dashboard.dashboards.mocmon.projects \
    import tables as project_tables
import host_dicts


from influxdb import InfluxDBClient




INDEX_URL = "horizon:mocmon:projects:index"
DETAIL_URL = "horizon:mocmon:projects:detail"
AGGREGATED_GRAFANA_URL = "http://129.10.3.55:3033/dashboard-solo/db/cloud-usage?panelId={}&fullscreen&theme=light"
HOST_GRAFANA_URL = "http://129.10.3.55:3033/dashboard-solo/db/{}?panelId={}&fullscreen&theme=light"

class IndexView(tables.DataTableView):

    table_class = project_tables.TenantsTable
    template_name = 'mocmon/projects/index.html'
    page_title = _("Projects")

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        """
        For admin user, get all the projects; for memebers, get its own projects
        Returns: keystone tenant object list

        """
        tenants = []
        marker = self.request.GET.get(
            project_tables.TenantsTable._meta.pagination_param, None)

        self._more = False

        if policy.check((("identity", "identity:list_projects"),),
                        self.request):
            domain_context = api.keystone.get_effective_domain_id(self.request)
            try:
                tenants, self._more = api.keystone.tenant_list(
                    self.request,
                    domain=domain_context,
                    paginate=True,
                    marker=marker)
            except Exception:
                exceptions.handle(self.request,
                                  _("Unable to retrieve project list."))
        elif policy.check((("identity", "identity:list_user_projects"),),
                          self.request):
            try:
                tenants, self._more = api.keystone.tenant_list(
                    self.request,
                    user=self.request.user.id,
                    paginate=True,
                    marker=marker,
                    admin=False)
            except Exception:
                exceptions.handle(self.request,
                                  _("Unable to retrieve project information."))
        else:
            msg = \
                _("Insufficient privilege level to view project information.")
            messages.info(self.request, msg)

        if api.keystone.VERSIONS.active >= 3:
            domain_lookup = api.keystone.domain_lookup(self.request)
            for t in tenants:
                t.domain_name = domain_lookup.get(t.domain_id)
        return tenants


class DetailProjectView(tables.DataTableView):
    table_class = project_tables.VMsTable
    template_name = 'mocmon/projects/detail.html'
    page_title = "{{ project.name }}"

    @memoized.memoized_method
    def get_data(self):
        try:
            project_id = self.kwargs['project_id']
            self.request.session['view_project'] = project_id
            #project=self.get_project_data()
            vms,hosts = self.get_vm_data(project_id)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=reverse(INDEX_URL))
        return vms

    def get_vm_data(self, project_id):
        """
        This function is using an influxDB client. If the ip address and password has changed
        this part need to change accordingly.
        Args:
            project_id: id of the project, getting from the url

        Returns: vms is the vm object list, which uses VMInstance class
        hosts is a list of hosts that this project is using

        """
        client = InfluxDBClient('129.10.3.55', 8086, 'root', 'root', 'sensu_db')

        project_vms= 'select instance_name,host_name,created_at,deleted_at \
        from instance_mapping where project_id=\''+project_id+'\' \
        group by instance_id ORDER BY time DESC limit 1;'
        result = client.query(project_vms)
        vms=[]
        hosts=[]
        for index,item in enumerate(result):
            instance_id = result.keys()[index][1]['instance_id']
            name = item[0]['instance_name']
            host_name = item[0]['host_name']
            created_at = item[0]['created_at']
            vm = VMInstance(instance_id,name,host_name,created_at)
            if item[0]['deleted_at'] is not None:
                vm.deleted_at = item[0]['deleted_at']
            print vm
            print "********************************************"
            print "**********************************"
            if item[0]['deleted_at'] is None:
                if vm.host_name not in hosts:
                    hosts.append(vm.host_name)
            vms.append(vm)
            print hosts
        return vms,hosts


    def get_context_data(self, **kwargs):
         context = super(DetailProjectView, self).get_context_data(**kwargs)
         project_id = self.kwargs['project_id']
         vms,hosts = self.get_vm_data(project_id)
         context["hosts"] = hosts
         context["url"] = reverse(INDEX_URL)
         return context


class VMInstance(object):
    '''
    This class is to create VM objects storing VM mapping information
    for table distribution
    '''
    def __init__(self,instance_id,name,host_name,created_at):
        self.id = instance_id
        self.name = name
        self.host_name = host_name
        self.created_at = created_at

class GrafanaView(views.HorizonTemplateView):
    template_name = 'mocmon/projects/average_usage.html'
    page_title = "Cloud Average Utilization"

    def get_context_data(self,**kwargs):
        context = super(GrafanaView, self).get_context_data(**kwargs)
        panel_list= self.get_grafana_dashboard()
        context['panel_list']=panel_list
        return context
    def get_grafana_dashboard(self):
        panel_list = []
        panelID_list=[3,1,4,5,2]
        print panelID_list
        for panelID in panelID_list:
            source = AGGREGATED_GRAFANA_URL.format(panelID)
            #source="http://129.10.3.55:3033/dashboard-solo/db/cloud-usage?panelId={}&fullscreen&theme=light".format(panelID)
            panel_list +=[{"source":source}]
        print panel_list
        return panel_list


class HostGrafanaView(GrafanaView):
    template_name='mocmon/projects/host_usage.html'
    page_title = "Host Usage"

    def get_grafana_dashboard(self):
        host = self.kwargs['host']
        print host
        panel_list=[]
        if host in host_dicts.hosts.keys():
            for item in host_dicts.hosts[host]:
                dashboard = item['dashboard']
                panelID = item['panelID']
                source = HOST_GRAFANA_URL.format(dashboard,panelID)
                #source="http://129.10.3.55:3033/dashboard-solo/db/{}?panelId={}&fullscreen&theme=light".format(dashboard,panelID)
                panel_list +=[{"source":source}]
        return panel_list

    def get_context_data(self,**kwargs):
        context = super(GrafanaView, self).get_context_data(**kwargs)
        panel_list= self.get_grafana_dashboard()
        project_id = self.request.session.get('view_project')
        context['panel_list']=panel_list
        context['project_id']= project_id
        return context