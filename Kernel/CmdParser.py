'''CmdParser.py
Parser cmd that from app
'''
import copy
import json
import datetime
from Kernel.DeviceHandler import buildNewDeviceDict
from Kernel.GlobalConstant import DEFAULT_IDENTITY
from Kernel.GlobalConstant import MY_DEVICES
from UserConfig import IDENTITY

class CmdParser:
    '''CmdParser class
    parse cmd from app and return result to app
    '''
    def __init__(self, iotManager):
        self.IotManager = iotManager

    def setCommand(self, conn, target, value):
        target = target.split(':')
        roomHandler = self.IotManager.getRoomHandler()
        deviceHandler = self.IotManager.getDeviceHandler()
        if target[0] == 'room':         # room rename
            old, new = target[1], value
            roomHandler.renameRoom(old, new)
            deviceHandler.moveAllDevice(old, new)
            conn.sendall('Rename succeed.'.encode())
        elif target[0] == 'device':
            oldRoom, deviceName = target[1].split('/')
            newRoom, newDeviceName = value.split('/')
            deviceUuid = deviceHandler.getDeviceUuidByName(oldRoom, deviceName)
            if oldRoom == newRoom:      # device rename
                deviceHandler.renameDevice(deviceUuid, newDeviceName)
            else:                       # device move
                deviceHandler.moveDevice(deviceUuid, newRoom)
        elif target[0] == 'deviceContent':  # set deviceContent to new value
            roomName, deviceName, deviceContentName = target[1].split('/')
            result = deviceHandler.setValueToDeviceContent(roomName, deviceName, deviceContentName, value)
            conn.sendall(result.encode())

    def	getCommand(self, conn, target, value):
        target = target.split(':')
        if target[0] == 'server' and value == 'checkServices':  # check services
            conn.sendall("raspServer is ready.".encode())
        elif target[0] == 'room' and value == 'roomlist':       # get room list
            roomHandler = self.IotManager.getRoomHandler()
            conn.sendall(roomHandler.getRoomJsonList().encode())
        elif target[0] == 'device' and value == 'devicelist':   # get device list
            sendJson = self.buildJSON(target[1])
            conn.sendall(sendJson.encode())


    def addCommand(self, conn, target, value):
        target = target.split(':')
        if target[0] == 'room':             # add a new room
            roomName = value
            roomHandler = self.IotManager.getRoomHandler()
            conn.sendall(roomHandler.addRoom(roomName).encode())
        elif target[0] == 'device':         # add a new device
            deviceUuid = value
            roomName, deviceName = target[1].split('/')
            deviceDict = buildNewDeviceDict(deviceName, deviceUuid)
            deviceHandler = self.IotManager.getDeviceHandler()
            conn.sendall(deviceHandler.addDevice(roomName, deviceDict).encode())

    def delCommand(self, conn, target, value):
        deviceHandler = self.IotManager.getDeviceHandler()
        if target.split(':')[0] == 'room':      # delete a room from home
            roomName = value
            deviceHandler.moveAllDevice(roomName, MY_DEVICES)
            conn.sendall('Done'.encode())
            roomHandler = self.IotManager.getRoomHandler()
            roomHandler.delRoom(roomName)

        # delete a device from room and move to Unauthorized_devices
        elif target.split(':')[0] == 'device':
            roomName, deviceName = target.split(':')[1], value
            deviceUuid = deviceHandler.getDeviceUuidByName(roomName, deviceName)
            deviceHandler.delDevice(deviceUuid)

    def commandParser(self, conn, recvdata):
        if recvdata['identity'] == IDENTITY or recvdata['identity'] == DEFAULT_IDENTITY:
            # cmd, target, value = json.loads(Json)
            # 以免json的Key顺序乱了，不够保险
            cmd, target, value = recvdata['cmd'], recvdata['target'], recvdata['value']
            if cmd == "get":
                self.getCommand(conn, target, value)
            elif cmd == 'set':
                self.setCommand(conn, target, value)
            elif cmd == 'add':
                self.addCommand(conn, target, value)
            elif cmd == 'del':
                self.delCommand(conn, target, value)
            print("Finished.")
            conn.close()
        elif recvdata['identity'] == 'device':
            self.IotManager.deviceHandler.setupIotServer(conn, recvdata)


    def buildJSON(self, roomName):
        deviceList = []
        deviceHandler = self.IotManager.getDeviceHandler()
        roomContent = copy.deepcopy(self.IotManager.roomHandler.getRoomContent(roomName))
        if not roomContent:
            return json.dumps([])
        for d in roomContent['devices']:
            if d['status']:
                deviceAttribute = deviceHandler.getDeviceAttributeByUuid(d['uuid'])
                # pop key: 'getter' or 'setter'
                if deviceAttribute:
                    for deviceContent in deviceAttribute['deviceContent']:
                        if deviceContent.get('getter'):
                            deviceContent.pop('getter')
                        elif deviceContent.get('setter'):
                            deviceContent.pop('setter')
                    deviceAttribute['status'] = True
                    deviceList.append(deviceAttribute)
                    continue

            # elif not d['status']:
            d['status'] = False
            d['deviceContent'] = []
            deviceList.append(d)

        roomjson = {}
        roomjson['name'] = roomName
        roomjson['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        roomjson['devices'] = deviceList

        return json.dumps(roomjson)
