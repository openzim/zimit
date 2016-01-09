import tempfile
import subprocess
import shlex
import shutil

from cornice import Service
from colander import MappingSchema, SchemaNode, String, drop

zimwriterfs_bin = "/home/alexis/dev/openzim/zimwriterfs/zimwriterfs"
httrack_bin = "/usr/bin/httrack"
default_author = "Alexis Metaireau"


def spawn(cmd):
    print cmd
    return subprocess.Popen(shlex.split(cmd))

def zim_it(config):
    location = download_website(config['url'])
    create_zim(location, config)

def download_website(url):
    path = tempfile.mkdtemp("website")
    p = spawn("%s --path %s %s" % (httrack_bin, path, url))
    p.wait()
    shutil.copy('/home/alexis/dev/zimit/favicon.ico', path)

    return path

def create_zim(location, config):
    config.update({
        'bin': zimwriterfs_bin,
        'location': location,
        'output': 'test.zim',
        'icon': 'favicon.ico',
        'publisher': 'Alexis Metaireau',
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
    author = SchemaNode(String(), default=default_author,
                        location="body", type='str')
    welcome = SchemaNode(String(), default="index.html",
                         location="body", type='str')
    language = SchemaNode(String(), default="en",
                          location="body", type='str')


webpage = Service(name='website', path='/website')

@webpage.post(schema=WebSiteSchema)
def crawl_new_website(request):
    request.queue.enqueue(zim_it, request.validated, timeout=1800)
    request.response.status_code = 201
    return {'success': True}
