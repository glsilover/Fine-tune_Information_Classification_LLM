import json
import requests
import time
import urllib
import logging


class HTTPClient(object):

    USER_AGENT = 'XXX'

    def __init__(self, timeout=None, retries=None, http_log_debug=False):
        self.retries = int(retries or 0)
        self.http_log_debug = http_log_debug
        self.timeout = timeout
        self._logger = logging.getLogger(__name__)
        if self.http_log_debug and not self._logger.handlers:
            ch = logging.StreamHandler()
            self._logger.setLevel(logging.ERROR)
            ch.setLevel(logging.ERROR)
            self._logger.addHandler(ch)
            if hasattr(requests, 'logging'):
                requests.logging.getLogger(requests.__name__).addHandler(ch)

    def http_log_req(self, url, method, kwargs):
        if not self.http_log_debug:
            return

        string_parts = ['curl -i']
        if method in ('GET', 'POST', 'DELETE', 'PUT'):
            string_parts.append(' -X %s' % method)

        for element in kwargs['headers']:
            header = ' -H "%s: %s"' % (element, kwargs['headers'][element])
            string_parts.append(header)

        if 'params' in kwargs:
            url = url + '?' + urllib.urlencode(kwargs['params'])
        string_parts.append(' %s' % url)

        if 'data' in kwargs:
            string_parts.append(" -d '%s'" % (kwargs['data']))
        self._logger.debug("\nREQ: %s\n" % "".join(string_parts))

    def http_log_resp(self, resp):
        if not self.http_log_debug:
            return
        self._logger.debug(
            "RESP: [%s] %s\nRESP BODY: %s\n",
            resp.status_code,
            resp.headers,
            resp.text)

    def request(self, url, method, **kwargs):
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['data'] = json.dumps(kwargs['body'])
            del kwargs['body']

        if self.timeout:
            kwargs.setdefault('timeout', self.timeout)
        self.http_log_req(url, method, kwargs)
        resp = requests.request(method, url, **kwargs)
        self.http_log_resp(resp)

        if resp.text:
            try:
                body = json.loads(resp.text)
            except ValueError:
                pass
                body = None
        else:
            body = None

        if resp.status_code >= 400:
            resp.raise_for_status()

        return resp, body

    def _cs_request(self, url, method, **kwargs):
        attempts = 0
        backoff = 1
        while True:
            attempts += 1
            kwargs.setdefault('headers', {})
            try:
                resp, body = self.request(url, method, **kwargs)
                return resp, body

            except requests.exceptions.RequestException as e:
                if attempts > self.retries:
                    raise
            self._logger.debug(
                "Failed attempt(%s of %s), retrying in %s seconds" %
                (attempts, self.retries, backoff))
            time.sleep(backoff)
            backoff *= 2

    def get(self, url, **kwargs):
        return self._cs_request(url, 'GET', **kwargs)

    def patch(self, url, **kwargs):
        return self._cs_request(url, 'PATCH', **kwargs)

    def post(self, url, **kwargs):
        return self._cs_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        return self._cs_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        return self._cs_request(url, 'DELETE', **kwargs)

