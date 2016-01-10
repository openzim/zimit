import os
import shlex
import shutil
import subprocess
import tempfile
from pyramid_mailer import Mailer
from slugify import slugify

from zimit.messages import ZimReadyMessage


HTTRACK_BIN = "/usr/bin/httrack"
DEFAULT_AUTHOR = "BSF"


def spawn(cmd):
    """Quick shortcut to spawn a command on the filesystem"""
    return subprocess.Popen(shlex.split(cmd))


class ZimCreator(object):

    def __init__(self, settings):
        if 'zimit.zimwriterfs_bin' not in settings:
            raise ValueError('Please define zimit.zimwriterfs_bin config.')

        if not os.path.exists(settings['zimit.zimwriterfs_bin']):
            msg = '%s does not exist.' % settings['zimit.zimwriterfs_bin']
            raise OSError(msg)

        httrack_bin = settings.get('zimit.httrack_bin', HTTRACK_BIN)
        if not os.path.exists(httrack_bin):
            raise OSError('%s does not exist.' % httrack_bin)

        self.zimwriterfs_bin = settings.get('zimit.zimwriterfs_bin')
        self.httrack_bin = httrack_bin
        self.author = settings.get('zimit.default_author', DEFAULT_AUTHOR)
        self.settings = settings

    def download_website(self, url):
            path = tempfile.mkdtemp("website")
            p = spawn("%s --path %s %s" % (self.httrack_bin, path, url))
            p.wait()
            shutil.copy('./favicon.ico', path)
            return path

    def create_zim(self, html_location, config):
        zim_file = "{slug}.zim".format(slug=slugify(config['url']))
        config.update({
            'bin': self.zimwriterfs_bin,
            'location': html_location,
            'output': zim_file,
            'icon': 'favicon.ico',
            'publisher': self.author,
        })

        # Spawn zimwriterfs with the correct options.
        p = spawn(('{bin} -w "{welcome}" -l "{language}" -t "{title}"'
                   ' -d "{description}" -f {icon} -c "{author}"'
                   ' -p "{publisher}" {location} {output}').format(**config))
        p.wait()
        return zim_file

    def send_email(self, email, zim_file):
        mailer = Mailer.from_settings(self.settings)
        msg = ZimReadyMessage(email, zim_file)
        mailer.send_immediately(msg)

    def create_zim_from_website(self, config):
        location = self.download_website(config['url'])
        zim_file = self.create_zim(location, config)
        self.send_email(config['email'], zim_file)
