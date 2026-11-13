import os


def server_options(environ=os.environ):
    """Waitress options. Behind a reverse proxy set TRUSTED_PROXY_COUNT to the
    exact number of proxies in front of the API (1 for a single Nginx) so the
    real client IP is used for rate limiting. 0 (default) ignores forwarding
    headers entirely, which is correct when clients connect directly."""
    options = dict(host='127.0.0.1', port=int(environ.get('PORT', '8010')), threads=8)
    count = int(environ.get('TRUSTED_PROXY_COUNT', '0'))
    if count > 0:
        options.update(trusted_proxy=environ.get('TRUSTED_PROXY_ADDRESS', '127.0.0.1'),
                       trusted_proxy_count=count,
                       trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host'},
                       clear_untrusted_proxy_headers=True)
    return options
