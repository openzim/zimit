from pyramid.config import Configurator
from pyramid.events import NewRequest
from redis import Redis
from rq import Queue

from worker import ZimCreator


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.registry.queue = Queue(connection=Redis())

    def attach_objects_to_request(event):
        event.request.queue = config.registry.queue
        event.request.client = ZimCreator(event.request.registry.settings)

    config.add_subscriber(attach_objects_to_request, NewRequest)

    config.include("cornice")
    config.include('pyramid_mailer')
    config.scan("zimit.views")
    return config.make_wsgi_app()
