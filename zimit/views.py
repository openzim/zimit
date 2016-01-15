from cornice import Service
from colander import MappingSchema, SchemaNode, String

webpage = Service(name='website', path='/website')
home = Service(name='home', path='/')

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
    language = SchemaNode(String(), default="en",
                          location="body", type='str')


@webpage.post(schema=WebSiteSchema)
def crawl_new_website(request):
    request.queue.enqueue(
        request.client.create_zim_from_website,
        request.validated,
        timeout=1800)
    request.response.status_code = 201
    return {'success': True}
