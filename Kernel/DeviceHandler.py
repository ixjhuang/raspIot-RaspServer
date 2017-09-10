import os
import json
import time
import shutil
import importlib
import threading
import subprocess
from Kernel.GlobalConstant import Unauthorized_devices
from Kernel.FileHandler import saveRoomContentToFile


class DeviceHandler:
    onLineIotServerListDict = dict()
    devicesUuidMapRoom = dict()
    def __init__(self, iotManager):
        self.IotManager = iotManager
        roomContentList = list(self.IotManager.roomHandler.getRoomContentListDict().values())
        for roomContent in roomContentList:
            for index in range(len(roomContent['devices'])):
                # using uuid to map room, make room search faster
                deviceUuid = roomContent['devices'][index]['uuid']
                self.devicesUuidMapRoom[deviceUuid] = roomContent['name']
        threading.Thread(target=self.checkIsIotDeviceAliving, args=()).start()


    def addDevice(self, roomName, device):
        ''' add device
                to deviceUuidMapRoom
                to roomContent['devices']
                and save roomContent to file
        '''
        deviceUuid = device['uuid']
        if self.devicesUuidMapRoom.get(deviceUuid) is not None:
            return 'Device already exists'
        self.devicesUuidMapRoom[deviceUuid] = roomName
        room = self.IotManager.roomHandler.getRoomContent(roomName)
        devices = room['devices']
        devices.append(device)
        saveRoomContentToFile(room)
        return 'Add device succeed.'


    def getDeviceJsonByUuid(self, uuid):
        if self.onLineIotServerListDict.get(uuid) is None:
            return None
        iotServer = self.onLineIotServerListDict.get(uuid)
        return iotServer.getDeviceContent()

    def setDeviceContentToValue(self, roomName, deviceName, deviceContentName, value):
        try:
            room = self.IotManager.roomHandler.getRoomContent(roomName)
            for index in range(len(room['devices'])):
                if room['devices'][index]['name'] == deviceName:
                    deviceUuid = room['devices'][index]['uuid']
                    break

            iotServer = self.onLineIotServerListDict[deviceUuid]
            device = iotServer.getDeviceAttribute()
            for index in range(len(device['deviceContent'])):
                if device['deviceContent'][index]['name'] == deviceContentName:
                    deviceContentSetter = device['deviceContent'][index]['setter']
                    break

            exec('iotServer.' + deviceContentSetter + '("' + value + '")')
        except Exception as reason:
            print(__file__ + " Error: " + str(reason))
            return "false"
        return "true"


    def checkIsIotDeviceAliving(self):
        while True:
            time.sleep(10)
            for iotServer in list(self.onLineIotServerListDict.values()):
                try:
                    deviceIp = iotServer.ip
                    deviceUuid = iotServer.uuid
                    PingCmd = 'ping -n 3 ' + deviceIp
                    pingResult = subprocess.check_output(PingCmd, shell=True).decode()
                    # device unreachable
                    if pingResult.find('from ' + deviceIp) == -1:
                        # Windows:  100% loss: Reply from itself
                        #           0%   loss: Reply from deviceIp
                        # Linux:    100% loss: No reply
                        #           0%   loss: from deviceIp
                        del iotServer       # device unreachable, shut iotServer down
                        self.onLineIotServerListDict.pop(deviceUuid)    # iotServer offline
                        roomName = self.devicesUuidMapRoom[deviceUuid]
                        roomContent = self.IotManager.roomHandler.getRoomContent(roomName)
                        for index in range(len(roomContent['devices'])):
                            if roomContent['devices'][index]['uuid'] == deviceUuid:
                                # set iotServer status to offline
                                roomContent['devices'][index]['status'] = False
                                print(roomName + ': ' + roomContent['devices'][index]['name'] + ' offline')
                                break
                        saveRoomContentToFile(roomContent)
                except Exception as reason:
                    print('Must use utf-8 to encode cmd when running on Windows.')
                    print('If not, could not check device is online or not.')
                    print('(Try: run "chcp 65001" in cmd, and restart RaspServer.)')
                    return



    def setupIotServer(self, conn, recvdata):
        ''' Setup IotServer in a new thread '''
        threading.Thread(target=self.IotServerSetter, args=(conn, recvdata)).start()


    def IotServerSetter(self, conn, recvdata):
        ''' setup IotServer and add it to iotServerList '''
        ip = recvdata['ip']
        uuid = recvdata['uuid']
        deviceName = recvdata['device']
        moduleName = className = recvdata['iotServer']

        try:
            if os.path.exists('IotServer/' + moduleName + '.py') is False:
                IotServerFile = moduleName + '.py'
                shutil.copyfile('Repository/' + IotServerFile, 'IotServer/' + IotServerFile)
            # import module from IotServer/
            iotServerModule = importlib.import_module('IotServer.' + moduleName)
            # import class from module
            iotServerClass = getattr(iotServerModule, className)
            # instantiation
            iotServer = iotServerClass(ip, uuid)
            if self.onLineIotServerListDict.get(uuid) is None:
                self.onLineIotServerListDict[uuid] = iotServer

            if self.devicesUuidMapRoom.get(uuid) is None:
                # Add to list of Unauthorized devices
                # self.devicesUuidMapRoom[uuid] = Unauthorized_devices
                conn.sendall(json.dumps({'response':'Setup completed'}).encode()) # for the moment
                return
            # search which room it's belong to
            roomName = self.devicesUuidMapRoom[uuid]

            # set status of this iotServer True
            devices = self.IotManager.roomHandler.getRoomContent(roomName)['devices']
            '''
            if roomName == Unauthorized_devices:
                deviceDict = self.buildNewDeviceDict(deviceName, uuid)
                deviceDict['status'] = True
            else:
            '''
            for index in range(len(devices)):
                if devices[index]['uuid'] == uuid:
                    devices[index]['status'] = True
                    print(roomName + ': ' + devices[index]['name'] + ' online')
                    break
            conn.sendall(json.dumps({'response':'Setup completed'}).encode())
        except Exception as reason:
            print(__file__ +' Error: ' + str(reason))


def buildNewDeviceDict(deviceName, deviceUuid):
    ''' build a device by device blueprint '''
    deviceDict = {"name": deviceName,
                  "uuid": deviceUuid,
                  "status": False}
    return deviceDict
