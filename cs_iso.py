#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2015, René Moser <mail@renemoser.net>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: cs_iso
short_description: Manages ISO images on Apache CloudStack based clouds.
description:
    - Register and remove ISO images.
version_added: '2.0'
author: "René Moser (@resmo)"
options:
  name:
    description:
      - Name of the ISO.
    required: true
  url:
    description:
      - URL where the ISO can be downloaded from. Required if C(state) is present.
    required: false
    default: null
  os_type:
    description:
      - Name of the OS that best represents the OS of this ISO. If the iso is bootable this parameter needs to be passed. Required if C(state) is present.
    required: false
    default: null
  is_ready:
    description:
      - This flag is used for searching existing ISOs. If set to C(true), it will only list ISO ready for deployment e.g. successfully downloaded and installed. Recommended to set it to C(false).
    required: false
    default: false
    aliases: []
  is_public:
    description:
      - Register the ISO to be publicly available to all users. Only used if C(state) is present.
    required: false
    default: false
  is_featured:
    description:
      - Register the ISO to be featured. Only used if C(state) is present.
    required: false
    default: false
  is_dynamically_scalable:
    description:
      - Register the ISO having XS/VMWare tools installed inorder to support dynamic scaling of VM cpu/memory. Only used if C(state) is present.
    required: false
    default: false
    aliases: []
  checksum:
    description:
      - The MD5 checksum value of this ISO. If set, we search by checksum instead of name.
    required: false
    default: false
  bootable:
    description:
      - Register the ISO to be bootable. Only used if C(state) is present.
    required: false
    default: true
  domain:
    description:
      - Domain the ISO is related to.
    required: false
    default: null
  account:
    description:
      - Account the ISO is related to.
    required: false
    default: null
  project:
    description:
      - Name of the project the ISO to be registered in.
    required: false
    default: null
  zone:
    description:
      - Name of the zone you wish the ISO to be registered or deleted from. If not specified, first zone found will be used.
    required: false
    default: null
  iso_filter:
    description:
      - Name of the filter used to search for the ISO.
    required: false
    default: 'self'
    choices: [ 'featured', 'self', 'selfexecutable','sharedexecutable','executable', 'community' ]
  state:
    description:
      - State of the ISO.
    required: false
    default: 'present'
    choices: [ 'present', 'absent' ]
extends_documentation_fragment: cloudstack
'''

EXAMPLES = '''
# Register an ISO if ISO name does not already exist.
- local_action:
    module: cs_iso
    name: Debian 7 64-bit
    url: http://mirror.switch.ch/ftp/mirror/debian-cd/current/amd64/iso-cd/debian-7.7.0-amd64-netinst.iso
    os_type: Debian GNU/Linux 7(64-bit)

# Register an ISO with given name if ISO md5 checksum does not already exist.
- local_action:
    module: cs_iso
    name: Debian 7 64-bit
    url: http://mirror.switch.ch/ftp/mirror/debian-cd/current/amd64/iso-cd/debian-7.7.0-amd64-netinst.iso
    os_type: Debian GNU/Linux 7(64-bit)
    checksum: 0b31bccccb048d20b551f70830bb7ad0

# Remove an ISO by name
- local_action:
    module: cs_iso
    name: Debian 7 64-bit
    state: absent

# Remove an ISO by checksum
- local_action:
    module: cs_iso
    name: Debian 7 64-bit
    checksum: 0b31bccccb048d20b551f70830bb7ad0
    state: absent
'''

RETURN = '''
---
name:
  description: Name of the ISO.
  returned: success
  type: string
  sample: Debian 7 64-bit
displaytext:
  description: Text to be displayed of the ISO.
  returned: success
  type: string
  sample: Debian 7.7 64-bit minimal 2015-03-19
zone:
  description: Name of zone the ISO is registered in.
  returned: success
  type: string
  sample: zuerich
status:
  description: Status of the ISO.
  returned: success
  type: string
  sample: Successfully Installed
is_ready:
  description: True if the ISO is ready to be deployed from.
  returned: success
  type: boolean
  sample: true
checksum:
  description: MD5 checksum of the ISO.
  returned: success
  type: string
  sample: 0b31bccccb048d20b551f70830bb7ad0
created:
  description: Date of registering.
  returned: success
  type: string
  sample: 2015-03-29T14:57:06+0200
domain:
  description: Domain the ISO is related to.
  returned: success
  type: string
  sample: example domain
account:
  description: Account the ISO is related to.
  returned: success
  type: string
  sample: example account
project:
  description: Project the ISO is related to.
  returned: success
  type: string
  sample: example project
