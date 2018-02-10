# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import sys
import urllib2, urlparse

from resources.lib.common import log, notify

class Main:

    def __init__(self):
        log(2)

        # アドオン
        self.addon = xbmcaddon.Addon()
        # LINE notifyの通知用エンドポイント
        self.endpoint = 'https://notify-api.line.me/api/notify'

    def main(self):
        log(3)
        log(sys.argv)

        # パラメータ抽出
        params = {'action':'','name':'','message':''}
        args = urlparse.parse_qs(sys.argv[2][1:])
        for key in params.keys():
            value = args.get(key, None)
            if value: params[key] = value[0]
        # メイン処理
        if params['action'] is None:
            # テスト用
            log('RunPlugin(%s?action=send&messgage=hello,replace)' % (self.addon.getAddonInfo('id')))
            xbmc.executebuiltin('RunPlugin(%s?action=send&messgage=hello,replace)' % (self.addon.getAddonInfo('id')))
        elif params['action'] == 'send':
            # nameに対応するtokenを取得
            token = 'Z14GaX8dAY4e52gNCy8g3iPc15vMw93NFUOe493LqpZ'
            # メッセージを送信
            self.send(token=token, message=params['message'])

    def send(self, token, message):
        headers = {'Authorization': 'Bearer %s' % token}
        values = {'message': message}
        postdata = urllib.urlencode(values)
        req = urllib2.Request(self.endpoint, headers=headers, data=postdata)
        response = urllib2.urlopen(req)
        # ステータスコードを確認
        status = response.getcode()
        if status == 200:
            notify('Message has been sent')
        else:
            notify('HTTP Error (%d)' % status)

log(1)
if __name__  == '__main__': Main().main()
