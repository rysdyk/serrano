from django.conf.urls import url, include
from serrano.conf import dep_supported

# Patterns for the data namespace
data_patterns = [
    url(r'^export/', include('serrano.resources.exporter')),

    url(r'^preview/', include('serrano.resources.preview')),
]

# Patterns for the serrano namespace
serrano_patterns = [
    url(r'^',
        include('serrano.resources')),

    url(r'^async/',
        include(('serrano.resources.async', 'serrano'), namespace='async')),

    url(r'^categories/',
        include('serrano.resources.category')),

    url(r'^concepts/',
        include('serrano.resources.concept')),

    url(r'^contexts/',
        include(('serrano.resources.context', 'serrano'), namespace='contexts')),

    url(r'^data/',
        include((data_patterns, 'serrano'), namespace='data')),

    url(r'^fields/',
        include('serrano.resources.field')),

    url(r'^jobs/',
        include(('serrano.resources.jobs', 'serrano'), namespace='jobs')),

    url(r'^queries/',
        include(('serrano.resources.query', 'serrano'), namespace='queries')),

    url(r'^stats/',
        include(('serrano.resources.stats', 'serrano'), namespace='stats')),

    url(r'^views/',
        include(('serrano.resources.view', 'serrano'), namespace='views')),
]

if dep_supported('objectset'):
    # Patterns for the 'sets' namespace
    serrano_patterns.append(
        url(r'^sets/', include(('serrano.resources.sets', 'serrano'), namespace='sets')))

# Exported patterns
urlpatterns = [
    url(r'^', include((serrano_patterns, 'serrano'), namespace='serrano'))
]