'''

try:
    from cs import CloudStack, CloudStackException, read_config
    has_lib_cs = True
except ImportError:
    has_lib_cs = False

# import cloudstack common
class AnsibleCloudStack:

    def __init__(self, module):
        if not has_lib_cs:
            module.fail_json(msg="python library cs required: pip install cs")

        self.result = {
            'changed': False,
        }

        self.module = module
        self._connect()

        self.domain = None
        self.account = None
        self.project = None
        self.ip_address = None
        self.zone = None
        self.vm = None
        self.os_type = None
        self.hypervisor = None
        self.capabilities = None


    def _connect(self):
        api_key = self.module.params.get('api_key')
        api_secret = self.module.params.get('secret_key')
        api_url = self.module.params.get('api_url')
        api_http_method = self.module.params.get('api_http_method')
        api_timeout = self.module.params.get('api_timeout')

        if api_key and api_secret and api_url:
            self.cs = CloudStack(
                endpoint=api_url,
                key=api_key,
                secret=api_secret,
                timeout=api_timeout,
                method=api_http_method
                )
        else:
            self.cs = CloudStack(**read_config())


    def get_or_fallback(self, key=None, fallback_key=None):
        value = self.module.params.get(key)
        if not value:
            value = self.module.params.get(fallback_key)
        return value


    # TODO: for backward compatibility only, remove if not used anymore
    def _has_changed(self, want_dict, current_dict, only_keys=None):
        return self.has_changed(want_dict=want_dict, current_dict=current_dict, only_keys=only_keys)


    def has_changed(self, want_dict, current_dict, only_keys=None):
        for key, value in want_dict.iteritems():

            # Optionally limit by a list of keys
            if only_keys and key not in only_keys:
                continue;

            # Skip None values
            if value is None:
                continue;

            if key in current_dict:

                # API returns string for int in some cases, just to make sure
                if isinstance(value, int):
                    current_dict[key] = int(current_dict[key])
                elif isinstance(value, str):
                    current_dict[key] = str(current_dict[key])

                # Only need to detect a singe change, not every item
                if value != current_dict[key]:
                    return True
        return False


    def _get_by_key(self, key=None, my_dict={}):
        if key:
            if key in my_dict:
                return my_dict[key]
            self.module.fail_json(msg="Something went wrong: %s not found" % key)
        return my_dict


    def get_project(self, key=None):
        if self.project:
            return self._get_by_key(key, self.project)

        project = self.module.params.get('project')
        if not project:
            return None
        args = {}
        args['account'] = self.get_account(key='name')
        args['domainid'] = self.get_domain(key='id')
        projects = self.cs.listProjects(**args)
        if projects:
            for p in projects['project']:
                if project.lower() in [ p['name'].lower(), p['id'] ]:
                    self.project = p
                    return self._get_by_key(key, self.project)
        self.module.fail_json(msg="project '%s' not found" % project)


    def get_ip_address(self, key=None):
        if self.ip_address:
            return self._get_by_key(key, self.ip_address)

        ip_address = self.module.params.get('ip_address')
        if not ip_address:
            self.module.fail_json(msg="IP address param 'ip_address' is required")

        args = {}
        args['ipaddress'] = ip_address
        args['account'] = self.get_account(key='name')
        args['domainid'] = self.get_domain(key='id')
        args['projectid'] = self.get_project(key='id')
        ip_addresses = self.cs.listPublicIpAddresses(**args)

        if not ip_addresses:
            self.module.fail_json(msg="IP address '%s' not found" % args['ipaddress'])

        self.ip_address = ip_addresses['publicipaddress'][0]
        return self._get_by_key(key, self.ip_address)


    def get_vm(self, key=None):
        if self.vm:
            return self._get_by_key(key, self.vm)

        vm = self.module.params.get('vm')
        if not vm:
            self.module.fail_json(msg="Virtual machine param 'vm' is required")

        args = {}
        args['account'] = self.get_account(key='name')
        args['domainid'] = self.get_domain(key='id')
        args['projectid'] = self.get_project(key='id')
        args['zoneid'] = self.get_zone(key='id')
        vms = self.cs.listVirtualMachines(**args)
        if vms:
            for v in vms['virtualmachine']:
                if vm in [ v['name'], v['displayname'], v['id'] ]:
                    self.vm = v
                    return self._get_by_key(key, self.vm)
        self.module.fail_json(msg="Virtual machine '%s' not found" % vm)


    def get_zone(self, key=None):
        if self.zone:
            return self._get_by_key(key, self.zone)

        zone = self.module.params.get('zone')
        zones = self.cs.listZones()

        # use the first zone if no zone param given
        if not zone:
            self.zone = zones['zone'][0]
            return self._get_by_key(key, self.zone)

        if zones:
            for z in zones['zone']:
                if zone in [ z['name'], z['id'] ]:
                    self.zone = z
                    return self._get_by_key(key, self.zone)
        self.module.fail_json(msg="zone '%s' not found" % zone)


    def get_os_type(self, key=None):
        if self.os_type:
            return self._get_by_key(key, self.zone)

        os_type = self.module.params.get('os_type')
        if not os_type:
            return None

        os_types = self.cs.listOsTypes()
        if os_types:
            for o in os_types['ostype']:
                if os_type in [ o['description'], o['id'] ]:
                    self.os_type = o
                    return self._get_by_key(key, self.os_type)
        self.module.fail_json(msg="OS type '%s' not found" % os_type)


    def get_hypervisor(self):
        if self.hypervisor:
            return self.hypervisor

        hypervisor = self.module.params.get('hypervisor')
        hypervisors = self.cs.listHypervisors()

        # use the first hypervisor if no hypervisor param given
        if not hypervisor:
            self.hypervisor = hypervisors['hypervisor'][0]['name']
            return self.hypervisor

        for h in hypervisors['hypervisor']:
            if hypervisor.lower() == h['name'].lower():
                self.hypervisor = h['name']
                return self.hypervisor
        self.module.fail_json(msg="Hypervisor '%s' not found" % hypervisor)


    def get_account(self, key=None):
        if self.account:
            return self._get_by_key(key, self.account)

        account = self.module.params.get('account')
        if not account:
            return None

        domain = self.module.params.get('domain')
        if not domain:
            self.module.fail_json(msg="Account must be specified with Domain")

        args = {}
        args['name'] = account
        args['domainid'] = self.get_domain(key='id')
        args['listall'] = True
        accounts = self.cs.listAccounts(**args)
        if accounts:
            self.account = accounts['account'][0]
            return self._get_by_key(key, self.account)
        self.module.fail_json(msg="Account '%s' not found" % account)


    def get_domain(self, key=None):
        if self.domain:
            return self._get_by_key(key, self.domain)

        domain = self.module.params.get('domain')
        if not domain:
            return None

        args = {}
        args['listall'] = True
        domains = self.cs.listDomains(**args)
        if domains:
            for d in domains['domain']:
                if d['path'].lower() in [ domain.lower(), "root/" + domain.lower(), "root" + domain.lower() ] :
                    self.domain = d
                    return self._get_by_key(key, self.domain)
        self.module.fail_json(msg="Domain '%s' not found" % domain)


    def get_tags(self, resource=None):
        existing_tags = self.cs.listTags(resourceid=resource['id'])
        if existing_tags:
            return existing_tags['tag']
        return []


    def _delete_tags(self, resource, resource_type, tags):
        existing_tags = resource['tags']
        tags_to_delete = []
        for existing_tag in existing_tags:
            if existing_tag['key'] in tags:
                if existing_tag['value'] != tags[key]:
                    tags_to_delete.append(existing_tag)
            else:
                tags_to_delete.append(existing_tag)
        if tags_to_delete:
            self.result['changed'] = True
            if not self.module.check_mode:
                args = {}
                args['resourceids']  = resource['id']
                args['resourcetype'] = resource_type
                args['tags']         = tags_to_delete
                self.cs.deleteTags(**args)


    def _create_tags(self, resource, resource_type, tags):
        tags_to_create = []
        for i, tag_entry in enumerate(tags):
            tag = {
                'key':   tag_entry['key'],
                'value': tag_entry['value'],
            }
            tags_to_create.append(tag)
        if tags_to_create:
            self.result['changed'] = True
            if not self.module.check_mode:
                args = {}
                args['resourceids']  = resource['id']
                args['resourcetype'] = resource_type
                args['tags']         = tags_to_create
                self.cs.createTags(**args)


    def ensure_tags(self, resource, resource_type=None):
        if not resource_type or not resource:
            self.module.fail_json(msg="Error: Missing resource or resource_type for tags.")

        if 'tags' in resource:
            tags = self.module.params.get('tags')
            if tags is not None:
                self._delete_tags(resource, resource_type, tags)
                self._create_tags(resource, resource_type, tags)
                resource['tags'] = self.get_tags(resource)
        return resource


    def get_capabilities(self, key=None):
        if self.capabilities:
            return self._get_by_key(key, self.capabilities)
        capabilities = self.cs.listCapabilities()
        self.capabilities = capabilities['capability']
        return self._get_by_key(key, self.capabilities)


    # TODO: for backward compatibility only, remove if not used anymore
    def _poll_job(self, job=None, key=None):
        return self.poll_job(job=job, key=key)


    def poll_job(self, job=None, key=None):
        if 'jobid' in job:
            while True:
                res = self.cs.queryAsyncJobResult(jobid=job['jobid'])
                if res['jobstatus'] != 0 and 'jobresult' in res:
                    if 'errortext' in res['jobresult']:
                        self.module.fail_json(msg="Failed: '%s'" % res['jobresult']['errortext'])
                    if key and key in res['jobresult']:
                        job = res['jobresult'][key]
                    break
                time.sleep(2)
        return job


class AnsibleCloudStackIso(AnsibleCloudStack):

    def __init__(self, module):
        AnsibleCloudStack.__init__(self, module)
        self.iso = None

    def register_iso(self):
        iso = self.get_iso()
        if not iso:

            args                            = {}
            args['zoneid']                  = self.get_zone('id')
            args['domainid']                = self.get_domain('id')
            args['account']                 = self.get_account('name')
            args['projectid']               = self.get_project('id')
            args['bootable']                = self.module.params.get('bootable')
            args['ostypeid']                = self.get_os_type('id')
            args['name']                    = self.module.params.get('name')
            args['displaytext']             = self.module.params.get('name')
            args['checksum']                = self.module.params.get('checksum')
            args['isdynamicallyscalable']   = self.module.params.get('is_dynamically_scalable')
            args['isfeatured']              = self.module.params.get('is_featured')
            args['ispublic']                = self.module.params.get('is_public')

            if args['bootable'] and not args['ostypeid']:
                self.module.fail_json(msg="OS type 'os_type' is requried if 'bootable=true'.")

            args['url'] = self.module.params.get('url')
            if not args['url']:
                self.module.fail_json(msg="URL is requried.")

            self.result['changed'] = True
            if not self.module.check_mode:
                res = self.cs.registerIso(**args)
                iso = res['iso'][0]
        return iso


    def get_iso(self):
        if not self.iso:

            args                = {}
            args['isready']     = self.module.params.get('is_ready')
            args['isofilter']   = self.module.params.get('iso_filter')
            args['domainid']    = self.get_domain('id')
            args['account']     = self.get_account('name')
            args['projectid']   = self.get_project('id')
            args['zoneid']      = self.get_zone('id')

            # if checksum is set, we only look on that.
            checksum = self.module.params.get('checksum')
            if not checksum:
                args['name'] = self.module.params.get('name')

            isos = self.cs.listIsos(**args)
            if isos:
                if not checksum:
                    self.iso = isos['iso'][0]
                else:
                    for i in isos['iso']:
                        if i['checksum'] == checksum:
                            self.iso = i
                            break
        return self.iso


    def remove_iso(self):
        iso = self.get_iso()
        if iso:
            self.result['changed'] = True

            args                = {}
            args['id']          = iso['id']
            args['projectid']   = self.get_project('id')
            args['zoneid']      = self.get_zone('id')

            if not self.module.check_mode:
                res = self.cs.deleteIso(**args)
        return iso


    def get_result(self, iso):
        if iso:
            if 'displaytext' in iso:
                self.result['displaytext'] = iso['displaytext']
            if 'name' in iso:
                self.result['name'] = iso['name']
            if 'zonename' in iso:
                self.result['zone'] = iso['zonename']
            if 'checksum' in iso:
                self.result['checksum'] = iso['checksum']
            if 'status' in iso:
                self.result['status'] = iso['status']
            if 'isready' in iso:
                self.result['is_ready'] = iso['isready']
            if 'created' in iso:
                self.result['created'] = iso['created']
            if 'project' in iso:
                self.result['project'] = iso['project']
            if 'domain' in iso:
                self.result['domain'] = iso['domain']
            if 'account' in iso:
                self.result['account'] = iso['account']
        return self.result


def main():
    module = AnsibleModule(
        argument_spec = dict(
            name = dict(required=True),
            url = dict(default=None),
            os_type = dict(default=None),
            zone = dict(default=None),
            iso_filter = dict(default='self', choices=[ 'featured', 'self', 'selfexecutable','sharedexecutable','executable', 'community' ]),
            domain = dict(default=None),
            account = dict(default=None),
            project = dict(default=None),
            checksum = dict(default=None),
            is_ready = dict(choices=BOOLEANS, default=False),
            bootable = dict(choices=BOOLEANS, default=True),
            is_featured = dict(choices=BOOLEANS, default=False),
            is_dynamically_scalable = dict(choices=BOOLEANS, default=False),
            state = dict(choices=['present', 'absent'], default='present'),
            api_key = dict(default=None),
            api_secret = dict(default=None, no_log=True),
            api_url = dict(default=None),
            api_http_method = dict(choices=['get', 'post'], default='get'),
            api_timeout = dict(type='int', default=10),
        ),
        required_together = (
            ['api_key', 'api_secret', 'api_url'],
        ),
        supports_check_mode=True
    )

    if not has_lib_cs:
        module.fail_json(msg="python library cs required: pip install cs")

    try:
        acs_iso = AnsibleCloudStackIso(module)

        state = module.params.get('state')
        if state in ['absent']:
            iso = acs_iso.remove_iso()
        else:
            iso = acs_iso.register_iso()

        result = acs_iso.get_result(iso)

    except CloudStackException, e:
        module.fail_json(msg='CloudStackException: %s' % str(e))

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
