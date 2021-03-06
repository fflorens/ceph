import os
import json
import sys
from subprocess import check_output

from jinja2 import Template


class Flags:
    NOFORWARD = (1 << 0)
    OBSOLETE = (1 << 1)
    DEPRECATED = (1 << 2)
    MGR = (1 << 3)
    POLL = (1 << 4)
    HIDDEN = (1 << 5)

    VALS = {
        NOFORWARD: 'no_forward',
        OBSOLETE: 'obsolete',
        DEPRECATED: 'deprecated',
        MGR: 'mgr',
        POLL: 'poll',
        HIDDEN: 'hidden',
    }

    def __init__(self, fs):
        self.fs = fs

    def __contains__(self, other):
        return other in str(self)

    def __str__(self):
        keys = Flags.VALS.keys()
        es = {Flags.VALS[k] for k in keys if self.fs & k == k}
        return ', '.join(sorted(es))

    def __bool__(self):
        return bool(str(self))


class CmdParam(object):
    t = {
        'CephInt': 'int',
        'CephString': 'str',
        'CephChoices': 'str',
        'CephPgid': 'str',
        'CephOsdName': 'str',
        'CephPoolname': 'str',
        'CephObjectname': 'str',
        'CephUUID': 'str',
        'CephEntityAddr': 'str',
        'CephIPAddr': 'str',
        'CephName': 'str',
        'CephBool': 'bool',
        'CephFloat': 'float',
        'CephFilepath': 'str',
    }

    bash_example = {
        'CephInt': '1',
        'CephString': 'string',
        'CephChoices': 'choice',
        'CephPgid': '0',
        'CephOsdName': 'osd.0',
        'CephPoolname': 'poolname',
        'CephObjectname': 'objectname',
        'CephUUID': 'uuid',
        'CephEntityAddr': 'entityaddr',
        'CephIPAddr': '0.0.0.0',
        'CephName': 'name',
        'CephBool': 'true',
        'CephFloat': '0.0',
        'CephFilepath': '/path/to/file',
    }

    def __init__(self, type, name, who=None, n=None, req=True, range=None, strings=None,
                 goodchars=None):
        self.type = type
        self.name = name
        self.who = who
        self.n = n == 'N'
        self.req = req != 'false'
        self.range = range.split('|') if range else []
        self.strings = strings.split('|') if strings else []
        self.goodchars = goodchars

        assert who == None

    def help(self):
        advanced = []
        if self.type != 'CephString':
            advanced.append(self.type + ' ')
        if self.range:
            advanced.append('range= ``{}`` '.format('..'.join(self.range)))
        if self.strings:
            advanced.append('strings=({}) '.format(' '.join(self.strings)))
        if self.goodchars:
            advanced.append('goodchars= ``{}`` '.format(self.goodchars))
        if self.n:
            advanced.append('(can be repeated)')

        advanced = advanced or ["(string)"]
        return ' '.join(advanced)

    def mk_example_value(self):
        if self.type == 'CephChoices' and self.strings:
            return self.strings[0]
        if self.range:
            return self.range[0]
        return CmdParam.bash_example[self.type]

    def mk_bash_example(self, simple):
        val = self.mk_example_value()

        if self.type == 'CephBool':
            return '--' + self.name
        if simple:
            if self.type == "CephChoices" and self.strings:
                return val
            elif self.type == "CephString" and self.name != 'who':
                return 'my_' + self.name
            else:
                return CmdParam.bash_example[self.type]
        else:
            return '--{}={}'.format(self.name, val)


class CmdCommand(object):
    def __init__(self, sig, desc, module=None, perm=None, flags=0, poll=None):
        self.sig = [s for s in sig if isinstance(s, str)]
        self.params = sorted([CmdParam(**s) for s in sig if not isinstance(s, str)],
                             key=lambda p: p.req, reverse=True)
        self.help = desc
        self.module = module
        self.perm = perm
        self.flags = Flags(flags)
        self.needs_overload = False

    def prefix(self):
        return ' '.join(self.sig)

    def is_reasonably_simple(self):
        if len(self.params) > 3:
            return False
        if any(p.n for p in self.params):
            return False
        return True

    def mk_bash_example(self):
        simple = self.is_reasonably_simple()
        line = ' '.join(['ceph', self.prefix()] + [p.mk_bash_example(simple) for p in self.params])
        return line


tpl = '''
.. This file is automatically generated. do not modify

{% for command in commands %}

{{ command.prefix() }}
{{ command.prefix() | length * '^' }}

{{ command.help | wordwrap(70)}}

Example command:

.. code-block:: bash

    {{ command.mk_bash_example() }}
{% if command.params %}
Parameters:

{% for param in command.params %}* **{{param.name}}**: {{ param.help() | wordwrap(70) | indent(2) }}
{% endfor %}{% endif %}
Ceph Module:

* *{{ command.module }}*

Required Permissions:

* *{{ command.perm }}*

{% if command.flags %}Command Flags:

* *{{ command.flags }}*
{% endif %}
{% endfor %}

'''

def mk_sigs(all):
    sigs = [CmdCommand(**e) for e in all]
    sigs = [s for s in sigs if 'hidden' not in s.flags]
    sigs = sorted(sigs, key=lambda f: f.sig)


    tm = Template(tpl)
    msg = tm.render(commands=list(sigs))

    print(msg)


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    commands = json.loads(check_output([sys.executable, script_dir + '/../../src/script/gen_static_command_descriptions.py']))
    mk_sigs(commands)
