# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import sys, os
import urllib, urllib2, urlparse
import json
import datetime

from resources.lib.common import log, notify, formatted_datetime

class Token:

    def __init__(self, path):
        # ファイル/フォルダのパス
        self.path = path
        # データ読み込み
        self.read()

    def read(self):
        if os.path.isfile(self.path):
            try:
                f = open(self.path,'r')
                self.data = json.loads(f.read(), 'utf-8')
                f.close()
            except ValueError:
                log('broken json: %s' % self.tokenfile)
                self.data = {}
        else:
            self.data = {}

    def write(self):
        f = open(self.path,'w')
        f.write(json.dumps(self.data, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8'))
        f.close()

    def update(self, name=None, token=None):
        if isinstance(name, str): name = name.decode('utf-8')
        if isinstance(token, str): token = token.decode('utf-8')
        if name and token:
            self.data[name] = token
            self.write()

    def delete(self, name=None, token=None):
        if isinstance(name, str): name = name.decode('utf-8')
        if isinstance(token, str): token = token.decode('utf-8')
        if name and token and self.data[name] == token:
            self.data.pop(name)
            self.write()

    def lookup(self, name):
        return self.data.get(name, None)


class Main:

    def __init__(self):
        # アドオン
        self.addon = xbmcaddon.Addon()
        # LINE notifyの通知用エンドポイント
        self.endpoint = 'https://notify-api.line.me/api/notify'
        # ファイル/フォルダのパス
        profile_path = xbmc.translatePath(self.addon.getAddonInfo('profile'))
        plugin_path = xbmc.translatePath(self.addon.getAddonInfo('path'))
        self.resources_path = os.path.join(plugin_path, 'resources')
        self.data_path = os.path.join(self.resources_path, 'data')
        self.cache_path = os.path.join(profile_path, 'cache')
        # トークン初期化
        tokenfile = os.path.join(profile_path, 'tokens.json')
        self.token = Token(tokenfile)
        # settings.xmlを作成
        self.update_settings()
        # 表示するメール数
        self.listsize = self.addon.getSetting('listsize')
        if self.listsize == 'Unlimited':
            self.listsize = 0
        else:
            self.listsize = int(self.listsize)

    def update_settings(self):
        template_file = os.path.join(self.data_path, 'settings.xml')
        f = open(template_file,'r')
        template = f.read()
        f.close()
        settings_file = os.path.join(self.resources_path, 'settings.xml')
        f = open(settings_file,'w')
        namelist = ('|'.join(self.token.data.keys())).decode('utf-8')
        f.write(template.format(tokenname=namelist,tokenname2=namelist))
        f.close()

    def main(self):
        # パラメータ抽出
        params = {'action':'','name':'','message':'','path':''}
        args = urlparse.parse_qs(sys.argv[2][1:])
        for key in params.keys():
            params[key] = value = args.get(key, None)
            if value: params[key] = value[0]
        # メイン処理
        if params['action'] is None:
            startup = self.addon.getSetting('startup')
            if len(self.token.data.keys()) == 0:
                self.addon.openSettings()
            elif startup == "0":
                # トークン一覧を表示
                self.show_tokens()
            else:
                # デフォルトトークンの送信履歴を表示
                xbmc.executebuiltin('Container.Update(%s?action=history,replace)' % (sys.argv[0]))
        elif params['action'] == 'token':
            # トークン一覧を表示
            self.show_tokens()
        elif params['action'] == 'history':
            # メッセージの履歴を表示
            name = params['name'] or self.addon.getSetting('defaultname')
            if name: self.show_history(name)
        elif params['action'] == 'message':
            # メッセージの内容を表示
            name = params['name'] or self.addon.getSetting('defaultname')
            path = params['path']
            if path: self.show_message(name, path)
        elif params['action'] == 'addtoken':
            name = self.addon.getSetting('name')
            token = self.addon.getSetting('token')
            self.token.update(name, token)
            # settings.xmlを更新
            self.update_settings()
            # トークン一覧を表示
            xbmc.executebuiltin('Container.Update(%s?action=token,replace)' % (sys.argv[0]))
        elif params['action'] == 'deletetoken':
            name = params['name']
            token = self.token.lookup(name)
            self.token.delete(name, token)
            # settings.xmlを更新
            self.update_settings()
            # トークン一覧を表示
            xbmc.executebuiltin('Container.Update(%s?action=token,replace)' % (sys.argv[0]))
        elif params['action'] == 'sendmessage':
            name = self.addon.getSetting('recipientname')
            message = self.addon.getSetting('message')
            # 送信データ
            values = {'action':'send', 'name':name, 'message':message}
            postdata = urllib.urlencode(values)
            xbmc.executebuiltin('RunPlugin(%s?%s)' % (sys.argv[0], postdata))
        elif params['action'] == 'send':
            name = params['name'] or self.addon.getSetting('defaultname')
            token = self.token.lookup(name)
            # メッセージを送信
            if token and self.send(token=token, message=params['message']):
                # 送信に成功した場合は履歴に格納
                cache_dir = os.path.join(self.cache_path, name)
                if not os.path.isdir(cache_dir): os.makedirs(cache_dir)
                label = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                path = os.path.join(cache_dir, label)
                f = open(path, 'w')
                f.write(params['message'])
                f.close()

    def show_tokens(self):
        for name in self.token.data.keys():
            listitem = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage="DefaultFolder.png")
            query = '%s?action=history&name=%s' % (sys.argv[0],urllib.quote_plus(name))
            # コンテクストメニュー
            menu = []
            # トークン削除
            menu.append((self.addon.getLocalizedString(32905),'RunPlugin(%s?action=deletetoken&name=%s)' % (sys.argv[0], urllib.quote_plus(name))))
            # アドオン設定
            menu.append((self.addon.getLocalizedString(32900),'Addon.OpenSettings(%s)' % (self.addon.getAddonInfo('id'))))
            # 追加
            listitem.addContextMenuItems(menu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), query, listitem, True)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_history(self, name):
        # ディレクトリ
        cache_dir = os.path.join(self.cache_path, name)
        if not os.path.isdir(cache_dir): os.makedirs(cache_dir)
        #ファイルリスト
        count = 0
        files = sorted(os.listdir(cache_dir), key=lambda message: os.stat(os.path.join(cache_dir,message)).st_mtime, reverse=True)
        for filename in files:
            path = os.path.join(cache_dir, filename)
            if os.path.isfile(path) and not filename.startswith('.'):
                if self.listsize == 0 or count < self.listsize:
                    f = open(path, 'r')
                    content = f.read()
                    f.close()
                    # 日付文字列
                    d = datetime.datetime.fromtimestamp(os.stat(path).st_mtime)
                    dayfmt = self.addon.getLocalizedString(32901)
                    daystr = self.addon.getLocalizedString(32902)
                    fd = formatted_datetime(d, dayfmt, daystr)
                    # リストアイテム
                    label = '%s  %s' % (fd, content.decode('utf-8'))
                    listitem = xbmcgui.ListItem(label, iconImage="DefaultFile.png", thumbnailImage="DefaultFile.png")
                    values = {'action':'message', 'name':name, 'path':path}
                    query = '%s?%s' % (sys.argv[0], urllib.urlencode(values))
                    # コンテクストメニュー
                    menu = []
                    # アドオン設定
                    menu.append((self.addon.getLocalizedString(32900),'Addon.OpenSettings(%s)' % (self.addon.getAddonInfo('id'))))
                    # 追加
                    listitem.addContextMenuItems(menu, replaceItems=True)
                    xbmcplugin.addDirectoryItem(int(sys.argv[1]), query, listitem, False)
                    # カウントアップ
                    count += 1
                else:
                    os.remove(path)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_message(self, name, path):
        # 表示内容
        mtime = datetime.datetime.fromtimestamp(os.stat(path).st_mtime).strftime('%Y-%m-%d  %H:%M:%S')
        content = '[COLOR green]From:[/COLOR] %s\n' % name
        content += '[COLOR green]Date:[/COLOR] %s\n\n' % mtime
        # ファイル読み込み
        f = open(path,'r')
        content += f.read()
        f.close()
        # テキストビューア
        viewer_id = 10147
        # ウィンドウを開く
        xbmc.executebuiltin('ActivateWindow(%s)' % viewer_id)
        # ウィンドウの用意ができるまで1秒待つ
        xbmc.sleep(1000)
        # ウィンドウへ書き込む
        viewer = xbmcgui.Window(viewer_id)
        viewer.getControl(1).setLabel(mtime)
        viewer.getControl(5).setText(content)

    def send(self, token, message):
        headers = {'Authorization': 'Bearer %s' % token}
        values = {'message': message}
        postdata = urllib.urlencode(values)
        try:
            req = urllib2.Request(self.endpoint, headers=headers, data=postdata)
            response = urllib2.urlopen(req)
            status = response.getcode()
            # ステータスコードを確認
            if status == 200:
                notify('Message has been sent')
                return True
            else:
                notify('HTTP Error (%d)' % status)
                return False
        except Exception as e:
            notify('Unknown Error (%s)' % str(e))
            return False

if __name__  == '__main__':
    main = Main()
    if main.addon.getSetting('defaultname'):
        main.main()
    else:
        xbmcaddon.Addon().openSettings()
