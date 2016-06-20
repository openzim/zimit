import os
import urlparse

from rq import get_current_job

from zimit.mailer import send_zim_url
from zimit.creator import load_from_settings


def create_zim(settings, options):
    """Call the zim creator and the mailer when it is finished.
    """
    job = get_current_job()
    log_dir = settings.get('zimit.logdir', '/tmp')
    log_file = os.path.join(log_dir, "%s.log" % job.id)
    zim_creator = load_from_settings(settings, log_file)
    zim_file = zim_creator.create_zim_from_website(options['url'], options)
    output_url = settings.get('zimit.output_url')
    zim_url = urlparse.urljoin(output_url, zim_file)
    send_zim_url(settings, options['email'], zim_url)
