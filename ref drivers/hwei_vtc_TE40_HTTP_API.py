import time
import urllib.error
import urllib.request
from json import loads, dumps
from extronlib.interface import SerialInterface, EthernetClientInterface
from extronlib.system import Wait, ProgramLog, GetUnverifiedContext

class DeviceClass:
    def __init__(self, ipAddress, port, deviceUsername, devicePassword, SSLVerifyMode):

        self.Unidirectional = 'False'
        self.connectionCounter = 15
        self.DefaultResponseTimeout = 0.3

        self._context = None
        if SSLVerifyMode == 'Off':
            self._context = GetUnverifiedContext()
        self.RootURL = 'https://{0}:{1}/'.format(ipAddress, port)
        self.Opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(), urllib.request.HTTPSHandler(context=self._context))

        self.Subscription = {}
        self.counter = 0
        self.connectionFlag = True
        self.initializationChk = True
        self.Debug = False
        self._NumberOfPhonebookSearch = 5
        self.IPAddress = ipAddress
        self.DefaultPort = port
        self.deviceUsername = deviceUsername
        self.devicePassword = devicePassword
        self.Models = {
            'TE40': self.hwei_T40,
            'TE50': self.hwei_T40,
            'Bar310': self.hwei_B310,
            'Box310': self.hwei_B310,
        }

        self.Commands = {
            'ConnectionStatus': {'Status': {}},
            'CallStatus': {'Status': {}},
            'CallTypeStatus': {'Status': {}},
            'ConferenceStatus': {'Status': {}},
            'ConferenceTypeStatus': {'Status': {}},
            'MicMute': {'Status': {}},
            'PhonebookNavigation': {'Status': {}},
            'PhonebookSearch': {'Status': {}},
            'PhonebookSearchResult': {'Parameters': ['Button'], 'Status': {}},
            'PhonebookSearchResultSet': {'Status': {}},
            'PhonebookUpdate': {'Status': {}},
            'PhoneHook': {'Status': {}},
            'SleepMode': {'Status': {}},
            'Presentation': {'Status': {}},
            'RemoteMicrophoneStatus': {'Status': {}},
            'SpeakerMute': {'Status': {}},
            'SpeakerVolume': {'Status': {}},
            'SecondDial': {'Status': {}},
            'CameraMute': {'Status': {}},
            'CameraControl': {'Status': {}},
            'CameraPreset': {'Parameters': ['Action'], 'Status': {}},
            'Layout': {'Status': {}},
            'Response': {'Parameters': ['Command'], 'Status': {}},
            'Error': {'Status': {}},
            'Call': {'Status': {}},
            'MainInSource': {'Status': {}},
            'Layout40': {'Status': {}},
            'InitCombination': {'Parameters': ['param'], 'Status': {}},
            'Combination': {'Status': {}},
            'SIP': {'Status': {}},
            'SIPAddress': {'Status': {}},
            'Model': {'Status': {}},
            'Version': {'Status': {}},
            'Logout': {'Status': {}},
            'CamStatus': {'Status': {}},
            'MicVersion': {'Status': {}},
            'Reboot': {'Status': {}},
        }

        self.SessionCookie = False
        self.SessionId = None
        self.acCSRFToken = ''
        self.DialString = None
        self.PhoneBookList = {}
        self.Advance = True
        self.StartingEntry = 1
        self.EndEntry = 0
        self.addList = []

        self.Opener.add_handler(urllib.request.HTTPCookieProcessor())

    @property
    def NumberOfPhonebookSearch(self):
        return self._NumberOfPhonebookSearch

    @NumberOfPhonebookSearch.setter
    def NumberOfPhonebookSearch(self, value):
        if 1 <= int(value) <= 10:
            self._NumberOfPhonebookSearch = int(value)
        else:
            self.Error(['NumberOfPhonebookSearch Parameter set to an invalid value'])

    def SessionUpdate(self, value, qualifier):
        res = self.__UpdateHelper('SessionUpdate', value, qualifier, url='action.cgi?ActionID=WEB_RequestSessionIDAPI')
        if res:
            try:
                if res["success"] == 1:
                    if self.Model == 'T40':
                        self.SessionId = res["data"]["acSessionId"]
                    self.SessionCookie = True
                    self.TokenUpdate(None, None)
                else:
                    raise ValueError
            except (KeyError, ValueError):
                self.SessionCookie = False
                self.Error(['Session Update: Invalid/unexpected response'])

    def TokenUpdate(self, value, qualifier):
        res = self.__UpdateHelper('TokenUpdate', value, qualifier,
            url='action.cgi?ActionID=WEB_RequestCertificateAPI',
            data={"user": self.deviceUsername, "password": self.devicePassword})
        
        if res:
            try:
                if res["success"] == 1:
#                    self.acCSRFToken = res["data"]["acCSRFToken"]
                    self.OnConnected()
                else:
                    raise ValueError
            except (KeyError, ValueError):
                self.acCSRFToken = None
                self.Error(['Token Update: Invalid/unexpected response'])
