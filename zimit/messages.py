from pyramid_mailer.message import Attachment, Message


class ZimReadyMessage(Message):
    def __init__(self, email, zim_link):
        subject = "[ZimIt!] Your zimfile is ready!"

        bdata = "{zim_link}".format(zim_link=zim_link)
        hdata = bdata

        body = Attachment(data=bdata, transfer_encoding="quoted-printable")
        html = Attachment(data=hdata, transfer_encoding="quoted-printable")

        super(ZimReadyMessage, self).__init__(
            subject=subject, body=body, html=html, recipients=[email])
