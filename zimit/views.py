import os
import shlex
import shutil
import subprocess
import tempfile

from cornice import Service
from colander import MappingSchema, SchemaNode, String

HTTRACK_BIN = "/usr/bin/httrack"
DEFAULT_AUTHOR = "BSF"


def spawn(cmd):
    print cmd
    return subprocess.Popen(shlex.split(cmd))


def zim_it(config, settings):
    location = download_website(config['url'], settings)
    create_zim(location, config)


def download_website(url, settings):
    httrack_bin = settings.get('zimit.httrack_bin', HTTRACK_BIN)

    if not os.path.exists(httrack_bin):
        raise OSError('%s does not exist.' % httrack_bin)

    path = tempfile.mkdtemp("website")
    p = spawn("%s --path %s %s" % (httrack_bin, path, url))
    p.wait()
    shutil.copy('./favicon.ico', path)

    return path


def create_zim(location, config, settings):
    if 'zimit.zimwriterfs_bin' not in settings:
        raise ValueError('Please define zimit.zimwriterfs_bin config.')

    if not os.path.exists(settings['zimit.zimwriterfs_bin']):
        raise OSError('%s does not exist.' % settings['zimit.zimwriterfs_bin'])

    config.update({
        'bin': settings['zimit.zimwriterfs_bin'],
        'location': location,
        'output': 'test.zim',
        'icon': 'favicon.ico',
        'publisher': settings.get('zimit.default_author', DEFAULT_AUTHOR),
    })
    # Spawn zimwriterfs with the correct options.
    p = spawn(('{bin} -w "{welcome}" -l "{language}" -t "{title}"'
               ' -d "{description}" -f {icon} -c "{author}"'
               ' -p "{publisher}" {location} {output}').format(**config))
    p.wait()


class WebSiteSchema(MappingSchema):
    url = SchemaNode(String(), location="body", type='str')
    title = SchemaNode(String(), location="body", type='str')
    email = SchemaNode(String(), location="body", type='str')
    description = SchemaNode(String(), default="-",
                             location="body", type='str')
    author = SchemaNode(String(), default=None,
                        location="body", type='str')
    welcome = SchemaNode(String(), default="index.html",
                         location="body", type='str')
    language = SchemaNode(String(), default="en",
                          location="body", type='str')


webpage = Service(name='website', path='/website')


@webpage.post(schema=WebSiteSchema)
def crawl_new_website(request):
    request.queue.enqueue(zim_it, request.validated,
                          request.registry.settings, timeout=1800)
    request.response.status_code = 201
    return {'success': True}