#                self.SessionUpdate(None, None)

    def SetCall(self, value, qualifier):

        sz_numb = value
        if sz_numb:
            url = 'action.cgi?ActionID=WEB_CallSiteAPI'
            data = {
                "bIsLdapCall":0,"bIsVideoCall":1,"ucEnableH239":0,
                "stSiteInfo":{
                    "uwID":0,"szName":sz_numb,"szPName":"","ucType":8,
                    "bIsLdap":0,"ucDevice":0,"ucOnline":0,"uwSortPos":0,
                    "stTPS":{},"stCTS":{},"stISDN":{},"stIP":{},
                    "stSIP":{
                        "ucBaudRate":3840,"szAlias":"ManualDial",
                        "szIP":"","szUri":""},
                    "stV35":{},"stE1":{},"stIPOverE1":{},"stT1":{},
                    "stPhone":{},"stPSTN":{},"ucH235Policy":0}
            }
            self.__SetHelper('Call', value, qualifier, url, data)

    def SetMainInSource(self, value, qualifier):

        ValueStateValues = {
            'Auto' : 255, 
            'HDMI':  7,
            'DVI' :  6, 
            'YPbPr': 8,
        }

        if value in ValueStateValues:
            url = 'action.cgi?ActionID=WEB_SaveCfgParamAPI'
            data = {"CfgItemInt":[{"CfgItemID":"port_ui_viport1",
                "CfgItemInfo":ValueStateValues[value]}], "CfgItemString":[],
                "acCSRFToken": self.acCSRFToken}
            self.__SetHelper('MainInSource', value, qualifier, url, data)

    def UpdateMainInSource(self, value, qualifier):

        SourceStates = {
            255: 'Auto', 
            7:   'HDMI',
            6:   'DVI', 
            8:   'YPbPr',
        }
        
        res = self.__UpdateHelper('MainInSource', value, qualifier,
            url='action.cgi?ActionID=WEB_GetCfgParamAPI',
            data={"CfgIDString":["port_ui_viport1"], "acCSRFToken": self.acCSRFToken})
        if res:
            try:
                self.WriteStatus('MainInSource', SourceStates[res["data"]["port_ui_viport1"]], qualifier)
            except KeyError:
                self.Error(['MainInSource: Invalid/unexpected response'])

    def UpdateLayout40(self, value, qualifier):

        res = self.__UpdateHelper('Layout40', value, qualifier,
            url='action.cgi?ActionID=WEB_GetCombinePicModeAPI',
            data={"acCSRFToken": self.acCSRFToken})
        if res:
            try:
                self.WriteStatus('Layout40', res["data"], qualifier)
            except KeyError:
                self.Error(['Layout40: Invalid/unexpected response'])

    def UpdateInitCombination(self, value, qualifier):

        res = self.__UpdateHelper('InitCombination', value, qualifier,
            url='action.cgi?ActionID=WEB_InitCombinationParam',
            data={"acCSRFToken": self.acCSRFToken})
        if res:
            try:
                self.WriteStatus('InitCombination', res["data"]["modeList"], {'param': 'modeList'})
            except KeyError:
                self.Error(['InitCombination: Invalid/unexpected response'])
            try:
                self.WriteStatus('InitCombination', res["data"]["curMode"], {'param': 'curMode'})
            except KeyError:
                self.Error(['InitCombination: Invalid/unexpected response'])
            try:
                self.WriteStatus('InitCombination', res["data"]["pipModeList"], {'param': 'pipModeList'})
            except KeyError:
                self.Error(['InitCombination: Invalid/unexpected response'])

    def SetCombination(self, value, qualifier):

        ValueStateValues = {
            1 : 1, 
            2 : 2,
            3 : 3, 
            4 : 4,
            5 : 5,
            6 : 6,
            7 : 7,
            8 : 8,
            9 : 9,
            10: 10,
            11: 11,
            12: 12,
            13: 13,
            14: 14,
            15: 15,
            16: 16,
            17: 17,
            18: 18,
            19: 19,
            20: 20,
        }

        if value in ValueStateValues:
            url = 'action.cgi?ActionID=WEB_ChangeCombinationMode'
            data = {"Param1":value, "Param2":0, "Param3":0, "Param4":0,
                "acCSRFToken": self.acCSRFToken}
            self.__SetHelper('Combination', value, qualifier, url, data)

    def SetMicMute(self, value, qualifier):

        ValueStateValues = {
            'On' : 'WEB_CloseMicAPI', 
            'Off': 'WEB_OpenMicAPI'
        }
        
        if value in ValueStateValues:
            MicMuteCmdString = 'action.cgi?ActionID={}'.format(ValueStateValues[value])
            data = {"acCSRFToken": self.acCSRFToken}
            self.__SetHelper('MicMute', value, qualifier, url=MicMuteCmdString, data=data)
        else:
            self.Discard('Invalid Command for SetMicMute')

    def SetReboot(self, value, qualifier):

        RebootCmdString = 'action.cgi?ActionID=WEB_RequestRebootAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        self.__SetHelper('Reboot', value, qualifier, url=RebootCmdString, data=data)

    def UpdateMicMute(self, value, qualifier):

        MicStates = {
            0: 'On', 
            1: 'Off'
        }

        SpeakerStates = {
            1: 'On', 
            0: 'Off'
        }
        
        res = self.__UpdateHelper('MicMute', value, qualifier, url='action.cgi?ActionID=WEB_InitAudioCtrlParamsAPI', data={"acCSRFToken": self.acCSRFToken})
        if res:
            try:
                value = MicStates[res["data"]["MicSwitch"]]
                self.WriteStatus('MicMute', value, qualifier)
                ProgramLog('\n\n\n\n\n MUTE {}\n\n\n\n\n'.format(value), 'info')
            except KeyError:
                self.Error(['Mic Mute: Invalid/unexpected response'])
            try:
                self.WriteStatus('SpeakerMute', SpeakerStates[res["data"]["SpeakerSwitch"]], qualifier)
            except KeyError:
                self.Error(['Speaker Mute: Invalid/unexpected response'])
            try:
                self.WriteStatus('SpeakerVolume', int(res["data"]["speakerValue"]), qualifier)
            except (KeyError, ValueError):
                self.Error(['Speaker Volume: Invalid/unexpected response'])

    def SetPhonebookNavigation(self, value, qualifier):

        if value in ['Up', 'Down', 'Page Up', 'Page Down']:
            if value == 'Up':
                self.StartingEntry -= 1
            elif value == 'Down':
                if self.Advance:
                    self.StartingEntry += 1
            elif value == 'Page Up':
                self.StartingEntry -= self._NumberOfPhonebookSearch
            elif value == 'Page Down':
                if self.Advance:
                    self.StartingEntry += self._NumberOfPhonebookSearch

            if self.StartingEntry < 1:
                self.StartingEntry = 1

            self.EndEntry = self.StartingEntry + self._NumberOfPhonebookSearch - 1

            number_of_names = len(self.addList)
            index = self.StartingEntry - 1
            button = 1
            self.Advance = True
            while index < number_of_names and index < self.EndEntry:
                self.WriteStatus('PhonebookSearchResult', self.addList[index], {'Button': button})
                button += 1
                index += 1

            if button <= self._NumberOfPhonebookSearch:
                self.Advance = False
                self.WriteStatus('PhonebookSearchResult', '*** End of list ***', {'Button': button})
                button += 1
                for idx in range(button, int(self._NumberOfPhonebookSearch) + 1):
                    self.WriteStatus('PhonebookSearchResult', '', {'Button': idx})
        else:
            self.Discard('Invalid Command for SetPhonebookNavigation')

    def SetPhonebookSearchResultSet(self, value, qualifier):

        if 1 <= value <= self._NumberOfPhonebookSearch:
            set_entry = self.ReadStatus('PhonebookSearchResult', {'Button': value})
            if set_entry not in ['', '*** Not Available ***', '*** End of list ***']:
                self.DialString = self.PhoneBookList[set_entry]
            else:
                self.Discard('Invalid Command for SetPhonebookSearchResultSet')
        else:
            self.Discard('Invalid Command for SetPhonebookSearchResultSet')

    def SetPhonebookUpdate(self, value, qualifier):

        param = ''
        if isinstance(qualifier, dict) and 'SearchString' in qualifier and qualifier['SearchString']:
            param = qualifier['SearchString']
        PhonebookUpdateCmdString = 'action.cgi?ActionID=WEB_SeachLdapAddrAPI'
        data = {"szKeyWords": param, "acCSRFToken": self.acCSRFToken}
        self.__SetHelper('PhonebookUpdate', value, qualifier, url=PhonebookUpdateCmdString, data=data)

        prev_time = time.monotonic()
        ctime = time.monotonic()
        while True:
            if ctime - prev_time > 3:
                break
            else:
                ctime = time.monotonic()

        PhonebookUpdateCmdString = 'action.cgi?ActionID=WEB_GetLdapAddrResultListAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('PhonebookUpdate', value, qualifier, url=PhonebookUpdateCmdString, data=data)
        if res:
            try:
                self.PhoneBookList = {}
                self.addList, ldap_list = [], res['data']['LdapList']
                button = 1
                for item in ldap_list:
                    self.addList.append(item['site'])
                    self.PhoneBookList[item['site']] = item['sipNum']
                    self.WriteStatus('PhonebookSearchResult', item['site'], {'Button': button})
                    button += 1
                if button <= self._NumberOfPhonebookSearch:
                    self.WriteStatus('PhonebookSearchResult', '*** End of list ***', {'Button': button})
                    button += 1
                    for idx in range(button, self._NumberOfPhonebookSearch + 1):
                        self.WriteStatus('PhonebookSearchResult', '', {'Button': idx})
            except KeyError:
                self.Error(['Phonebook Update: Invalid/unexpected response'])
        else:
            button = 1
            self.Advance = False
            self.WriteStatus('PhonebookSearchResult', '*** Not Available ***', {'Button': button})
            button = button + 1
            for idx in range(button, int(self._NumberOfPhonebookSearch) + 1):
                self.WriteStatus('PhonebookSearchResult', '', {'Button': idx})

    def SetPhoneHook(self, value, qualifier):

        ValueStateValues = {
            'Make Point to Point Call Site': 'WEB_CallNumberAPI',
            'Cancel':                        'WEB_CancelCallAPI',
            'Answer':                        'WEB_IncomingCallProcAPI',
            'Reject':                        'WEB_IncomingCallProcAPI',
            'Hangup':                        'WEB_HangupCallAPI',
        }

        if value in ValueStateValues:
            PhoneHookCmdString = 'action.cgi?ActionID={}'.format(ValueStateValues[value])
            if value in ['Hangup', 'Cancel']:
