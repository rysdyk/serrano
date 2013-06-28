import re
import functools
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from restlib2.params import Parametizer, param_cleaners
from restlib2.resources import Resource
from avocado.models import DataContext, DataView, DataQuery
from ..decorators import check_auth
from .. import cors

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

def _get_request_object(request, attrs=None, klass=None, key=None):
    """Resolves the appropriate object for use from the request.

    This applies only to DataView or DataContext objects.
    """
    # Attempt to derive the `attrs` from the request
    if attrs is None:
        if request.method == 'POST':
            attrs = request.data.get(key)
        elif request.method == 'GET':
            attrs = request.GET.get(key)

    # If the `attrs` still could not be resolved, try to get the view or
    # context from the query data if it exists within the request.
    if attrs is None:
        request_data = None

        # Try to read the query data from the request
        if request.method == 'POST':
            request_data = request.data.get('query')
        elif request.method == 'GET':
            request_data = request.GET.get('query')

        # If query data was found in the request, then attempt to create a
        # DataQuery object from it.
        if request_data:
            query = get_request_query(request, attrs=request_data.get('query'))
            
            # Now that the DataQuery object is built, read the appropriate
            # attribute from it, returning None if the attribute wasn't found.
            # Since `context` and `view` are the keys used in get_request_view
            # and get_request_context respectively, we can use the key directly
            # to access the context and view properties of the DataQuery model.
            key_object = getattr(query, key, None)
            
            # If the property exists and is not None, then read the json from
            # the object as both DataContext and DataView objects will have a
            # json property. This json will be used as the attributes to
            # construct or lookup the klass object going forward. Otherwise,
            # `attrs` will still be None and we are no worse off than we were
            # before attempting to create and read the query.
            if key_object:
                attrs = key_object.json

    # If attrs were supplied or derived from the request, validate them
    # and return as is. This provides support for one-off queries via POST
    # or GET.
    if isinstance(attrs, dict):
        klass.validate(attrs)
        return klass(json=attrs)

    # Ignore archived objects..
    kwargs = {
        'archived': False,
    }

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if hasattr(request, 'user') and request.user.is_authenticated():
        kwargs['user'] = request.user
    else:
        # If no session has been created, this is a cookie-less user agent
        # which is most likely a bot or a non-browser client (e.g. cURL).
        if request.session.session_key is None:
            return klass()
        kwargs['session_key'] = request.session.session_key

    # Assume it is a primary key and fallback to the sesssion
    try:
        kwargs['pk'] = int(attrs)
    except (ValueError, TypeError):
        kwargs['session'] = True

    try:
        return klass.objects.get(**kwargs)
    except klass.DoesNotExist:
        pass

    # Fallback to an instance based off the default template if one exists
    instance = klass()
    default = klass.objects.get_default_template()
    if default:
        instance.json = default.json
    return instance


# Partially applied functions for DataView and DataContext. These functions
# only require the request object and an optional `attrs` dict
get_request_view = functools.partial(_get_request_object,
    klass=DataView, key='view')
get_request_context = functools.partial(_get_request_object,
    klass=DataContext, key='context')

