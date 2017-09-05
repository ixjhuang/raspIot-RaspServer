'''IotManager.py
    Manage IotServer and IotDevice
    Including access IotDevice and setup IotServer
'''

import os
import json
import time
import shutil
import importlib
import threading
from RoomHandler import getRoomListFromFile, saveRoomListToFile, saveRoomContentToFile, getRoomContentFromFile


class IotManager:
    '''IotManager.class
        Manage IotServer and IotDevice
        Including access IotDevice and setup IotServer
    '''

    roomList = list()
    devicesUuidMapRoom = {}
    roomContentList = list()

    def __init__(self):
        self.roomList = getRoomListFromFile()
        for room in self.roomList:
            self.buildRoomContentVariable(room['name'])
        threading.Thread(self.saveRoomListAndRoomContentToFileAtRegularTime, None)


    def buildRoomContentVariable(self, roomName):
        ''' Get room content from folder and build variable '''
        roomContent = getRoomContentFromFile(roomName)
        self.roomContentList.append(roomContent)
        devicesUuid = []
        for index in range(len(roomContent['devices'])):
            roomContent['devices'][index]['status'] = False
            # using uuid to map room, make room search faster 
            self.devicesUuidMapRoom[roomContent['devices'][index]['uuid']] = roomName
        # use every different room name to build variable
        # format: _roomname_RoomContent
        setattr(self, self.buildRoomVariableName(roomName), roomContent)


    def buildRoomVariableName(self, roomName):
        '''   format: _roomname_RoomContent '''
        return '_' + roomName + '_RoomContent'


    def setupIotServer(self, conn, recvdata):
        ''' Setup IotServer in a new thread '''
        threading.Thread(target=self.IotServerSetter, args=(conn, recvdata))


    def IotServerSetter(self, conn, recvdata):
        ''' setup IotServer and add it to iotServerList '''
        ip = recvdata['ip']
        mac = recvdata['mac']
        moduleName = className = recvdata['iotServer']
        try:
            if os.path.exists('IotServer/' + moduleName + '.py') is False:
                shutil.copyfile('Repository/' + moduleName + '.py', 'IotServer/' + moduleName + '.py')
            # import module from IotServer/
            iotServerModule = importlib.import_module('IotServer.' + moduleName)
            # import class from module
            iotServerClass = getattr(iotServerModule, className)
            # instantiation
            iotServer = iotServerClass(ip, mac)
            # search which room it's belong to


            conn.sendall(json.dumps({'response':'Setup completed'}).encode())
            #exec('print(iotServerList[0].' + iotServerList[0].buildDeviceJSON()['deviceContent'][0]['getter'] + ')')
        except Exception as reason:
            print(__file__ +' Error: ' + str(reason))

    
    def saveRoomListAndRoomContentToFileAtRegularTime(self):
        ''' save room list and room content to file at regular time '''
        while True:
            # hold it for three minutes
            time.sleep(3 * 60)
            # save room list
            saveRoomListToFile(self.roomList)
            # remove device's status before save
            for roomContent in self.roomContentList:
                saveRoomContentToFile(roomContent)

def addRoomtoIotManager(roomDict):
    IotManager.roomList.append(roomDict)
    return IotManager.roomList


def getRoomListFromIotManager():
    ''' get room list from IotManager.roomList '''
    return IotManager.roomList

def deleteRoomInIotManager(roomName):
    ''' delete room in IotManager.roomList '''
    roomList = getRoomListFromIotManager()
    for index in range(len(roomList)):
        if roomList[index]['name'] == roomName:
            del roomList[index]
            break
