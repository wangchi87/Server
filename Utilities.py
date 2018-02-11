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


def packagePublicChatMsg(sender, msg):
    rtnStr = {}
    rtnStr['ChatMsg'] = {'toAll': [sender, msg]}
    return json.dumps(rtnStr)


def packagePrivateChatMsg(sender, receiver, msg):
    # at server end, usrname indicates the name of receiver.
    # at cliend end, usrname indicates the name of sender
    rtnStr = {}
    rtnStr['ChatMsg'] = {'toClient': [sender, receiver, msg]}
    return json.dumps(rtnStr)

def secondsToHMS(seconds):

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    # timeStr = str("%02dh-%02dm-%02ds" % (h, m, s))
    timeStr = str("%02dh-%02dm" % (h, m))
    return timeStr