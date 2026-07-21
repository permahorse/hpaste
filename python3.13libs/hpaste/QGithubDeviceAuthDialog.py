import re
import json
from urllib import request
from .nethelper import urlopen_nt
try:
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QSizePolicy, QPushButton, QMessageBox
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    from PySide6.QtCore import Slot, Qt, QUrl
except ImportError:
    from PySide2.QtWidgets import QDialog, QVBoxLayout, QLabel, QSizePolicy, QPushButton, QMessageBox
    from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
    from PySide2.QtCore import Slot, Qt, QUrl

import time


class QGithubDeviceAuthDialog(QDialog):
    def __init__(self, client_id='42e8e8e9d844e45c2d05', hint_username=None, parent=None):
        super(QGithubDeviceAuthDialog, self).__init__(parent=parent)
        self.setWindowTitle('Log into your GitHub account and enter this code')

        self.__webview = QWebEngineView(parent=self)
        self.__webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.__webview.urlChanged.connect(self.on_url_changed)

        self.__infolaabel = QLabel('<p style="font-size:14px">'
                                   '<br>You need to allow hpaste to modify your gists on github. for that you need to log in to your account and authorize hpaste.\n'
                                   '<br>You can do it in <b>any</b> browser, not only in this window. Just go to <a href="https://github.com/login/device">https://github.com/login/device</a> and enter the code below.\n'
                                   '<br>close this window when you are done'
                                   '</p>', parent=self)
        self.__infolaabel.setTextFormat(Qt.RichText)
        self.__infolaabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.__infolaabel.setOpenExternalLinks(True)
        self.__devidlabel = QLabel(parent=self)
        self.__devidlabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        ff = self.__devidlabel.font()
        ff.setPointSize(64)
        self.__devidlabel.setFont(ff)

        self.__reload_button = QPushButton('log in to a different account', parent=self)
        self.__reload_button.clicked.connect(self.reload_button_clicked)

        self.__layout = QVBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.addWidget(self.__infolaabel)
        self.__layout.addWidget(self.__devidlabel)
        self.__layout.addWidget(self.__reload_button)
        self.__layout.addWidget(self.__webview)
        self.__result = None

        # self.setGeometry(512, 256, 1024, 768)
        self.resize(1024, 860)

        # init auth process
        self.__client_id = client_id
        self.__headers = {'User-Agent': 'HPaste', 'Accept': 'application/json', 'charset': 'utf-8', 'Content-Type': 'application/json'}
        self.__hint_username = hint_username

        self.__webprofile = None
        self.__webpage = None

        self.__device_code = None
        self.__interval = None
        self.__await_login_redirect = False
        self.reinit_code()

    def reinit_code(self):
        reqdata = {'client_id': self.__client_id,
                   'scope': 'gist'}
        req = request.Request('https://github.com/login/device/code', data=json.dumps(reqdata).encode('UTF-8'), headers=self.__headers)
        req.get_method = lambda: 'POST'
        code, ret = urlopen_nt(req)
        if code != 200:
            raise RuntimeError('code %d when trying to register device' % code)
        init_data = json.loads(ret.read().decode('UTF-8'))
        print(init_data)
        self.__device_code = init_data['device_code']
        self.__interval = init_data.get('interval', 5)
        url = init_data['verification_uri']

        self.__await_login_redirect = True
        self.__webprofile = QWebEngineProfile(parent=self.__webview)
        self.__webpage = QWebEnginePage(self.__webprofile, parent=self.__webview)  # just to be sure they are deleted in proper order
        self.__webview.setPage(self.__webpage)
        self.__webview.load(QUrl(url))
        self.__devidlabel.setText('code: %s' % (init_data['user_code'],))

    def get_result(self):
        return self.__result

    def closeEvent(self, event):
        # here we assume user has done his part, so lets get checking
        for attempt in range(5):
            reqdata = {'client_id': self.__client_id,
                       'device_code': self.__device_code,
                       'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'}
            req = request.Request('https://github.com/login/oauth/access_token', data=json.dumps(reqdata).encode('UTF-8'), headers=self.__headers)
            req.get_method = lambda: 'POST'
            code, ret = urlopen_nt(req)
            if code == 200:
                rep = json.loads(ret.read().decode('UTF-8'))
                print(rep)
                if 'error' not in rep:  # a SUCC
                    headers = {'User-Agent': 'HPaste',
                                'Authorization': 'Token %s' % rep['access_token'],
                                'Accept': 'application/vnd.github.v3+json'}
                    req = request.Request(r'https://api.github.com/user', headers=headers)
                    usercode, userrep = urlopen_nt(req)
                    if usercode != 200:
                        raise RuntimeError('could not probe! %d' % (usercode,))
                    userdata = json.loads(userrep.read().decode('UTF-8'))
                    print(userdata)

                    self.__result = {'token': rep['access_token'],
                                     'user': userdata['login']}
                    break

                # NO SUCC
                errcode = rep['error']
                if errcode == 'authorization_pending':
                    # note that this error will happen if user just closes down the window
                    break
                elif errcode == 'slow_down':
                    self.__interval = rep.get('interval', self.__interval + 5)
                    time.sleep(self.__interval)
                    continue
                elif errcode == 'expired_token':
                    if QMessageBox.warning(self, 'device code expired', 'it took you too long to enter the code, now it\'s expired.\nWant to retry?', buttons=QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                        event.reject()
                        self.reinit_code()
                        return
                    break
                elif errcode == 'unsupported_grant_type':
                    raise RuntimeError('unsupported grant type. probably github changed API. need to update the plugin')
                elif errcode == 'incorrect_client_credentials':
                    raise RuntimeError('incorect client id. probably pedohorse changed hpaste id for some reason. update the plugin')
                elif errcode == 'incorrect_device_code':
                    if QMessageBox.warning(self, 'bad device code', 'server reported wrong device code\nWant to retry?', buttons=QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                        event.reject()
                        self.reinit_code()
                        return
                    break
                elif errcode == 'access_denied':
                    # means user denied the request
                    break
                else:
                    raise RuntimeError('unexpected error: %s' % (json.dumps(rep),))
            else:
                raise RuntimeError('bad return code. server reported with bad return code %d' % code)
        else:
            if QMessageBox.warning(self, 'unknown error', 'could not manage to check authorization in reasonable amount of attempts\nWant to retry?', buttons=QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                event.reject()
                self.reinit_code()
                return

        return super(QGithubDeviceAuthDialog, self).closeEvent(event)

    @Slot(object)
    def on_url_changed(self, qurl):
        url = qurl.toString()
        print(url)
        if not self.__await_login_redirect:
            return
        if qurl.path() != '/login':
            return
        self.__await_login_redirect = False
        if self.__hint_username is not None:
            if qurl.hasQuery():
                qurl.setQuery('&'.join((qurl.query(), 'login=%s' % self.__hint_username)))
            else:
                qurl.setQuery('login=%s' % self.__hint_username)
        print('redir to %s' % qurl.toString)
        self.__webview.load(qurl)

    @Slot()
    def reload_button_clicked(self):
        self.reinit_code()


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
    w = QGithubDeviceAuthDialog(client_id='42e8e8e9d844e45c2d05', hint_username='ololovich', parent=None)
    res = w.exec_()
    print(res == QGithubDeviceAuthDialog.Accepted)
    print(w.get_result())