#                data = {"ucSiteHandle": 1, "acCSRFToken": self.acCSRFToken}
                data = {"acCSRFToken": self.acCSRFToken}

            elif value == 'Answer':
                data = {"ucValue": 1, "ucMediaType": 0, "ucSiteHandle": 1, "acCSRFToken": self.acCSRFToken}
            elif value == 'Reject':
                data = {"ucValue": 0, "ucMediaType": 0, "ucSiteHandle": 1, "acCSRFToken": self.acCSRFToken}
            elif self.DialString:
                data = {"szNumber": self.DialString, "acCSRFToken": self.acCSRFToken}
            else:
                self.Discard('Invalid Command for SetPhoneHook')
                return
            self.__SetHelper('PhoneHook', value, qualifier, url=PhoneHookCmdString, data=data)
        else:
            self.Discard('Invalid Command for SetPhoneHook')

    def SetSleepMode(self, value, qualifier):

        ValueStateValues = {
            'On' : 'WEB_StartTermSleepAPI', 
            'Off': 'WEB_SystemWakeUpAPI'
        }
        
        if value in ValueStateValues:
            SleepModeCmdString = 'action.cgi?ActionID={}'.format(ValueStateValues[value])
            data = {"acCSRFToken": self.acCSRFToken}
            self.__SetHelper('SleepMode', value, qualifier, url=SleepModeCmdString, data=data)
        else:
            self.Discard('Invalid Command for SetSleepMode')

    def UpdateSleepMode(self, value, qualifier):

        ValueStateValues = {
            'sleep'  : 'On', 
            'unsleep': 'Off'
        }

        SleepModeCmdString = 'action.cgi?ActionID=WEB_IsSystemSleepAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('SleepMode', value, qualifier, url=SleepModeCmdString, data=data)
        if res:
            try:
                value = ValueStateValues[res["data"]["isSystemSleep"]]
                self.WriteStatus('SleepMode', value, qualifier)
            except KeyError:
                self.Error(['Sleep Mode: Invalid/unexpected response'])

    def SetPresentation(self, value, qualifier):

        ValueStateValues = {
            'Start': 'WEB_StartSendAuxStreamAPI', 
            'Stop' : 'WEB_StopSendAuxStreamAPI'
        }
        
        if value in ValueStateValues:
            PresentationCmdString = 'action.cgi?ActionID={}'.format(ValueStateValues[value])
            data = {"acCSRFToken": self.acCSRFToken}
            self.__SetHelper('Presentation', value, qualifier, url=PresentationCmdString, data=data)
        else:
            self.Discard('Invalid Command for SetPresentation')

    def UpdatePresentation(self, value, qualifier):

        ValueStateValues = {
            'auxOpen' : 'Start', 
            'auxClose': 'Stop'
        }

        PresentationCmdString = 'action.cgi?ActionID=WEB_IsSendAuxStreamAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('Presentation', value, qualifier, url=PresentationCmdString, data=data)
        if res:
            try:
                value = ValueStateValues[res["data"]["isSendAux"]]
                self.WriteStatus('Presentation', value, qualifier)
            except KeyError:
                self.Error(['Presentation: Invalid/unexpected response'])

    def UpdateCallStatus(self, value, qualifier):

        CallStatusValues = {
            0: 'No Call',
            1: 'Calling',
            2: 'Disconnected',
        }

        CallTypeStatusValues = {
            0: 'ISDN call',
            1: 'V.35 call',
            2: 'E1 call',
            3: 'H.323 (IP) call',
            4: 'Phone call (audio only)',
            5: 'PSTN call (narrow band)',
            6: 'T1 call',
            7: '4E1 call',
            8: 'SIP (IP) call',
            9: 'SIP (phone) call',
            10: 'Automatic switch between call types',
        }

        ConferenceStatusValues = {
            0: 'Idle',
            1: 'Making a call',
            2: 'Answering a call',
            3: 'Rejecting a call',
            4: 'SiteCall',
            5: 'Scheduled call',
            6: 'Querying schedule',
            7: 'Deleting schedule',
        }

        ConferenceTypeStatusValues = {
            0: 'No call',
            1: 'Point-to-point call',
            2: 'Remote multipoint conference',
            3: 'Local multipoint conference',
            4: 'Cascaded conference',
        }

        RemoteMicrophoneStatusValues = {
            0: 'Unmuted',
            1: 'Muted',
        }

        MicMuteStatusValues = {
            0: 'On',
            1: 'Off',
        }

        CallStatusCmdString = 'action.cgi?ActionID=WEB_GetMailboxDataAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('CallStatus', value, qualifier, url=CallStatusCmdString, data=data)
        if res:
            try:
                value = CallStatusValues[res['data']['state']['callstate']]
                self.WriteStatus('CallStatus', value, qualifier)
            except (KeyError, IndexError):
                self.Error(['Call Status: Invalid/unexpected response'])
            try:
                value = CallTypeStatusValues[res['data']['state']['calltype']]
                self.WriteStatus('CallTypeStatus', value, qualifier)
            except KeyError:
                self.Error(['Call Type Status: Invalid/unexpected response'])
            try:
                value = ConferenceStatusValues[res['data']['state']['confstate']]
                self.WriteStatus('ConferenceStatus', value, qualifier)
            except KeyError:
                self.Error(['Conference Status: Invalid/unexpected response'])
            try:
                value = ConferenceTypeStatusValues[res['data']['state']['conftype']]
                self.WriteStatus('ConferenceTypeStatus', value, qualifier)
            except KeyError:
                self.Error(['Conference Type Status: Invalid/unexpected response'])
            try:
                value = RemoteMicrophoneStatusValues[res['data']['state']['RemoteMicStates']]
                self.WriteStatus('RemoteMicrophoneStatus', value, qualifier)
            except KeyError:
                self.Error(['Remote Microphone Status: Invalid/unexpected response'])
            try:
                value = MicMuteStatusValues[res['data']['state']['mic']]
                self.WriteStatus('MicMute', value, qualifier)
            except KeyError:
                self.Error(['Microphone Mute Status: Invalid/unexpected response'])

    def UpdateCallTypeStatus(self, value, qualifier):
        self.UpdateCallStatus(None, None)

    def UpdateConferenceStatus(self, value, qualifier):
        self.UpdateCallStatus(None, None)

    def UpdateConferenceTypeStatus(self, value, qualifier):
        self.UpdateCallStatus(None, None)

    def UpdateRemoteMicrophoneStatus(self, value, qualifier):
        self.UpdateCallStatus(None, None)

    def UpdateSpeakerMute(self, value, qualifier):
        self.UpdateMicMute(None, None)

    def SetSpeakerVolume(self, value, qualifier):

        ValueConstraints = {
            'Min': 0,
            'Max': 21,
        }

        if ValueConstraints['Min'] <= value <= ValueConstraints['Max']:
            SpeakerVolumeCmdString = 'action.cgi?ActionID=WEB_SetSpeakVolumeAPI'
            data = {"speaker": 1, "speakerValue": value, "acCSRFToken": self.acCSRFToken}
            self.__SetHelper('SpeakerVolume', value, qualifier, url=SpeakerVolumeCmdString, data=data)
        else:
            self.Discard('Invalid Command for SetSpeakerVolume')

    def UpdateSpeakerVolume(self, value, qualifier):
        self.UpdateMicMute(None, None)

    def SetSecondDial(self, value, qualifier):

        ValueStateValues = {
            '0': '0',
            '1': '1',
            '2': '2',
            '3': '3',
            '4': '4',
            '5': '5',
            '6': '6',
            '7': '7',
            '8': '8',
            '9': '9',
            '*': '*',
            '#': '#',
        }

        if self.Model == 'T40':
            SecondDialCmdString = 'action.cgi?ActionID=WEB_SendAuthConfPswdAPI'
            data = {"Password": '{}'.format(ValueStateValues[value])}
            method = 'POST'
        elif self.Model == 'B310':
            SecondDialCmdString = 'v1/meeting/calls/DTMF'
            data = {"tone": '{}'.format(ValueStateValues[value])}
            method = 'PUT'
        data["acCSRFToken"] = self.acCSRFToken
        self.__SetHelper('SecondDial', value, qualifier, url=SecondDialCmdString, data=data, method=method)

    def SetCameraMute(self, value, qualifier):

        if self.Model == 'T40':
            ValueStateValues = {
                'On': 'action.cgi?ActionID=WEB_StartSendBlueScreenAPI',
                'Off': 'action.cgi?ActionID=WEB_StopSendBlueScreenAPI',
            }
            url = ValueStateValues[value]
            data = dumps({"acCSRFToken": self.acCSRFToken})
            method='POST'

        elif self.Model == 'B310':
            ValueStateValues = {
                'On': {"CfgItemInt":[{"CfgItemID":"ViSourceState","CfgItemInfo":0}],"CfgItemString":[], "acCSRFToken": self.acCSRFToken},
                'Off': {"CfgItemInt":[{"CfgItemID":"ViSourceState","CfgItemInfo":1}],"CfgItemString":[], "acCSRFToken": self.acCSRFToken}
            }
            url = 'v1/om/config'
            data = ValueStateValues[value]
            method='PUT'
        self.__SetHelper('CameraMute', value, qualifier, url=url, data=data, method=method)

    def SetCameraControl(self, value, qualifier):

        if self.Model == 'T40':
            ValueStateValues = {
                'Start moving to the right': 0,
                'Start moving to the left': 1,
                'Start tilting upward': 2,
                'Start tilting downward': 3,
                'Start zooming in': 4,
                'Start zooming out': 5,
                'Start focusing in': 6,
                'Start focusing out': 7,
                'Stop moving to the right': 8,
                'Stop moving to the left': 9,
                'Stop tilting upward': 10,
                'Stop tilting downward': 11,
                'Stop zooming in': 12,
                'Stop zooming out': 13,
                'Stop focusing in': 14,
                'Stop focusing out': 15,
                'Move to the home position': 16,
                'Autofocus': 17,
            }
            url = 'action.cgi?ActionID=WEB_CtrlCameraOpeateAPI'
            method = 'POST'
            if value in ValueStateValues:
                data = {"camState": 'localCam', "camAction": ValueStateValues[value],
                    "camPos": 255, "camSrc": 0, "acCSRFToken": self.acCSRFToken}
            else:
                self.Discard('Invalid Command for SetCameraControl')
                return

        elif self.Model == 'B310':
            ValueStateValues = {
                'Start moving to the right': 6,
                'Start moving to the left': 5,
                'Start tilting upward': 3,
                'Start tilting downward': 4,
                'Start zooming in': 7,
                'Start zooming out': 8,
                'Start focusing in': 9,
                'Start focusing out': 10,
                'Stop moving to the right': 13,
                'Stop moving to the left': 13,
                'Stop tilting upward': 12,
                'Stop tilting downward': 12,
                'Stop zooming in': 14,
                'Stop zooming out': 14,
                'Stop focusing in': 15,
                'Stop focusing out': 15,
                'Move to the home position': 0,
                'Autofocus': 11,
            }
            url = 'v1/mediacontrol/camera/control'
            method = 'PUT'
            if value in ValueStateValues:
                data = {"cameraId": 6, "cameraAction": ValueStateValues[value],
                    "acCSRFToken": self.acCSRFToken}
            else:
                self.Discard('Invalid Command for SetCameraControl')
                return

        self.__SetHelper('CameraControl', value, qualifier, url=url, data=data, method=method)

    def SetCameraPreset(self, value, qualifier):

        ValueConstraints = {
            'Min': 1,
            'Max': 30,
        }

        if self.Model == 'T40':
    
            ActionStates = {
                'Save': 18,
                'Recall': 19,
                'Clear': 20,
            }
            url = 'action.cgi?ActionID=WEB_CtrlCameraOpeateAPI'
            action = qualifier['Action']
            if ValueConstraints['Min'] <= int(value) <= ValueConstraints['Max'] and action in ActionStates:
                data = {"camState": 'localCam', "camAction": ActionStates[action],
                    "camPos": int(value), "camSrc": 0, "acCSRFToken": self.acCSRFToken}
                method = 'POST'
            else:
                self.Discard('Invalid Command for SetCameraPreset')
                return

        elif self.Model == 'B310':

            ActionStates = {
                'Save': 'POST',
                'Recall': 'PUT',
                'Clear': 'DELETE',
            }
            action = qualifier['Action']
            if ValueConstraints['Min'] <= int(value) <= ValueConstraints['Max'] and action in ActionStates:
                if action == 'Clear':
                    url = 'v1/mediacontrol/camera/position?cameraId=6&cameraPos={}'.format(value)
                    data = ''
                else:
                    url = 'v1/mediacontrol/camera/position'
                    data = {"cameraId": 6, "cameraPos": int(value), "acCSRFToken": self.acCSRFToken}
                method = ActionStates[action]
            else:
                self.Discard('Invalid Command for SetCameraPreset')
                return

        self.__SetHelper('CameraPreset', value, qualifier, url=url, data=data, method=method)

    def SetLayout(self, value, qualifier):

        ValueStateValues = {
            'Full Screen': 256,
            'Full Screen and Upper Left Corner': 512,
            'Full Screen and Upper Right Corner': 513,
            'Full Screen and Lower Left Corner': 514,
            'Full Screen and Lower Right Corner': 515,
            'Pane with Big Upper part and Small Lower part': 769,
            'Pane with Equal Left side and Equal Right side': 771,
            'Pane with Big Left side and Small Right side': 770,
            'Pane with Upper half part, Lower Left corner and Lower Right corner': 1026,
            'Pane with Left half part, Upper right corner and Lower Right corner': 1024,
        }
        
        ImageStates = {
            'Local Video':         256,
            'Remote Video':        257,
            'Local Presentation':  771,
            'Remote Presentation': 259,
        }
        
        url = 'v1/mediacontrol/layout'
