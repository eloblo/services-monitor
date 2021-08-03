from sys import platform


def main():
    started = False
    options = "start   : starts the monitoring process with given time. can only start once.\n" \
              "          the format of the time is <time> <type>.\n" \
              "          <time> is the amount in seconds.\n" \
              "stop    : stops the monitoring of the services\n" \
              "compare : compares each service log and prints the difference.\n" \
              "          the format of the dates is DD/MM/YY and time HH:MM:SS.\n" \
              "file    : scan the serviceList file and print any corruptions found\n" \
              "help    : print the options.\n"
    print(options)
    mon = Monitor()
    while True:
        answer = input('>')
        if answer == "start" and not started:
            answer = input("please enter the amount: ")
            if answer != '':
                try:
                    interval = float(answer.split(None, 1)[0])
                    if interval > 0:
                        mon.monitor(interval)
                        started = True
                    else:
                        print("invalid amount, returning to main menu")
                except ValueError:
                    print("invalid amount, returning to main menu")
            else:
                print("invalid amount, returning to main menu")
        elif answer == "help":
            print(options)
        elif answer == "stop" and started:
            mon.stop()
            started = False
            print("monitoring stopped")
        elif answer == "compare":
            date1 = input("enter the first date: ")
            date2 = input("enter the second date: ")
            mon.compare(date1, date2)
        elif answer == "quit":
            if started:
                mon.stop()
            return
        elif answer == "file":
            mon.scan_file()
        else:
            if answer == "start":
                print("already started")
            elif answer == "stop":
                print("not running")
            else:
                print("invalid input, please try again")


if platform == 'win32':
    from MonitorWin import Monitor
    main()

elif platform == 'linux':
    from MonitorUnx import Monitor
    main()

else:
    print("incompatible os")
