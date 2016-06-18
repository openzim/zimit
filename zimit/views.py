from cornice import Service
from colander import MappingSchema, SchemaNode, String
from pyramid.response import Response

from zimit import utils

home = Service(name='home', path='/')
webpage = Service(name='website', path='/website')
logs = Service(name='home', path='/logs')


@home.get()
def hello(request):
    return {
        "project_name": "zimit",
        "project_docs": "https://github.com/almet/zimit/"
    }


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
    language = SchemaNode(String(), default="eng",
                          location="body", type='str')


@webpage.post(schema=WebSiteSchema)
def crawl_new_website(request):
    request.queue.enqueue(
        request.client.create_zim_from_website,
        request.validated,
        timeout=1800)
    request.response.status_code = 201
    return {
        'success': True
    }


@logs.get()
def get_logs(request):
    stream_headers = [
        ('Content-Type', 'text/event-stream'),
        ('Cache-Control', 'no-cache')
    ]
    return Response(
        headerlist=stream_headers,
        app_iter=utils.read_fifo("toto")
    )
