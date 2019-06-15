from datetime import datetime
from dateutil.tz import tzutc
from guillotina import app_settings
from guillotina import configure
from guillotina.component._api import get_component_registry
from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IObjectEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IRequestFinishedEvent
from guillotina.interfaces import IResource


_zone = tzutc()


@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
def modified_object(obj, event):
    """Set the modification date of an object."""
    now = datetime.now(tz=_zone)
    obj.modification_date = now


@configure.subscriber(for_=IObjectEvent)
async def object_event_notify(event):
    """Dispatch ObjectEvents to interested adapters."""
    try:
        sitemanager = get_component_registry()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    return await sitemanager.adapters.asubscribers((event.object, event), None)


@configure.subscriber(
    for_=IRequestFinishedEvent)
async def add_http_cache_headers(event):
    """This will add, if configured, the corresponding http cache headers
    on the response of GET requests
    """
    if event.request.method != 'GET':
        # Only cache responses from get requests
        return

    httpcache_settings = app_settings.get('http_cache', {})
    if not httpcache_settings:
        return

    max_age_s = httpcache_settings.get('max_age', 0)
    if not max_age_s:
        return

    cache_control = f'max-age={max_age_s}'

    public = httpcache_settings.get('public', False)
    if public:
        cache_control += ', public'
    else:
        cache_control = ', private'

    httpcache_hdrs = {
        'Cache-Control': cache_control,
        'ETag': 'foobar',  # TODO: what to use here?
    }

    # Add http cache headers on response
    event.response._headers.update(**httpcache_hdrs)
