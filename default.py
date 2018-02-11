# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import sys
import urllib, urllib2, urlparse

from resources.lib.common import log, notify

# アドオン
ADDON = xbmcaddon.Addon()

# LINE notifyの通知用エンドポイント
ENDPOINT = 'https://notify-api.line.me/api/notify'

def send_message(token, message):
    headers = {'Authorization': 'Bearer %s' % token}
    values = {'message': message}
    postdata = urllib.urlencode(values)
    req = urllib2.Request(ENDPOINT, headers=headers, data=postdata)
    response = urllib2.urlopen(req)
    # ステータスコードを確認
    status = response.getcode()
    if status == 200:
        notify('Message has been sent')
    else:
        notify('HTTP Error (%d)' % status)

if __name__  == '__main__':

    # パラメータ抽出
    params = {'action':'','name':'','message':''}
    args = urlparse.parse_qs(sys.argv[2][1:])
    for key in params.keys():
        params[key] = value = args.get(key, None)
        if value: params[key] = value[0]

    # メイン処理
    if params['action'] is None:
        # テスト用
        values = {'action': 'send', 'message': 'さようなら'}
        postdata = urllib.urlencode(values)
        #xbmc.executebuiltin('RunPlugin(plugin://%s?action=send&message=hello)' % (ADDON.getAddonInfo('id')))
        xbmc.executebuiltin('RunPlugin(plugin://%s?%s)' % (ADDON.getAddonInfo('id'), postdata))
    elif params['action'] == 'send':
        # nameに対応するtokenを取得
        token = 'Z14GaX8dAY4e52gNCy8g3iPc15vMw93NFUOe493LqpZ'
        message = 'こんにちは'
        # メッセージを送信
        send_message(token=token, message=params['message'])
