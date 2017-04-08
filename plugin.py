# Verisure Alarm plugin
#
# Author: Gesv and Daniko
#
"""
<plugin key="Verisure" name="Verisure Alarm Central" author="gesv" version="1.0.0" wikilink="https://github.com/gesv/Domoticz-VerisurePlugin/wiki">
    <params>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default=""/>
        <param field="Mode1" label="Polling Interval (s)" width="200px" required="true" default="300"/>
    </params>
</plugin>
"""

import Domoticz
import base64
import httplib2
import hashlib
from verisure import urls
import json
class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        return


    def onStart(self):
        global data
        data = httplib2.Http('.cache')
        Domoticz.Debugging(1)
        Domoticz.Log("onStart called")
        Domoticz.Heartbeat(int(Parameters['Mode1']))
        verisureLogin()

    def onStop(self):
        Domoticz.Log("onStop called")
        
    def onConnect(self, Status, Description):
        Domoticz.Log("onConnect called")
        Domoticz.Log(str(Status))
        Domoticz.Log(str(Description))

    def onMessage(self, Data, Status, Extra):
        Domoticz.Log("onMessage")
        
    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat called")
        verisureCreateDevices()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Status, Description):
    global _plugin
    _plugin.onConnect(Status, Description)

def onMessage(Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect():
    global _plugin
    _plugin.onDisconnect()

def onHeartbeat():
    global _plugin  
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
def _validate_response(response):
    """ Verify that response is OK """
    if response.status_code == 200:
        Domoticz.Log(str(response))
        return
    raise Exception('')

def verisureLogin():
    login = httplib2.Http('.cache')
    auth = 'Basic {}'.format(
        base64.b64encode(
            'CPE/{username}:{password}'.format(
                username=Parameters['Username'],
                password=Parameters['Password']).encode('utf-8')
        ).decode('utf-8'))
    headers={
             'Authorization': auth,
             'Accept': 'application/json,'
                       'text/javascript, */*; q=0.01',
    }
    global cookie
    for base_url in urls.BASE_URLS:
        urls.BASE_URL = base_url
        (resp, content) = login.request(urls.login(), 'POST', headers=headers)
        res = json.loads(str(content.decode('utf-8')))
        if(resp.status == 200):
            cookie = res['cookie']
            Domoticz.Log("Successfully Logged in")
            break
        else:
            Domoticz.Log('Login failed, trying next server')

    VerisureGetInstallation()


def VerisureGetInstallation():
    headers={
            'Cookie': 'vid={}'.format(cookie),
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            }
    (resp, content) = data.request(urls.get_installations(Parameters['Username']), 'GET', headers=headers)
    res = json.loads(str(content.decode('utf-8')))
    Domoticz.Log("Installation ID: " + str(res[0]['giid']))
    return res[0]['giid']
	
def verisureCreateDevices():
    headers={
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json',
            'Cookie': 'vid={}'.format(cookie)}
    (resp, content) = data.request(urls.overview(VerisureGetInstallation()), 'GET', headers=headers)
    res = json.loads(content.decode('utf-8'))
    #Domoticz.Log(str(res))
    i = 2

    #Door Window Sensors
    for dev in res['doorWindow']['doorWindowDevice']:
        if i not in Devices.keys():
            Domoticz.Log('Creating doorWindow devices')
            Domoticz.Device(Name=str(dev['area']), Unit=i, TypeName="Switch").Create()
        else:
            if(str(dev['state']) != str(Devices[i].sValue)):
                if(str(dev['state']) == "CLOSE"):
                    Devices[i].Update(nValue=0,sValue="CLOSE")
                else:
                    Devices[i].Update(nValue=1,sValue="OPEN")

        i += 1
		
	#Temperature sensors
    for dev in res['climateValues']:
        if i not in Devices.keys():
            Domoticz.Log('Creating Temperature Devices')
            Domoticz.Device(Name=str(dev['deviceArea']), Unit=i, TypeName="Temperature").Create()
        else:
            if(int(Devices[i].nValue) != int(dev['temperature'])):
                Devices[i].Update(nValue=int(dev['temperature']),sValue=str(dev['temperature']))
        i += 1
	
    #Smartplug devices	
    for dev in res['smartPlugs']:
        devlabel = int(hashlib.sha256(dev['deviceLabel'].encode('utf-8')).hexdigest(), 16) % 3 ** 3
        if devlabel not in Devices.keys():
            Domoticz.Log('Creating Smartplug Devices')
            Domoticz.Log(str(devlabel))
            Domoticz.Device(Name=str(dev['area']), Unit=devlabel, TypeName="Switch").Create()
            Domoticz.Log(str(Devices[devlabel]))
        else:
            if(str(dev['currentState']) != str(Devices[devlabel].sValue)):
                if(str(dev['currentState']) == "OFF"):
                    Devices[devlabel].Update(nValue=0,sValue="OFF")
                else:
                    Devices[devlabel].Update(nValue=1,sValue="ON")
        i += 1
		
	#Alarm devices	
    
    if i not in Devices.keys():
        Domoticz.Log('Creating Alarm device')
        Domoticz.Device(Name="Alarm", Unit=i, TypeName="Text").Create()
    else:
        if(str(Devices[i].sValue) != str(res['armState']['statusType'] + " - " + res['armState']['name'])):
            Devices[i].Update(nValue=0,sValue=str(res['armState']['statusType'] + " - " + res['armState']['name']))
    i += 1		
