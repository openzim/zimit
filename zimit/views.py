from cornice import Service
from colander import MappingSchema, SchemaNode, String
from pyramid.httpexceptions import HTTPTemporaryRedirect

from zimit.worker import create_zim

website = Service(name='website', path='/website')
home = Service(name='home', path='/')


@home.get()
def redirect_to_app(request):
    raise HTTPTemporaryRedirect("/app/index.html")


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


@website.post(schema=WebSiteSchema)
def crawl_new_website(request):
    request.queue.enqueue(
        create_zim,
        request.registry.settings,
        request.zim_creator,
        request.validated,
        timeout=1800)
    request.response.status_code = 201
    return {'success': True}
