# coding=utf-8
"""
This version responds to HTTP requests with static HTML files or
directory listings.

*   Run with `python server.py .` (or some other base directory name).
*   Point browser at `http://localhost:9000/some/path`.

    :copyright: (c) 2015 by fangpeng.
    :license: MIT, see LICENSE for more details.
"""
__date__ = '16/6/17'
import os
import urllib
import BaseHTTPServer
import magic


class ServerException(Exception):
    pass


class BaseCase(object):

    def handle_file(self, handler, full_path):
        try:
            content_type = magic.from_file(full_path, mime=True)
            with open(full_path, 'rb') as f:
                content = f.read()
            handler.send_content(content, content_type=content_type)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(full_path, msg)
            handler.handle_error(msg)

    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        assert False, "Not implemented."

    def act(self, handler):
        assert False, "Not implemented."


class CaseNoFile(BaseCase):
    """File or directory does not exist."""

    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))


class CaseExistingFile(BaseCase):
    """File exists"""

    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        self.handle_file(handler, handler.full_path)


class CaseDirectoryIndexFile(BaseCase):
    """Serve index.html page for a directory."""

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
            os.path.isfile(self.index_path(handler))

    def act(self, handler):
        self.handle_file(handler, self.index_path(handler))


class CaseDirectoryNoIndexFile(BaseCase):
    """Serve listing for a directory without an index.html page."""

    # How to display a directory listing.
    Listing_Page = '''\
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title></title>
        </head>
        <body>
        <ul>
        {0}
        </ul>
        </body>
        </html>
        '''

    def list_dir(self, handler, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li><a href="{1}">{0}</a></li>'.format(e, urllib.quote(os.path.join(handler.path, e)))
                       for e in entries if not e.startswith('.')]
            page = self.Listing_Page.format('\n'.join(bullets))
            handler.send_content(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(handler.path, msg)
            handler.handle_error(msg)

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
            not os.path.isfile(self.index_path(handler))

    def act(self, handler):
        self.list_dir(handler, handler.full_path)


class CaseAlwaysFail(BaseCase):
    """Base case if nothing else worked"""

    def test(self, handler):
        return True

    def act(self, handler):
        raise ServerException("Unknown object: '{0}'".format(handler.path))


class CaseCgiFile(BaseCase):
    """something runnable"""

    def run_cgi(self, handler):
        cmd = "python " + handler.full_path
        child_stdin, child_stdout = os.popen2(cmd)
        child_stdin.close()
        data = child_stdout.read()
        child_stdout.close()
        handler.send_content(data)

    def test(self, handler):
        return os.path.isfile(handler.full_path) and \
            handler.full_path.endswith('.py')

    def act(self, handler):
        self.run_cgi(handler)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    If the requested path maps to a file, that file is served.
    If anything goes wrong, an error page is constructed.
    """

    Error_Page = """\
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title></title>
            </head>
            <body>
                <h1>Error Accessing {path} </h1>
                <p>{msg}</p>
            </body>
        </html>
        """

    Cases = [
        CaseNoFile(),
        CaseCgiFile(),
        CaseExistingFile(),
        CaseDirectoryIndexFile(),
        CaseDirectoryNoIndexFile(),
        CaseAlwaysFail()
    ]

    def do_GET(self):
        try:
            self.full_path = os.getcwd() + urllib.unquote(self.path)

            # Figure out how to handle it
            for case in self.Cases:
                if case.test(self):
                    case.act(self)
                    break

        except Exception as msg:
            self.handle_error(msg)

    def handle_error(self, msg, status_code=500):
        content = self.Error_Page.format(path=self.path, msg=msg)
        self.send_content(content, status_code)

    def send_content(self, content, status_code=200, content_type="text/html"):
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == '__main__':
    server_addr = ('', 9000)
    server = BaseHTTPServer.HTTPServer(server_addr, RequestHandler)
    server.serve_forever()

