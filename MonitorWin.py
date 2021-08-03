from datetime import date
from datetime import datetime
import threading
import win32con
import win32service
import cryptography
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
import os


class Monitor:

    def __init__(self):
        self.key = b'CP48-Bye9bH9rxaQYwOOmSa-F9BURizFqa2LORupfjA='     # encryption key
        self.crypt = Fernet(self.key)                                  # encryption object
        self.thread = None                                             # monitoring thread
        self.cond = threading.Condition()                              # condition object for notifying
        self.lock = threading.Lock()                                   # to limit file access
        self.run = True                                                # if monitoring thread is running

    # check the running services and update the files accordingly
    def ListServices(self):
        accessSCM = win32con.GENERIC_READ

        # Open Service Control Manager
        hscm = win32service.OpenSCManager(None, None, accessSCM)
        statuses = win32service.EnumServicesStatus(hscm)

        last_line = ''          # last line in serviceList
        new_line = ''           # the new information about the services
        corrupt = False         # corrupted file flag
        missing = False         # missing file flag
        no_change = True        # no new log information flag

        try:  # check for file existing and content
            if os.stat("serviceList").st_size != 0:
                with open("serviceList", 'rb') as ser_list:
                    last_line = self.crypt.decrypt(ser_list.readlines()[-1]).decode()
        except FileNotFoundError:
            missing = True
        except (InvalidSignature, cryptography.fernet.InvalidToken):
            corrupt = True
            print("\nread from a corrupted line please check log")

        ser_list = open("serviceList", 'ab')
        log = open("Status_Log.txt", 'a')

        # get current time
        today = date.today()
        curr_date = today.strftime("%d/%m/%y")
        now = datetime.now()
        curr_time = now.strftime("%H:%M:%S")
        log.write(curr_date + " " + curr_time + '\n')
        new_line = new_line + curr_date + "-" + curr_time + ' '

        # write to the file running services
        for (short_name, desc, status) in statuses:
            full_name = ' ' + short_name + ' '
            if status[1] == 4:  # if running
                new_line = new_line + short_name + ' '
                if full_name not in last_line:
                    log.write(short_name + ": ON\n")
                    no_change = False
            else:
                if full_name in last_line:
                    log.write(short_name + ": OFF\n")
                    no_change = False
        if missing:
            log.write("missing serviceList, new serviceList file was created\n")
        elif corrupt:
            log.write("serviceList file corrupted\n")
        elif no_change:
            log.write("No changes\n")
        log.close()
        ser_list.write(self.crypt.encrypt(new_line.encode()))
        ser_list.write(b'\n')
        ser_list.close()

    # scan the services list every given interval
    def scan(self, interval):
        self.cond.acquire()
        if interval > 24 * 3600:  # max 1 day waiting time
            interval = 24 * 3600
        while self.run:           # while we want to monitor run and scan
            self.lock.acquire()
            self.ListServices()
            self.lock.release()
            self.cond.wait(interval)
        self.cond.release()

    # start monitoring thread
    def monitor(self, interval):
        self.thread = threading.Thread(target=self.scan, args=(interval,))
        self.run = True
        self.thread.start()

    # stop monitoring thread
    def stop(self):
        self.run = False
        self.cond.acquire()
        self.cond.notify_all()
        self.cond.release()
        self.thread.join()

    # compare the content of the 2 given dates, round to the closest earlier dates
    def compare(self, date1, date2):
        try:
            date_obj1 = datetime.strptime(date1, "%d/%m/%y %H:%M:%S")
            date_obj2 = datetime.strptime(date2, "%d/%m/%y %H:%M:%S")
        except ValueError:
            print("error, bad dates!\n")
            return
        services = ['', '']    # the 2 lines checked in serviceList
        dates = ['', '']       # the corresponding dates to the lines
        try:   # check existence of serviceList
            if os.stat("serviceList").st_size != 0:
                self.lock.acquire()
                with open("serviceList", 'rb') as serList:
                    line_num = 1
                    for line in serList:   # check every line until closest dates are reached
                        try:
                            tmp_line = self.crypt.decrypt(line)
                            dcr_line = tmp_line.decode()
                            tmp = dcr_line.split(None, 1)[0]  # get written date
                            tmp_obj = datetime.strptime(tmp, "%d/%m/%y-%H:%M:%S")
                            if tmp_obj <= date_obj1:
                                services[0] = dcr_line
                                dates[0] = tmp
                            if tmp_obj <= date_obj2:
                                services[1] = dcr_line
                                dates[1] = tmp
                            elif tmp_obj > date_obj1 and tmp_obj > date_obj2:
                                break
                        # in case of corrupted lines in serviceList print location
                        except (ValueError, InvalidSignature, cryptography.fernet.InvalidToken):
                            print("line", line_num, "is corrupted at serviceList")
                        line_num += 1
                self.lock.release()
                # create services lists and pop the dates
                date1list = services[0].split(' ')
                date1list.pop(0)
                date2list = services[1].split(' ')
                date2list.pop(0)
                if len(date1list) == 0 or len(date2list) == 0:
                    print("no fitting logs for given dates")
                    return
                date1list.pop()  # pop \n char
                date2list.pop()
                space = 13
                print(dates[0] + ' '*space + dates[1])
                # compare the 2 services lists
                for serv in date1list:
                    full_serv = ' '+serv+' '
                    if not (full_serv in services[1]):
                        print(serv + ': ON' + ' '*space + serv + ': OFF')
                for serv in date2list:
                    full_serv = ' '+serv+' '
                    if not (full_serv in services[0]):
                        print(serv + ': OFF' + ' '*space + serv + ': ON')
            else:
                print("file is empty please start monitoring process")
        except FileNotFoundError:
            print("no serviceList file was found")

    # report any corruptions in the serviceList file
    def scan_file(self):
        end_time = "30/12/60 23:59:59"    # maximum date
        self.compare(end_time, end_time)
