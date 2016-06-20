from pyramid.config import Configurator
from pyramid.events import NewRequest
from pyramid.static import static_view

from redis import Redis
from rq import Queue


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.registry.queue = Queue(connection=Redis())

    def attach_objects_to_request(event):
        event.request.queue = config.registry.queue

    config.add_subscriber(attach_objects_to_request, NewRequest)

    config.include("cornice")
    config.include('pyramid_mailer')
    config.scan("zimit.views")

    static = static_view('../app', use_subpath=True, index='index.html')
    config.add_route('catchall_static', '/app/*subpath')
    config.add_view(static, route_name="catchall_static")
    return config.make_wsgi_app()