#        layoutMode = ValueStateValues[value]
        layoutMode = value
#        layoutViewList = [ImageStates[i] for i in qualifier['Images']]
        layoutViewList = qualifier['Images']
        data = {"layoutMode":layoutMode,"layoutViewList":layoutViewList, "acCSRFToken": self.acCSRFToken}
        self.__SetHelper('CameraPreset', value, qualifier, url=url, data=data, method='PUT')

    def UpdateLayout(self, value, qualifier):

        ValueStateValues = {
            256: 'Full Screen',
            512: 'Full Screen and Upper Left Corner',
            513: 'Full Screen and Upper Right Corner',
            514: 'Full Screen and Lower Left Corner',
            515: 'Full Screen and Lower Right Corner',
            769: 'Pane with Big Upper part and Small Lower part',
            771: 'Pane with Equal Left side and Equal Right side',
            770: 'Pane with Big Left side and Small Right side',
            1026: 'Pane with Upper half part, Lower Left corner and Lower Right corner',
            1024: 'Pane with Left half part, Upper right corner and Lower Right corner',
        }
        
        ImageStates = {
            256: 'Local Video',
            257: 'Remote Video',
            771: 'Local Presentation',
            259: 'Remote Presentation',
        }
        
        url = 'v1/mediacontrol/layout'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('Layout', value, qualifier, url=url, data=data, method='GET')
        if res:
            try:
                value = res['data']
                self.WriteStatus('Layout', value, qualifier)
            except (KeyError, IndexError):
                self.Error(['Layout: Invalid/unexpected response'])

    def SetLogout(self, value, qualifier):

        LogoutCmdString = 'action.cgi?ActionID=WEB_LogoutAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        self.__SetHelper('Logout', value, qualifier, url=LogoutCmdString, data=data)
        
    def UpdateSIP(self, value, qualifier):

        ValueStateValues = {
            'SIP_STATE_OK'  : 'On', 
            'EMPTY': 'Off'
        }

        SIPCmdString = 'action.cgi?ActionID=WEB_GetLineStateInfoAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('SIP', value, qualifier, url=SIPCmdString, data=data)
        if res:
            try:
                value = ValueStateValues[res["data"]["sipStatusTxStr"]]
                ProgramLog('SIP Status value is: {}'.format(value), 'info')
                self.WriteStatus('SIP', value, qualifier)
            except KeyError:
                self.Error(['SIP Mode: Invalid/unexpected response'])

    def UpdateModel(self, value, qualifier):

        ModelCmdString = 'action.cgi?ActionID=WEB_GetVersionInfoAPI'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('Model', value, qualifier, url=ModelCmdString, data=data)
        if res:
            try:
                value = res["data"]["model"]
                ProgramLog('Model Status value is: {}'.format(value), 'info')
                self.WriteStatus('Model', value, qualifier)
            except KeyError:
                self.Error(['Model Mode: Invalid/unexpected response'])
            try:
                value = res["data"]["softVersion"]
                ProgramLog('Version Status value is: {}'.format(value), 'info')
                self.WriteStatus('Version', value, qualifier)
            except KeyError:
                self.Error(['Version Mode: Invalid/unexpected response'])
            try:
                value = res["data"]["micVersion"]
                ProgramLog('Mic Version Status value is: {}'.format(value), 'info')
                self.WriteStatus('MicVersion', value, qualifier)
            except KeyError:
                self.Error(['Mic Version Mode: Invalid/unexpected response'])

    def SetSIPAddress(self, value, qualifier):

        ValueStateValues = {
            'SIPServer' : "sipserv_addr", 
            'ProxyServer': "proxy_addr",
        }
        
        url = 'action.cgi?ActionID=WEB_SaveCfgParamAPI'
        data = {"CfgItemInt":[], "CfgItemString":[{"CfgItemID":ValueStateValues[value],
                "CfgItemInfo":"vcs-core-a.sber.ru"}],
                "acCSRFToken": self.acCSRFToken}
        self.__SetHelper('SIPAddress', value, qualifier, url, data)

    def UpdateSIPAddress(self, value, qualifier):

        res = self.__UpdateHelper('SIPAddress', value, qualifier,
            url='action.cgi?ActionID=WEB_GetCfgParamAPI',
            data={"CfgIDString":["sipserv_addr"], "acCSRFToken": self.acCSRFToken})
        if res:
            try:
                value = res["data"]["sipserv_addr"]
                self.WriteStatus('SIPAddress', value, qualifier)
                ProgramLog('SIPAddress value is: {}, qual is: {}'.format(value, qualifier), 'info')
            except KeyError:
                self.Error(['SIPAddress: Invalid/unexpected response'])

    def UpdateCamStatus(self, value, qualifier):

        ValueStateValues1 = {
            0: 'Off', 
            1: 'On'
        }
        ValueStateValues2 = {
            0: 'Off', 
            1: 'On'
        }
        
        CamStatusCmdString = 'action.cgi?ActionID=WEB_GetLocalCameraList'
        data = {"acCSRFToken": self.acCSRFToken}
        res = self.__UpdateHelper('CamStatus', value, qualifier, url=CamStatusCmdString, data=data)
        if res:
            try:
                value1 = ValueStateValues1[res["data"]["itemList"][0]["itemState"]]
                value2 = ValueStateValues2[res["data"]["itemList"][1]["itemState"]]
                value = value1 + value2
                self.WriteStatus('CamStatus', value, qualifier)
            except KeyError:
                self.Error(['Cam Status: Invalid/unexpected response'])

    def __CheckResponseForErrors(self, sourceCmdName, response):

        try:
            headers = response.headers
            body = response.read().decode()
            self.NewStatus('Response', {'Headers': headers, 'Body': body}, {'Command': sourceCmdName})
            return loads(body.replace('\\', '').replace('}"', '}').replace('"{', '{'))
        except Exception:
            self.Error(['{}: Invalid/unexpected response'.format(sourceCmdName)])
            return ''

    def __SetHelper(self, command, value, qualifier, url='', data=None, method='POST'):
        
        if not self.SessionCookie:
            self.SessionUpdate(None, None)

        if self.Model == 'B310' and not self.acCSRFToken:
            self.Discard('Not Authenticated')
        else:
            self.Debug = True
            url = '{}{}'.format(self.RootURL, url) #self.RootURL = 'http://<IP Address>:<Port>/'
            if data is not None:
                data = dumps(data).encode()
            headers = {'Content-Type': 'application/json'}
            if self.Model == 'T40':
                headers['Sessionid'] = self.SessionId
            my_request = urllib.request.Request(url, data=data, headers=headers, method=method)

            try:
                res = self.Opener.open(my_request, timeout=1) # open() returns a http.client.HTTPResponse object if successful
            except urllib.error.HTTPError as err: # includes HTTP status codes 101, 300-505
                self.Error(['{0} {1} - {2}'.format(command, err.code, err.reason)])
                res = ''
            except urllib.error.URLError as err: # received if can't reach the server (times out)
                self.Error(['{0} {1}'.format(command, err.reason)])
                res = ''
            except Exception as err: # includes HTTP status code 100 and any invalid status code
                self.Error(['{0} {1}'.format(command, err)])
                res = ''
            else:
                if res.status not in (200, 202):
                    self.Error(['{0} {1} - {2}'.format(command, res.status, res.msg)])
                    res = ''
                else:
                    res = self.__CheckResponseForErrors(command, res)
            return res

    def __UpdateHelper(self, command, value, qualifier, url='', data=None, method='POST'):

        if command not in ['SessionUpdate', 'TokenUpdate']:
            if not self.SessionCookie:
                self.SessionUpdate(None, None)

        if self.Model == 'B310' and not self.acCSRFToken:
            self.Discard('Not Authenticated')
        else:
            url = '{}{}'.format(self.RootURL, url)
            if data is not None:
                data = dumps(data).encode()
            headers = {'Content-Type': 'application/json'}
            if self.Model == 'T40' and command != 'SessionUpdate':
                headers['Sessionid'] = self.SessionId
            my_request = urllib.request.Request(url, data, headers=headers, method=method)

