import os

from cornice import Service
from colander import MappingSchema, SchemaNode, String
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPNotFound

from zimit.worker import create_zim

website = Service(name='website', path='/website-zim')
home = Service(name='home', path='/')
status = Service(name='status', path='/status/{id}')


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
    job = request.queue.enqueue(
        create_zim,
        request.registry.settings,
        request.validated,
        timeout=1800)
    request.response.status_code = 201
    return {
        'job_id': job.id
    }


@status.get()
def display_status(request):
    job = request.queue.fetch_job(request.matchdict["id"])
    if job is None:
        raise HTTPNotFound()

    log_dir = request.registry.settings.get('zimit.logdir', '/tmp')
    log_file = os.path.join(log_dir, "%s.log" % job.id)

    log_content = None
    if os.path.exists(log_file):
        with open(log_file) as f:
            log_content = f.read()

    return {
        "status": job.status,
        "log": log_content
    }
