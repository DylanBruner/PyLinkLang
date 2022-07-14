import mclink, mctypes, time

Server = mclink.ServerSession('localhost', '0ngZRP26ktb4')
EventSession = mclink.EventSession(Server.server, 'C:\\Users\\brune\\Documents\\Python Projects\\Projects\\McServerHoster\\data\\servers\\MCLinkTester\\logs\\latest.log')

def onPlayerMessage(event):
    if event['command'].startswith('/fakesay'):
        target = event['command'].split('say ')[1].split(' ')[0]
        text   = event['command'].split(f'say {target} ')[1]
        mclink.ServerPlayer(target, Server.server).makeSay(text)
    if event['command'].startswith('/!stopserver'):
        Server.server.command('stop')

def onPlayerAttack(event):
    print(event)
    if event['itemName'] == 'Ban Stick' and event['itemType'] == 'stick':
        Server.server.command(f'execute at {event["attacker"]} run kill @e[distance=..6,limit=1,type={event["victim"].lower()}]')

EventSession.registerEventHandler(mctypes.Event_Player_Command, onPlayerMessage)
EventSession.registerEventHandler(mctypes.Event_Player_Attack, onPlayerAttack)
EventSession.startListener()