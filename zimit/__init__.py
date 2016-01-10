from pyramid.config import Configurator
from pyramid.events import NewRequest
from redis import Redis
from rq import Queue


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.registry.queue = Queue(connection=Redis())

    def attach_objects_to_request(event):
        event.request.queue = config.registry.queue
    config.add_subscriber(attach_objects_to_request, NewRequest)

    config.include("cornice")
    config.scan("zimit.views")
    return config.make_wsgi_app()
