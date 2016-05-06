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

from horizon import views
from openstack_dashboard import policy



INDEX_URL = "horizon:mocmon:projects:index"



class GrafanaView(views.HorizonTemplateView):
    template_name = 'mocmon/cloudusage/average_usage.html'
    page_title = "Cloud Average Utilization"

    def get_context_data(self,**kwargs):
        context = super(GrafanaView, self).get_context_data(**kwargs)
        panel_list= self.get_grafana_dashboard()
        context['panel_list']=panel_list
        if self.get_admin_grafana_link() is not None:
            context['admin_grafana'] = self.get_admin_grafana_link()
        return context
    def get_grafana_dashboard(self):
        panel_list = []
        panelID_list=[3,1,4,5,2]
        print panelID_list
        for panelID in panelID_list:
            source="http://129.10.3.55:3033/dashboard-solo/db/cloud-usage?panelId={}&fullscreen&theme=light".format(panelID)
            panel_list +=[{"source":source}]
        print panel_list
        return panel_list

    def get_admin_grafana_link(self):
        if policy.check((("identity", "identity:list_projects"),),self.request):
            url = "http://129.10.3.55:3033"
            return url
        return None




