from mailer import send_zim_url
import urlparse


def create_zim(settings, zimCreator, options):
    """Call the zim creator and the mailer when it is finished.
    """
    zim_file = zimCreator.create_zim_from_website(options['url'], options)
    output_url = settings.get('zimit.output_url')
    zim_url = urlparse.urljoin(output_url, zim_file)
    send_zim_url(settings, options['email'], zim_url)
