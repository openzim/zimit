import os.path
import shutil
import tempfile
import urlparse

from pyramid_mailer import Mailer
from slugify import slugify

from zimit.messages import ZimReadyMessage
from zimit import utils

HTTRACK_BIN = "/usr/bin/httrack"
DEFAULT_AUTHOR = "BSF"


class ZimCreator(object):

    def __init__(self, settings):
        if 'zimit.zimwriterfs_bin' not in settings:
            raise ValueError('Please define zimit.zimwriterfs_bin config.')

        zimwriterfs_bin = settings['zimit.zimwriterfs_bin']
        httrack_bin = settings.get('zimit.httrack_bin', HTTRACK_BIN)
        output_location = settings.get('zimit.output_location')

        utils.ensure_paths_exists(
            zimwriterfs_bin, httrack_bin, output_location)

        self.zimwriterfs_bin = settings.get('zimit.zimwriterfs_bin')
        self.httrack_bin = httrack_bin
        self.author = settings.get('zimit.default_author', DEFAULT_AUTHOR)
        self.output_location = settings.get('zimit.output_location')
        self.output_url = settings.get('zimit.output_url')
        self.settings = settings

    def download_website(self, url):
            path = tempfile.mkdtemp("website")
            p = utils.spawn("%s --path %s %s" % (self.httrack_bin, path, url))
            p.wait()
            shutil.copy('./favicon.ico', path)
            return path

    def create_zim(self, html_location, config):
        zim_file = "{slug}.zim".format(slug=slugify(config['url']))
        config.update({
            'bin': self.zimwriterfs_bin,
            'location': html_location,
            'output': os.path.join(self.output_location, zim_file),
            'icon': 'favicon.ico',
            'publisher': self.author,
        })

        # Spawn zimwriterfs with the correct options.
        p = utils.spawn(
            ('{bin} -w "{welcome}" -l "{language}" -t "{title}"'
             ' -d "{description}" -f {icon} -c "{author}"'
             ' -p "{publisher}" {location} {output}').format(**config))
        p.wait()
        return zim_file

    def send_email(self, email, zim_file):
        mailer = Mailer.from_settings(self.settings)
        zim_file_url = urlparse.urljoin(self.output_url, zim_file)
        msg = ZimReadyMessage(email, zim_file_url)
        mailer.send_immediately(msg)

    def create_zim_from_website(self, config):
        location = self.download_website(config['url'])
        zim_file = self.create_zim(location, config)
        self.send_email(config['email'], zim_file)
