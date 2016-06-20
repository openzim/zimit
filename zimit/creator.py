import os
import os.path
import shutil
import tempfile
import urlparse

from slugify import slugify

from zimit import utils

HTTRACK_BIN = "/usr/bin/httrack"
DEFAULT_AUTHOR = "ZimIt"


class ZimCreator(object):
    """A synchronous zim creator, using HTTrack to spider websites and
    zimwriterfs to create the zim files.

    Please note that every operation is blocking the interpretor. As such, it
    is recommended to run this operation in a worker if invoked from a website
    view / controller.
    """

    def __init__(self, zimwriterfs_bin, output_location,
                 author=DEFAULT_AUTHOR, httrack_bin=HTTRACK_BIN,
                 log_file=None):
        self.output_location = output_location
        self.author = author
        self.zimwriterfs_bin = zimwriterfs_bin
        self.httrack_bin = httrack_bin
        self.log_file = log_file

        utils.ensure_paths_exists(
            self.zimwriterfs_bin,
            self.httrack_bin,
            self.output_location)

    def _spawn(self, cmd):
        return utils.spawn(cmd, self.log_file)

    def download_website(self, url, destination_path):
        """Downloads the website using HTTrack and wait for the results to
        be available before returning.

        :param url:
            The entry URL of the website to retrieve.

        :param destination_path:
            The absolute location of a folder where the files will be written.
        """
        options = (self.httrack_bin, destination_path, url)
        self._spawn("%s --path %s %s" % options)

    def prepare_website_folder(self, url, input_location):
        """Prepare the website files to make them ready to be embedded in a zim
        file.

        :returns:
            the absolute location of the website folder, ready to be embedded.
        """
        netloc = urlparse.urlparse(url).netloc
        website_folder = os.path.join(input_location, netloc)
        if not os.path.isdir(website_folder):
            raise Exception("Unable to find the website folder!")
        shutil.copy('./favicon.ico', website_folder)
        return website_folder

    def create_zim(self, input_location, output_name, zim_options):
        """Create a zim file out of an existing folder on disk.

        :param input_location:
            The absolute location of the files to be bundled in the zim file.
        :param output_name:
            The name to use to create the zim file.
        :param options:
            Options to pass to the zim creator.
        """

        zim_options.update({
            'bin': self.zimwriterfs_bin,
            'location': input_location,
            'output': os.path.join(self.output_location, output_name),
            'icon': 'favicon.ico',
            'publisher': self.author,
        })

        # Spawn zimwriterfs with the correct options.
        options = (
            '{bin} -w "{welcome}" -l "{language}" -t "{title}"'
            ' -d "{description}" -f {icon} -c "{author}"'
            ' -p "{publisher}" {location} {output}'
        ).format(**zim_options)
        self._spawn(options)
        return output_name

    def create_zim_from_website(self, url, zim_options):
        """Create a zim file from a website. It might take some time.

        The name of the generated zim file is a slugified version of its URL.

        :param url:
            the URL of the website to download.

        :param zim_options:
            A dictionary of options to use when generating the Zim file. They
            are title, language, welcome and description.

        :returns:
            the name of the generated zim_file (relative to the output_folder)
        """
        temporary_location = tempfile.mkdtemp("zimit")
        self.download_website(url, temporary_location)
        website_folder = self.prepare_website_folder(url, temporary_location)
        output_name = "{slug}.zim".format(slug=slugify(url))
        zim_file = self.create_zim(website_folder, output_name, zim_options)
        return zim_file


def load_from_settings(settings, log_file=None):
    """Load the ZimCreator object from the given pyramid settings, converting
    them to actual parameters.

    This is a convenience function for people wanting to create a ZimCreator
    out of a ini file compatible with the pyramid framework.

    :param settings: the dictionary of settings.
    """
    if 'zimit.zimwriterfs_bin' not in settings:
        raise ValueError('Please define zimit.zimwriterfs_bin config.')

    return ZimCreator(
        zimwriterfs_bin=settings['zimit.zimwriterfs_bin'],
        httrack_bin=settings.get('zimit.httrack_bin'),
        output_location=settings.get('zimit.output_location'),
        author=settings.get('zimit.default_author'),
        log_file=log_file
    )
