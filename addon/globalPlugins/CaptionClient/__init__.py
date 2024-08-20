import base64
import gui, wx
from gui import guiHelper
import textInfos
import scriptHandler
import json
import ui
import globalPluginHandler
import tones # We want to hear beeps.
import subprocess
import io
import threading 
import api
import wx
import urllib.request
import urllib.error

#Insure one instance of Search with dialog is active.
_searchWithDialog= None


# 构建请求的 URL（服务器的接收端点）,第一个打算弃用,它不支持提问,而且没有多语言支持, 只能输出中文, 而且有时会冒两句英文
url = 'https://caption.flowersky.love'  
# queryUrl = "http://localhost:8787"
queryUrl = "https://vision.flowersky.love"

# 构建请求头，包括内容类型和 Bearer API Key
headers = {
    "User-Agent": "curl/7.68.0",  # 这里模拟的是curl的请求头
    # 'Content-Type': 'image/png',  # 指定内容类型为 PNG 图像
    'Content-Type': 'application/json', 
    'Authorization': 'Bearer luckydog'  # 使用 Bearer 认证，将 'YOUR_API_KEY' 替换为实际的 API Key
}


def isSelectedText():
    '''this function  specifies if a certain text is selected or not
        and if it is, returns text selected.
    '''
    obj=api.getFocusObject()
    treeInterceptor=obj.treeInterceptor
    if hasattr(treeInterceptor,'TextInfo') and not treeInterceptor.passThrough:
        obj=treeInterceptor
    try:
        info=obj.makeTextInfo(textInfos.POSITION_SELECTION)
    except (RuntimeError, NotImplementedError, LookupError):
        info=None
    if not info or info.isCollapsed:
        return False
    else:
        return info.text.strip()

def saveImage():
    # 获取当前屏幕上聚焦的对象，通常是一个导航对象（可能表示当前窗口或屏幕的某一部分）
    obj = api.getNavigatorObject()
    
    # 获取对象的位置和尺寸信息，即 x 和 y 位置，以及宽度和高度
    x, y, width, height = obj.location
    
    # 如果启用了 sizeReport 选项，并且脚本没有被重复调用（通常与按键脚本相关）
    # 这里的代码被注释掉了，通常用于报告尺寸
    # if conf["sizeReport"] and scriptHandler.getLastScriptRepeatCount() != 1:
    #    ui.message(_("Size: {width} X {height} pixels").format(width=width, height=height))
    
    # 创建一个与对象尺寸相同的空白位图，准备在其上绘制图像
    bmp = wx.Bitmap(width, height)
    
    # 创建一个内存设备上下文，用于在位图上进行绘图操作
    mem = wx.MemoryDC(bmp)
    
    # 将屏幕上的指定区域（由 x, y, width, height 指定）复制到内存位图中
    mem.Blit(0, 0, width, height, wx.ScreenDC(), x, y)
    
    # 将位图转换为图像对象，这样可以进行更灵活的图像操作
    image = bmp.ConvertToImage()
    
    # 创建一个字节流对象，用于将图像数据保存为二进制数据（例如 PNG 格式）
    body = io.BytesIO()
    
    # 将图像保存到字节流中，使用 PNG 格式
    image.SaveFile(body, wx.BITMAP_TYPE_PNG)
    
    # 从字节流对象中读取图像的二进制数据，以便进一步处理或保存
    image_data = body.getvalue()
    return  image_data

def caption(image_data):
    # image_data 是要发送的图像的二进制数据（假设之前已经从 BytesIO 对象中读取）
    # image_data = b'...'  # 这里应该是你要发送的图像数据

    # 构建请求对象
    req = urllib.request.Request(url, data=image_data, headers=headers, method='POST')

    try:
        # 发送请求并获取响应
        with urllib.request.urlopen(req) as response:
            # 读取和打印服务器响应
            response_data = response.read()
            # ui.browseableMessage("hello")
            print(f"Response: {response_data.decode('utf-8')}")
            result = response_data.decode('utf-8')
            data = json.loads(result)
            description = data['description']
            ui.message(description)
            api.copyToClip(text=description, notify=False)
    except Exception as e:
        ui.message(str(e))

def image_query(image, text):
    # 将 bytes 对象转换为一个整数列表,直接传输列表到服务器,服务器使用数组处理
    # byte_list = list(image)
    
    # 使用base64编码,没太大用,脱裤子放屁,目前先这样
    image_base64 = base64.b64encode(image).decode('utf-8')

    
    image_and_prompt_json_data = json.dumps({
        "image": image_base64,
        # "image": byte_list,
        "prompt": text
    })
    json_bytes = image_and_prompt_json_data.encode('utf-8')


    req = urllib.request.Request(queryUrl, data=json_bytes, headers=headers, method='POST')

    try:
        # 发送请求并获取响应
        with urllib.request.urlopen(req) as response:
            # 读取和打印服务器响应
            response_data = response.read()
            result = response_data.decode('utf-8')
            data = json.loads(result)
            description = data['description']
            ui.message(description)
            api.copyToClip(text=description, notify=False)
    except Exception as e:
        ui.message(str(e))