#            if self.initializationChk:
#                self.OnConnected()
#                self.initializationChk = False

            self.counter = self.counter + 1
            if self.counter > self.connectionCounter and self.connectionFlag:
                self.OnDisconnected()

            try:
                res = self.Opener.open(my_request, timeout=1) # open() returns a http.client.HTTPResponse object if successful
            except urllib.error.HTTPError as err: # includes HTTP status codes 101, 300-505
                self.Error(['{0} {1} - {2}'.format(command, err.code, err.reason)])
                res = ''
            except urllib.error.URLError as err: # received if can't reach the server (times out)
                self.Error(['{0} {1}'.format(command, err.reason)])
                res = ''
            except Exception as err: # includes HTTP status code 100 and any invalid status code
                self.Error(['{0} {1}'.format(command, err)])
                res = ''
            else:
                if res.status not in (200, 202):
                    self.Error(['{0} {1} - {2}'.format(command, res.status, res.msg)])
                    res = ''
                else:
                    res = self.__CheckResponseForErrors(command, res)
            return res

    def OnConnected(self):
        self.connectionFlag = True
        self.WriteStatus('ConnectionStatus', 'Connected')
        self.counter = 0

    def OnDisconnected(self):
        self.WriteStatus('ConnectionStatus', 'Disconnected')
        self.connectionFlag = False
        self.SessionCookie = False
        self.acCSRFToken = None
        self.PhoneBookList = {}
        self.Advance = True
        self.StartingEntry = 1
        self.EndEntry = 0
        self.addList = []

    def hwei_T40(self):
        self.Model = 'T40'

    def hwei_B310(self):
        self.Model = 'B310'

