from pyramid_mailer.message import Attachment, Message
from pyramid_mailer import Mailer


def send_zim_url(settings, email, zim_url):
    """Send an email with a link to one zim file.

    :param settings:
        A pyramid settings object, used by pyramid_mailer.
    :param email:
        The email of the recipient.
    :param zim_url:
        The URL of the zim file.
    """
    mailer = Mailer.from_settings(settings)
    msg = ZimReadyMessage(email, zim_url)
    mailer.send_immediately(msg)


class ZimReadyMessage(Message):
    def __init__(self, email, zim_link):
        subject = "[ZimIt!] Your zimfile is ready!"

        bdata = """
Hi,

You have asked for the creation of a zim file, and it is now ready !

You can access it at the following URL:

    {zim_link}

Cheers,
ZimIt.
""".format(zim_link=zim_link)
        hdata = bdata

        body = Attachment(data=bdata, transfer_encoding="quoted-printable")
        html = Attachment(data=hdata, transfer_encoding="quoted-printable")

        super(ZimReadyMessage, self).__init__(
            subject=subject, body=body, html=html, recipients=[email])