class SearchWithDialog(wx.Dialog):

    def __init__(self, parent):
        # Translators: Title of dialog
        super(SearchWithDialog, self).__init__(parent, title=_("Image Query"))

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

        editTextSizer= guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        # Translators: Label of static text
        editTextSizer.addItem(wx.StaticText(self, wx.ID_ANY, label= _("question about image")))
        # Translators: Label of text control to enter query.
        self.editControl= editTextSizer.addLabeledControl(_("Enter a query about image "), wx.TextCtrl)
        sHelper.addItem(editTextSizer.sizer)

        # Translators: Label of Other models button
        self.otherEngines= sHelper.addItem(wx.Button(self, wx.ID_ANY, label= _("Other Models")))
        self.otherEngines.Bind(wx.EVT_BUTTON, self.onOtherEngines)

        sHelper.addDialogDismissButtons(wx.OK | wx.CANCEL)
        self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)

        mainSizer.Add(sHelper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
        mainSizer.Fit(self)

    def postInit(self, defaultText= None, defaultImage=None):
        self.defaultImage = defaultImage
        if defaultText:
            self.editControl.SetValue(defaultText)
            self.editControl.SelectAll()
        self.editControl.SetFocus()
        self.CentreOnScreen()
        self.Raise()
        self.Show()

    def onOtherEngines(self, event):
        text= self.editControl.GetValue()
        if not text:
            self.editControl.SetFocus()
            return
        btn = event.GetEventObject()
        pos = btn.ClientToScreen( (0,0) )
        menu= OtherEnginesMenu(self, text)
        self.PopupMenu(menu, pos)
        menu.Destroy()

    def onOk(self, event):
        text= self.editControl.GetValue()
        if not text:
            self.editControl.SetFocus()
            return
        # image_data= saveImage()
        image_data = self.defaultImage
        # caption(image_data)
        image_threading =threading.Thread(target=image_query, args=(image_data, text))
        ui.message("starting image query ")
        image_threading.start()
        # image_query(image, text)
        wx.CallLater(4000, self.Destroy)

    def onCancel(self, event):
        self.Destroy()



class GlobalPlugin(globalPluginHandler.GlobalPlugin):


    def openSearchWithDialog(self, image):
        ''' Open Search with dialog if no text is selected.'''
        global _searchWithDialog
        if not _searchWithDialog:
            # if  config.conf["searchWith"]["useAsDefaultQuery"]== 0:
            if True:
                # leave blank is selected as default.
                text= "请描述图片"
                image = image
            elif  config.conf["searchWith"]["useAsDefaultQuery"]== 1:
                # Clipboard text is selected as  default value.
                text= getClipboardText()
            elif config.conf["searchWith"]["useAsDefaultQuery"]== 2:
                #  Last spoken text is selected as default value.
                text= LastSpoken.lastSpokenText[-1]
            dialog= SearchWithDialog(gui.mainFrame)
            dialog.postInit(defaultText= text, defaultImage = image)
            _searchWithDialog= dialog
        else:
            _searchWithDialog.Raise()

    def searchWithForRequiredText(self, text, image, type= "selected"):
        if not text:
            if type== "selected":
                # 打开真实对话框，使用 editControl 输入关于图片的问题。
                self.openSearchWithDialog(image)
                return
            if type== "clipboard":
                # Translators: Message displayed if there is no text in clipboard.
                message= _("No text in clipboard")
            elif type== "lastSpoken":
                # Translators: Message displayed if there is no last spoken text.
                message= _("No last spoken text")
            ui.message(message)
            return
        scriptCount= scriptHandler.getLastScriptRepeatCount()
        if scriptCount== 0:
            ui.message("已选中")
            # Activating virtual menu.
            # self.showVirtualMenu()
            return
        #Otherwise search text with Google directly.
        # if type== "lastSpoken":
            # text= LastSpoken.lastSpokenText[0]
        # searchWithGoogle(text)
        # self.clearVirtual()

    @scriptHandler.script(
        # Translators: Message displayed in input help mode.
        description= _("Display  dialog to enter a  query about image object. ."),
        gesture= "kb:nvda+windows+'",
        # Translators: Category of addon in input gestures.
        category= _("Caption Client")
        # category= _("Image Query")
    )
    def script_searchWith(self, gesture):
        self.textRequired = isSelectedText()
        self.imageRequired = saveImage()
        self.searchWithForRequiredText(self.textRequired, self.imageRequired)



    @scriptHandler.script(
        description=_("浏览对象图像描述"),
        # Translators: Category of addon in input gestures.
        # category= _("Image Query"),
        category= _("Caption Client"),
        gesture="kb:NVDA+windows+."
    )
    def script_runCaption(self, gesture):
        image_data= saveImage()
        # caption(image_data)
        image_threading =threading.Thread(target=caption, args=(image_data,))
        ui.message("starting recognize")
        image_threading.start()


    # __gestures={
        # "kb:nvda+windows+,":"runCaption",
    # }
