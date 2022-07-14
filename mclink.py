import mcrcon, servererrors, json, threading, random, string

def getRandString(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

class Event(object):
    def __init__(self, event_type: str, data: dict):
        self.event_type = event_type
        self.data       = data

class EventSession(object):
    def __init__(self, server: mcrcon.MCRcon, serverLogFile: str):
        self.server = server

        self.shutdownWithRcon = True

        self.eventHandlers = {
            'player_join': [],
            'player_leave': [],
            'player_chat': [],
            'player_command': [],
            'player_death': [],
            'player_attack': []
        }

        self.serverLogFile = open(serverLogFile, 'r')
    
    def startListener(self): threading.Thread(target=self._listener).start()
    def _listener(self):  # sourcery skip: low-code-quality
        self.serverLogFile.readlines()#Remove all the initial lines
        while True:
            for line in self.serverLogFile.readlines():
                if line.strip() == '': pass

                if '[Async Chat Thread' in line:
                    self.handleEvent('player_chat', {'player': line.split('INFO]: <')[1].split('>')[0], 'message': line.split('> ')[1].replace('\n','')})
                elif 'left the game' in line and 'INFO]' in line:
                    self.handleEvent('player_leave', {'player': line.split('INFO]: ')[1].split(' left')[0]})
                elif 'joined the game' in line and 'INFO]' in line:
                    self.handleEvent('player_join', {'player': line.split('INFO]: ')[1].split(' joined')[0]})
                elif 'issued server command' in line and 'INFO]' in line:
                    self.handleEvent('player_command', {'player': line.split('INFO]: ')[1].split(' issued server command')[0], 'command': line.split('issued server command: ')[1].split('\n')[0]})
                elif 'was killed by' in line and "]::(death)" in line:
                    self.handleEvent('player_death', {'victim': line.split(') ')[1].split(' was')[0], 'killer': line.split('by ')[1].replace('\n','')})
                elif '[McSupportHelper]::(hit)' in line:
                    victim   = line.split('hit) ')[1].split(' was')[0]
                    attacker = line.split('by ')[1].split(' with')[0]
                    if "count=" in line: itemType = line.split('count=')[0].split('namespace="')[1].split('value="')[1].split('"},')[0]
                    else: itemType = "None"

                    if "nbt={display:{Name:'" in line: itemName = line.split("nbt={display:{Name:'")[1].split('","color')[0].split('":"')[1].replace("'}","")
                    else: itemName = "None"

                    self.handleEvent('player_attack', {'victim': victim, 'attacker': attacker, 'itemType': itemType, 'itemName': itemName})
                
                elif 'Thread RCON Client' in line and 'shutting down' in line and self.shutdownWithRcon:
                    print('RCON Client shut down, stopping event listener')
                    self.serverLogFile.close()
                    exit()

    def handleEvent(self, eventType: str, eventData: dict):
        for handler in self.eventHandlers[eventType]:
            threading.Thread(target=lambda: handler(eventData)).start()
    
    def registerEventHandler(self, event: str, handler: callable):
        if event not in self.eventHandlers:
            raise servererrors.InvalidEventError(event)
        self.eventHandlers[event].append(handler)

class ServerPlayer(object):
    def __init__(self, playerUsername: str, rconConnection: mcrcon.MCRcon):
        self.playerUsername = playerUsername
        self.server         = rconConnection
    
    def _getPlain(self, name: str) -> str:
        command = self.server.command(f'data get entity {self.playerUsername} {name}')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')

        return command.strip().split('data: ')[1].strip()
    
    def _getString(self, stringName: str) -> str:
        command = self.server.command(f'data get entity {self.playerUsername} {stringName}')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')

        return command.strip().split('data: ')[1].replace('"','')

    def _getBool(self, boolName: str) -> bool:
        command = self.server.command(f'data get entity {self.playerUsername} {boolName}')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')

        return command.strip().split('data: ')[1].strip().replace('b','') == '1'

    def _getFloat(self, floatName: str) -> float:
        command = self.server.command(f'data get entity {self.playerUsername} {floatName}')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')

        return float(command.strip().split('data: ')[1].replace('f',''))
    
    def _getAttribute(self, attributeName: str, attributeType) -> str:
        command = self.server.command(f'data get entity {self.playerUsername} {attributeName}')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')

        if attributeType == 'float':
            return float(command.strip().split('movement_speed", Base: ')[1].split("d}")[0])

    def _getAbility(self, abilityName: str, abilityType: str) -> str:
        command = self.server.command(f'data get entity {self.playerUsername} abilities')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')

        cmd = command.strip().split('data: ')[1].split(f'{abilityName}: ')[1]
        if abilityType == 'bool': return cmd.split('b,')[0] == "1"
        elif abilityType == 'float': return float(cmd.split('f,')[0])
        elif abilityType == 'int': return int(cmd.split('i,')[0])
        elif abilityType == 'string': return cmd.split('",')[0]
        elif abilityType == 'double': return float(cmd.split('d,')[0])
    
    def teleportTo(self, selector: str) -> str:
        """
        Selector can be: (Coors), (@e[limit=1] type) or (player_name)
        """
        return self.server.command(f'minecraft:teleport {self.playerUsername} {selector}')

    def setSpawnPoint(self, location: tuple) -> str: return self.server.command(f"minecraft:spawnpoint {self.playerUsername} {location[0]} {location[1]} {location[2]}") 

    def effectGive(self, effectName: str, effectLength: int, effectStrength: int, hideParticals: bool = True) -> str:
        return self.server.command(f"minecraft:effect give {self.playerUsername} {effectName} {effectLength} {effectStrength} {hideParticals.lower()}")
    def effectClear(self, effectName: str = '') -> str: return self.server.command(f"minecraft:effect clear {self.playerUsername} {effectName}")
    
    def xpAdd(self, amount: int) -> str: return self.server.command(f'minecraft:xp {self.playerUsername} add {amount} points')
    def xpGet(self) -> float: return float(self.server.command(f"minecraft:xp query {self.playerUsername} points").strip().split('has ')[1].split(' e')[0])
    def xpAddL(self, amount: int) -> str: return self.server.command(f'minecraft:xp {self.playerUsername} add {amount} levels')
    def xpGetL(self) -> float: return float(self.server.command(f"minecraft:xp query {self.playerUsername} levels").strip().split('has ')[1].split(' e')[0])

    def makeSay(self, message: str) -> str: return self.server.command('minecraft:tellraw @a {}'.format(json.dumps({"text": f"<{self.playerUsername}> {message}"})))
    def op(self) -> str: return self.server.command(f'minecraft:op {self.playerUsername}')
    def deop(self) -> str: return self.server.command(f'minecraft:deop {self.playerUsername}')
    def gamemode(self, gamemode: str) -> str: return self.server.command(f'minecraft:gamemode {gamemode.lower()} {self.playerUsername}')
    def enchant(self, enchant: str, level: int) -> str: return self.server.command(f'minecraft:enchant {self.playerUsername} {enchant} {level}')
    def removeFromInventory(self, item: str, amount: int = 1) -> str: return self.server.command(f'minecraft:clear {self.playerUsername} {item} {amount}')
    def addToInventory(self, item: str, amount: int = 1) -> str: return self.server.command(f'minecraft:give {self.playerUsername} {item} {amount}')
    def kill(self) -> str: return self.server.command(f"minecraft:kill {self.playerUsername}")
    def kick(self, reason: str = "") -> str: return self.server.command(f"minecraft:kick {self.playerUsername} {reason}")
    def ban(self, reason: str = "") -> str: return self.server.command(f"minecraft:ban {self.playerUsername} {reason}")
    def pardon(self) -> str: return self.server.command(f"minecraft:pardon {self.playerUsername}")

    def setAttributeBase(self, attribute: str, value: str) -> str: return self.server.command(f'minecraft:attribute {self.playerUsername} {attribute} base set {value}')
    def getAttributeBase(self, attribute: str) -> str: return self.server.command(f'minecraft:attribute {self.playerUsername} {attribute} base get').split('is ')[1]
    
    def getFoodLevel(self): return self._getPlain('foodLevel')
    def getHealth(self) -> float: return self._getFloat('Health')
    def getMaxHealth(self) -> float: return float(self.server.command(f'minecraft:attribute {self.playerUsername} minecraft:generic.max_health get').split('is ')[1])
    def getCurrentDimension(self) -> str: return self._getString('Dimension')
    def getIsOnGround(self): return self._getBool('OnGround')
    def getAbsorptionAmount(self): return self._getFloat('AbsorptionAmount')

    def getCanBuild(self) -> bool: return self._getAbility('mayBuild', 'bool')
    def getCanFly(self) -> bool: return self._getAbility('mayfly', 'bool')
    def getWalkSpeed(self) -> float: return self._getAbility('walkSpeed', 'float')
    def getFlySpeed(self) -> float: return self._getAbility('flySpeed', 'float')
    def getIsInvulnerable(self) -> bool: return self._getAbility('invulnerable', 'bool')
    def isFlying(self) -> bool: return self._getAbility('flying', 'bool')
    def getGamemode(self) -> str: return str(self._getPlain('playerGameType')).replace('0','survival').replace('1', 'creative').replace('2', 'adventure').replace('3', 'spectator')

    def getItemInSlot(self, slot: int) -> str:
        command = self.server.command(f'data get entity {self.playerUsername} Inventory')
        if command.strip() == 'No entity was found': raise servererrors.EntityNotFound(f'Entity {self.playerUsername} not found')
        if f"{slot}" not in f"{command}": return ''

        return command.strip().split('data: ')[1].split(f'Slot: {slot}b, id: "')[1].split('",')[0]
    
    def isBlockAtFoot(self, block_name: str) -> bool:
        tempTag = getRandString(7)
        self.server.command(f"minecraft:execute as @r at {self.playerUsername} if block ~ ~-1 ~ {block_name} run tag {self.playerUsername} add {tempTag}")
        return 'does not have' not in self.server.command(f'tag {self.playerUsername} remove {tempTag}').strip().lower()
    
    def isBlockAt(self, location: str, block_name: str) -> bool:
        tempTag = getRandString(7)
        self.server.command(f"minecraft:execute as @r at {self.playerUsername} if block {location} {block_name} run tag {self.playerUsername} add {tempTag}")
        return 'does not have' not in self.server.command(f'tag {self.playerUsername} remove {tempTag}').strip().lower()

    def isInWater(self):
        return self.isBlockAt('~ ~ ~','water')

    def getNextAirLocation(self, maxTries=400) -> str:
        yMod = next((f'~ ~{yMod} ~' for yMod in range(maxTries) if self.isBlockAt(f'~ ~{yMod} ~', 'air')), None)
        cLoc = self.getLocation()
        return None if yMod is None else [cLoc[0].strip(), float(self.getLocation()[1]) + float(yMod.replace('~','').strip()), cLoc[2].strip()]
    
    def getLocation(self) -> list:
        return self._getPlain('Pos').split('[')[1].split(']')[0].replace('d','').split(',')

class ServerSession(object):
    def __init__(self, rconHost: str, rconPassword: str, rconPort: int = 25575):
        self.rconHost     = rconHost
        self.rconPort     = rconPort
        self.rconPassword = rconPassword

        self.server = mcrcon.MCRcon(self.rconHost, self.rconPassword, self.rconPort)
        self.server.connect()
    
    def getTps(self) -> float: return float(self.server.command('tps').strip().split('15m: ')[1].split(', ')[0].replace("§a",""))
    
    def fill(self, startLocation: tuple, stopLocation: tuple, block: str, fillType: str = 'replace') -> str: return self.server.command(f'minecraft:fill {startLocation[0]} {startLocation[1]} {startLocation[2]} {stopLocation[0]} {stopLocation[1]} {stopLocation[2]} {block} {fillType}')
    def setBlock(self, location: tuple, block: str, fillType: str = 'replace') -> str: return self.server.command(f'minecraft:setblock {location[0]} {location[1]} {location[2]} {block} {fillType}')
    def setWorldBorder(self, distance: float, time: float = 0) -> str: return self.server.command(f'minecraft:worldborder set {distance} {time}')
    def setWeather(self, weather: str) -> str: return self.server.command(f'minecraft:weather {weather}')
    def setTime(self, time: str) -> str: return self.server.command(f'minecraft:time set {time}')
    def whitelistSet(self, status: str) -> str: return self.server.command(f'minecraft:whitelist {status}')
    def addToWhitelist(self, playerName: str) -> str: return self.server.command(f'minecraft:whitelist add {playerName}')
    def removeFromWhitelist(self, playerName: str) -> str: return self.server.command(f'minecraft:whitelist remove {playerName}')
    def addTitle(self, player, titleText: str, titleLocation: str) -> str: return self.server.command(f'minecraft:title {player} {titleLocation} "{titleText}"')
    def clearTitle(self, player: str) -> str: return self.server.command(f'minecraft:title {player} clear')
    def fakeSay(self, username: str, message: str) -> str: return self.server.command('minecraft:tellraw @a {}'.format(json.dumps({"text": f"<{username}> {message}"})))

    def getBanlist(self) -> str: return self.server.command('minecraft:banlist')
    def getWorldBorder(self) -> float: return float(self.server.command('minecraft:worldborder get').strip().split('ly ')[1].split(' bl')[0])
    def getWhitelisted(self) -> list: 
        cmd = self.server.command('minecraft:whitelist list')
        if 'there are no whitelisted players' in cmd.lower().strip(): return []
        else: return cmd.strip().split(': ')[1].split(', ')