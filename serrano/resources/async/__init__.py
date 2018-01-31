from django.conf.urls import include, url

urlpatterns = [
    url(
        r'^export/',
        include('serrano.resources.async.exporter'),
    ),
    url(
        r'^preview/',
        include('serrano.resources.async.preview'),
    ),
    url(
        r'^queries/',
        include('serrano.resources.async.query'),
    ),
]
