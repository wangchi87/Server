# -*- coding: utf-8 -*-
import json

def packageMsg(key, msg):
    rtnStr = {}
    rtnStr[key] = msg
    return json.dumps(rtnStr)

def packageSysMsg(key, msg):
    rtnStr = {}
    rtnStr['SysMsg'] = {key: msg}
    return json.dumps(rtnStr)

def packageChatMsg(msg):
    rtnStr = {}
    rtnStr['ChatMsg'] = {'toAll': msg}
    return json.dumps(rtnStr)

def packagePrivateChatMsg(usrnameToSend, msg):
    rtnStr = {}
    rtnStr['ChatMsg'] = {usrnameToSend: msg}
    return json.dumps(rtnStr)

def secondsToHMS(seconds):

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    timeStr = str("%02dh-%02dm-%02ds" % (h, m, s))
    return timeStr