######################################################    
    # RECOMMENDED not to modify the code below this point
    ######################################################

    # Send Control Commands
    def Set(self, command, value, qualifier=None):
        method = getattr(self, 'Set%s' % command, None)
        if method is not None and callable(method):
            method(value, qualifier)
        else:
            raise AttributeError(command + 'does not support Set.')

    # Send Update Commands
    def Update(self, command, qualifier=None):
        method = getattr(self, 'Update%s' % command, None)
        if method is not None and callable(method):
            method(None, qualifier)
        else:
            raise AttributeError(command + 'does not support Update.')

    # This method is to tie an specific command with a parameter to a call back method
    # when its value is updated. It sets how often the command will be query, if the command
    # have the update method.
    # If the command doesn't have the update feature then that command is only used for feedback 
    def SubscribeStatus(self, command, qualifier, callback):
        Command = self.Commands.get(command, None)
        if Command:
            if command not in self.Subscription:
                self.Subscription[command] = {'method':{}}
        
            Subscribe = self.Subscription[command]
            Method = Subscribe['method']
        
            if qualifier:
                for Parameter in Command['Parameters']:
                    try:
                        Method = Method[qualifier[Parameter]]
                    except:
                        if Parameter in qualifier:
                            Method[qualifier[Parameter]] = {}
                            Method = Method[qualifier[Parameter]]
                        else:
                            return
        
            Method['callback'] = callback
            Method['qualifier'] = qualifier    
        else:
            raise KeyError('Invalid command for SubscribeStatus ' + command)

    # This method is to check the command with new status have a callback method then trigger the callback
    def NewStatus(self, command, value, qualifier):
        if command in self.Subscription :
            Subscribe = self.Subscription[command]
            Method = Subscribe['method']
            Command = self.Commands[command]
            if qualifier:
                for Parameter in Command['Parameters']:
                    try:
                        Method = Method[qualifier[Parameter]]
                    except:
                        break
            if 'callback' in Method and Method['callback']:
                Method['callback'](command, value, qualifier)  

    # Save new status to the command
    def WriteStatus(self, command, value, qualifier=None):
        self.counter = 0
        if not self.connectionFlag:
            self.OnConnected()
        Command = self.Commands[command]
        Status = Command['Status']
        if qualifier:
            for Parameter in Command['Parameters']:
                try:
                    Status = Status[qualifier[Parameter]]
                except KeyError:
                    if Parameter in qualifier:
                        Status[qualifier[Parameter]] = {}
                        Status = Status[qualifier[Parameter]]
                    else:
                        return  
        try:
            if Status['Live'] != value:
                Status['Live'] = value
                self.NewStatus(command, value, qualifier)
        except:
            Status['Live'] = value
            self.NewStatus(command, value, qualifier)

    # Read the value from a command.
    def ReadStatus(self, command, qualifier=None):
        Command = self.Commands.get(command, None)
        if Command:
            Status = Command['Status']
            if qualifier:
                for Parameter in Command['Parameters']:
                    try:
                        Status = Status[qualifier[Parameter]]
                    except KeyError:
                        return None
            try:
                return Status['Live']
            except:
                return None
        else:
            raise KeyError('Invalid command for ReadStatus: ' + command)

    def MissingCredentialsLog(self, credential_type):
        if isinstance(self, EthernetClientInterface):
            port_info = 'IP Address: {0}:{1}'.format(self.IPAddress, self.IPPort)
        elif isinstance(self, SerialInterface):
            port_info = 'Host Alias: {0}\r\nPort: {1}'.format(self.Host.DeviceAlias, self.Port)
        else:
            return 
        ProgramLog("{0} module received a request from the device for a {1}, "
                   "but device{1} was not provided.\n Please provide a device{1} "
                   "and attempt again.\n Ex: dvInterface.device{1} = '{1}'\n Please "
                   "review the communication sheet.\n {2}"
                   .format(__name__, credential_type, port_info), 'warning') 

class HTTPClass(DeviceClass):
    def __init__(self, ipAddress, port, deviceUsername='api', devicePassword='Change_Me', Model=None, SSLVerifyMode='On'):
        self.ConnectionType = 'HTTP'
        DeviceClass.__init__(self, ipAddress, port, deviceUsername, devicePassword, SSLVerifyMode)
        # Check if Model belongs to a subclass      
        if len(self.Models) > 0:
            if Model not in self.Models:
                ProgramLog('{}: Model mismatch'.format(__name__), 'warning')             
            else:
                self.Models[Model]()

    def Error(self, message):
        errText = 'Module: {0}\r\nIP Address/Host: {1}\r\nError Message: {2}'.format(__name__, self.RootURL, message[0])
        self.NewStatus('Error', errText, None)
        print(errText)

    def Discard(self, message):
        self.Error([message])
