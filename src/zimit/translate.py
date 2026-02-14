from warcio.warcwriter import WARCWriter
from warcio.archiveiterator import ArchiveIterator
import argostranslate.package, argostranslate.translate
import bs4
from bs4 import BeautifulSoup
from argostranslate.tags import Tag, translate_tags
from io import BytesIO
import tempfile
import os
from pathlib import Path
import re


from_code = "en"
to_code = "es"

NON_TRANSLATEABLE_TAGS = [
    "address",
    "applet",
    "audio",
    "canvas",
    "code",
    "embed",
    "script",
    "style",
    "time",
    "video",
]
    
# Download and install Argos Translate package
available_packages = argostranslate.package.get_available_packages()
available_package = list(
    filter(
        lambda x: x.from_code == from_code and x.to_code == to_code, available_packages
    )
)[0]
download_path = available_package.download()
argostranslate.package.install_from_path(download_path)


def itag_of_soup(soup):
    if isinstance(soup, bs4.element.NavigableString):
        return str(soup)
    translateable = (
        soup.name not in NON_TRANSLATEABLE_TAGS and soup.get("translate") != "no"
    )
    to_return = Tag([itag_of_soup(content) for content in soup.contents], translateable)
    to_return.soup = soup
    return to_return


def soup_of_itag(itag):
    if isinstance(itag, str):
        return bs4.element.NavigableString(itag)
    soup = itag.soup
    soup.clear()
    soup.extend([soup_of_itag(child) for child in itag.children])
    return soup


def translate_html(underlying_translation, html):
    soup = BeautifulSoup(html, "html.parser")
    itag = itag_of_soup(soup)
    translated_tag = translate_tags(underlying_translation, itag)
    translated_soup = soup_of_itag(translated_tag)
    return translated_soup


def translate(html, target_language="en"):


    # Translate
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = list(filter(lambda x: x.code == from_code, installed_languages))[0]
    to_lang = list(filter(lambda x: x.code == to_code, installed_languages))[0]

    translation = from_lang.get_translation(to_lang)

    translated_soup = translate_html(translation, html)
    return str(translated_soup)


def get_charset(content_type: str | None):
    if not content_type:
        return None
    match = re.search(r"charset=([^\s;]+)", content_type, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip("\"'")


def content_type_with_utf8(content_type: str):
    if re.search(r"charset=", content_type, flags=re.IGNORECASE):
        return re.sub(
            r"charset=([^\s;]+)",
            "charset=utf-8",
            content_type,
            flags=re.IGNORECASE,
        )
    return f"{content_type}; charset=utf-8"



def translate_warc(warc_path, target_language):
    warc_path = Path(warc_path)
    tmp_path = tempfile.NamedTemporaryFile(delete=False).name

    stale_digest_headers = {
        "WARC-Block-Digest",
        "WARC-Payload-Digest",
        "Content-Length",
    }

    with warc_path.open("rb") as inp, open(tmp_path, "wb") as out:
        writer = WARCWriter(out, gzip="".join(warc_path.suffixes[-2:]) == ".warc.gz")

        for record in ArchiveIterator(inp):

            if record.rec_type == "response" and record.http_headers:
                ct = record.http_headers.get_header("Content-Type")

                if ct and "text/html" in ct:
                    html_bytes = record.content_stream().read()
                    charset = get_charset(ct)
                    if charset:
                        html = html_bytes.decode(charset, errors="replace")
                    else:
                        try:
                            html = html_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            html = html_bytes.decode("latin-1", errors="replace")
                    translated = translate(html, target_language)
                    if isinstance(translated, str):
                        translated = translated.encode("utf-8")

                    record.http_headers.replace_header(
                        "Content-Length",
                        str(len(translated))
                    )
                    record.http_headers.replace_header(
                        "Content-Type",
                        content_type_with_utf8(ct),
                    )

                    warc_headers = [
                        (name, value)
                        for (name, value) in record.rec_headers.headers
                        if name not in stale_digest_headers
                    ]
                    new_record = writer.create_warc_record(
                        record.rec_headers.get_header("WARC-Target-URI"),
                        "response",
                        payload=BytesIO(translated),
                        warc_headers_dict=warc_headers,
                        http_headers=record.http_headers,
                    )

                    writer.write_record(new_record)
                    continue

            writer.write_record(record)

    os.replace(tmp_path, str(warc_path))
