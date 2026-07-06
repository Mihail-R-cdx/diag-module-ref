from extronlib.system import Wait, Timer, ProgramLog
import globals as gl
import hwei_vtc_TE20_v1_2_1_2b as TE20
import re
from moduleDiag import BtnCodecSetSIP, BtnStatusSIP, LblStatusMic, ImgSIP, ImgCall, ImgContent, ImgMic, ImgVolume
gl.portCodec = TE20.HTTPClass(gl.IPCodec, 443, 'api', gl.PassCodec, Model='TE20', SSLVerifyMode = 'Off')

QUERY_DELAY = 0.3
QUERY_LIST = [('Presentation', None), ('CameraMute', None),
              ('RemotePresentation', None), ('AudioParams', None)]
queryIndex = 0

def Query():
    global queryIndex
    command, qualifier = QUERY_LIST[queryIndex]
    try:
        gl.portCodec.Update(command, qualifier)
    except Exception as e:
        pass
    queryIndex += 1
    if queryIndex >= len(QUERY_LIST):
        queryIndex = 0
    @Wait(15)
    def wait_poll():
        if gl.portCodec.ReadStatus('ConnectionStatus') == 'Connected':
            pollingWait.Restart()

pollingWait = Wait(QUERY_DELAY, Query)
pollingWait.Cancel()

def ConnectionStatus(command, value, qualifier):
    if value == 'Connected':
        pollingWait.Restart()
        #gl.portCodec.Update('AudioParams', None)
        #gl.portCodec.Update('ConferenceTypeStatus', None)
        #gl.portCodec.Update('SIP', None)
        #gl.portCodec.Update('Presentation', None)
        #gl.portCodec.Update('Model', None)
        gl.ConnectionStatusCodec = 1
    else:
        gl.ConnectionStatusCodec = 0
        pollingWait.Cancel()
    ProgramLog('VCS Connection Status is {}'.format(gl.ConnectionStatusCodec), 'info')

def MicMuteStatus(command, value, qualifier):
    if value == 'On':
        gl.MicMuteStatusCodec = 'Выключен'
        ImgMic.SetState(0)
    else:
        gl.MicMuteStatusCodec = 'Включен'
        ImgMic.SetState(1)
    LblStatusMic.SetText(gl.MicMuteStatusCodec)

def CameraMuteStatus(command, value, qualifier):
    pass

def PresentationStatus(command, value, qualifier):
    if value == 'Stopped':
        gl.PresentationStatusCodec = 'Не демонстрируется'
        ImgContent.SetState(0)
    else:
        gl.PresentationStatusCodec = 'Демонстрируется'
        ImgContent.SetState(1)

def RemotePresentationStatus(command, value, qualifier):
    pass

def ConferenceTypeStatus(command, value, qualifier):
    if value == 'No call':
        gl.CallStatusCodec = 'Не в звонке'
        ImgCall.SetState(0)
    else:
        gl.CallStatusCodec = 'В звонке'
        ImgCall.SetState(1)

def CallStatus(command, value, qualifier):
    pass

def CurrentConferenceParameters(command, value, qualifier):
    pass

def PowerStatus(command, value, qualifier):
    pass

def SpeakerVolumeStatus(command, value, qualifier):
    if value == 0:
        ImgVolume.SetState(0)
    else:
        ImgVolume.SetState(1)
    gl.VolumeCodec = value

def SIPStatus(command, value, qualifier):
    if value == 'Off':
        gl.SIPStatusCodec = 'Не зарегистрирован'
        BtnCodecSetSIP.SetVisible(True)
        BtnStatusSIP.SetState(1)
        ImgSIP.SetState(0)
    else:
        gl.SIPStatusCodec = 'Зарегистрирован'
        BtnCodecSetSIP.SetVisible(False)
        BtnStatusSIP.SetState(2)
        ImgSIP.SetState(1)
    #BtnStatusSIP.SetText(gl.SIPStatusCodec + '\n' + gl.SIPAddress)

def ModelStatus(command, value, qualifier):
    gl.ModelCodec = value

def VersionStatus(command, value, qualifier):
    value = value.replace("TE20 ","")
    value = re.sub(r'\R\e\l.*', '', value)
    gl.VersionCodec = value

def SIPAddressStatus(command, value, qualifier):
    gl.SIPAddress = value
    ProgramLog('\n\n\n\nSIPAddr is: {}\n\n\n\n'.format(gl.SIPAddress), 'info')
    
def CameraStatus(command, value, qualifier):
    if value == 'OffOff':
        gl.StatusCam = 'Не подключена'
    else:
        gl.StatusCam = 'Подключена'

def MicVersionStatus(command, value, qualifier):
    if value == []:
        gl.StatusMic = 'Не подключен'
        gl.ModelMic = 'Неизвестно'
    else:
        value = value[0]["micVersion"]
        value = re.sub(r'\R\e\l.*', '', value)
        gl.StatusMic = 'Подключен'
        gl.ModelMic = value

def ResponseStatus(command, value, qualifier):
    ProgramLog('{} {} {}'.format(command, value, qualifier), 'info')

def ErrorStatus(command, value, qualifier):
    pass

gl.portCodec.SubscribeStatus('ConnectionStatus', None, ConnectionStatus)
gl.portCodec.SubscribeStatus('Power', None, PowerStatus)
gl.portCodec.SubscribeStatus('MicMute', None, MicMuteStatus)
gl.portCodec.SubscribeStatus('Presentation', None, PresentationStatus)
gl.portCodec.SubscribeStatus('RemotePresentation', None, RemotePresentationStatus)
gl.portCodec.SubscribeStatus('ConferenceTypeStatus', None, ConferenceTypeStatus)
gl.portCodec.SubscribeStatus('CallStatus', None, CallStatus)
gl.portCodec.SubscribeStatus('CurrentConferenceParameters', None, CurrentConferenceParameters)
gl.portCodec.SubscribeStatus('CameraMute', None, CameraMuteStatus)
gl.portCodec.SubscribeStatus('SpeakerVolume', None, SpeakerVolumeStatus)
gl.portCodec.SubscribeStatus('AudioParams', None, SpeakerVolumeStatus)
gl.portCodec.SubscribeStatus('Response', None, ResponseStatus)
gl.portCodec.SubscribeStatus('Error', None, ErrorStatus)
gl.portCodec.SubscribeStatus('SIP', None, SIPStatus)
gl.portCodec.SubscribeStatus('Model', None, ModelStatus)
gl.portCodec.SubscribeStatus('Version', None, VersionStatus)
gl.portCodec.SubscribeStatus('CamStatus', None, CameraStatus)
gl.portCodec.SubscribeStatus('SIPAddress', None, SIPAddressStatus)
gl.portCodec.SubscribeStatus('MicVersion', None, MicVersionStatus)

def Initialize():
    gl.portCodec.Update('RequiredPolling', None)

Initialize()
