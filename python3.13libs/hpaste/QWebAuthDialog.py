raise NotImplementedError()
# TODO: Ran into temporary deadend: This requires exposing client_secret for github authentication... so no point using it now
# TODO: need to implement something like device flow, but it is in beta currently
# TODO: or enter personal access token manually

import re
try:
    from PySide6.QtWidgets import QDialog, QVBoxLayout
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtCore import QUrl
except ImportError:
    from PySide2.QtWidgets import QDialog, QVBoxLayout
    from PySide2.QtWebEngineWidgets import QWebEngineView
    from PySide2.QtCore import QUrl


class QWebAuthDialog(QDialog):
    def __init__(self, url, success_re, parent=None):
        super(QWebAuthDialog, self).__init__(parent=parent)

        self.__webview = QWebEngineView(parent=self)
        self.__webview.load(QUrl(url))
        self.__succre = re.compile(success_re)
        self.__webview.urlChanged.connect(self.on_url_changed)

        self.__layout = QVBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.addWidget(self.__webview)
        self.__result = None

    def get_result(self):
        return self.__result

    def on_url_changed(self, qurl):
        url = qurl.toString()
        match = self.__succre.match(url)
        print(url, match)
        if match:
            self.__result = match
            self.accept()


if __name__ == '__main__':  # testing
    import sys
    import string
    import random
    from PySide2.QtWidgets import QApplication
    qapp = QApplication(sys.argv)
    # w = QWebAuthDialog('https://www.google.com', r'https://www.google.com/search\?(.*)')
    webauthstate = ''.join(random.choice(string.ascii_letters) for _ in range(32))
    webauthparms = {'client_id': '42e8e8e9d844e45c2d05',
                    'redirect_uri': 'https://github.com/login/oauth/success',
                    'scope': 'gist',
                    'state': webauthstate}
    w = QWebAuthDialog(url='https://github.com/login/oauth/authorize?' +
                           '&'.join('%s=%s' % (k, v) for k, v in webauthparms.iteritems()),
                       success_re=r'https://github.com/login/oauth/success\?(.*)',
                       parent=None)
    w.setGeometry(512, 256, 1024, 768)
    res = w.exec_()
    print(res == QWebAuthDialog.Accepted)
    print(w.get_result())
    if res == QWebAuthDialog.Accepted:
        print(w.get_result().groups())
    # qapp.exec_()