def get_request_query(request, attrs=None):
    """
    Resolves the appropriate DataQuery object for use from the request.
    """
    # Attempt to derive the `attrs` from the request
    if attrs is None:
        if request.method == 'POST':
            attrs = request.data.get('query')
        elif request.method == 'GET':
            attrs = request.GET.get('query')
    
    # If the `attrs` could not be derived from the request(meaning no query
    # was explicity defined), try to construct the query by deriving a context
    # and view from the request.
    if attrs is None:
        json = {}
        
        context = get_request_context(request)
        if context:
            json['context'] = context.json

        view = get_request_view(request)
        if view:
            json['view'] = view.json

        return DataQuery(json)

    # If `attrs` were derived or supplied then validate them and return a
    # DataQuery based off the `attrs`.
    if isinstance(attrs, dict):
        # We cannot simply validate and create a DataQuery based off the 
        # `attrs` as they are now because the context and or view might not
        # contain json but might instead be a pk or some other value. Use the
        # internal helper methods to construct the context and view objects
        # and build the query from the json of those objects' json.
        json = {}

        context = get_request_context(request, attrs=attrs)
        if context:
            json['context'] = context.json
        view = get_request_view(request, attrs=attrs)
        if view:
            json['view'] = view.json

        DataQuery.validate(json)
        return DataQuery(json)

    # Ignore archived objects..
    kwargs = {
        'archived': False,
    }

    # If an authenticated user made the request, filter by the user or
    # fallback to an active session key.
    if hasattr(request, 'user') and request.user.is_authenticated():
        kwargs['user'] = request.user
    else:
        # If not session has been created, this is a cookie-less user agent
        # which is most likely a bot or a non-browser client (e.g. cURL).
        if request.session.session_key is None:
            return DataQuery()
        kwargs['session_key'] = request.session.session_key

    # Assume it is a primary key and fallback to the sesssion
    try:
        kwargs['pk'] = int(attrs)
    except (ValueError, TypeError):
        kwargs['session'] = True

    try:
        return DataQuery.objects.get(**kwargs)
    except DataQuery.DoesNotExist:
        pass

    # Fallback to an instance based off the default template if one exists
    instance = DataQuery()
    default = DataQuery.objects.get_default_template()
    if default:
        instance.json = default.json
    return instance  
     
class BaseResource(Resource):
    param_defaults = None

    parametizer = Parametizer

    @check_auth
    def __call__(self, request, **kwargs):
        return super(BaseResource, self).__call__(request, **kwargs)

    def process_response(self, request, response):
        response = super(BaseResource, self).process_response(request, response)
        response = cors.patch_response(request, response, self.allowed_methods)
        return response

    def get_params(self, request):
        "Returns cleaned set of GET parameters."
        return self.parametizer().clean(request.GET, self.param_defaults)

    def get_context(self, request, attrs=None):
        "Returns a DataContext object based on `attrs` or the request."
        return get_request_context(request, attrs=attrs)

    def get_view(self, request, attrs=None):
        "Returns a DataView object based on `attrs` or the request."
        return get_request_view(request, attrs=attrs)

    def get_query(self, request, attrs=None):
        "Returns a DataQuery object based on `attrs` or the request."
        return get_request_query(request, attrs=attrs)

class PaginatorParametizer(Parametizer):
    page = 1
    per_page = 20

    def clean_page(self, value):
        return param_cleaners.clean_int(value)

    def clean_per_page(self, value):
        return param_cleaners.clean_int(value)


class PaginatorResource(Resource):
    parametizer = PaginatorParametizer

    def get_paginator(self, queryset, per_page):
        return Paginator(queryset, per_page=per_page)

    def get_page_links(self, request, path, page, extra=None):
        "Returns the page links."
        uri = request.build_absolute_uri

        # format string will be expanded below
        params = {
            'page': '{0}',
            'per_page': '{1}',
        }

        if extra:
            for key, value in extra.items():
                # Use the original GET parameter if supplied and if the
                # cleaned value is valid
                if key in request.GET and value is not None and value != '':
                    params.setdefault(key, request.GET.get(key))

        # Stringify parameters. Since these are the original GET params,
        # they do not need to be encoded
        pairs = sorted(['{0}={1}'.format(k, v) for k, v in params.items()])

        # Create path string
        path_format = '{0}?{1}'.format(path, '&'.join(pairs))

        per_page = page.paginator.per_page

        links = {
            'self': {
                'href': uri(path_format.format(page.number, per_page)),
            },
            'base': {
                'href': uri(path),
            }
        }

        if page.has_previous():
            links['prev'] = {
                'href': uri(path_format.format(page.previous_page_number(), per_page)),
            }

        if page.has_next():
            links['next'] = {
                'href': uri(path_format.format(page.next_page_number(), per_page)),
            }

        return links


