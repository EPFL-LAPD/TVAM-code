

# Usage (old lab PC)
* Start **Anaconda Powershell Prompt**
* Use the base Python environment
* Call `python .\tvam_code.py --help` to see the help
* `python .\tvam_code.py --path 'D:\patterns_png_001'`



## Zaber
### Stage
We use the Zaber X-RSW60C stage.

One of them has the modified I/O output which allows the stage to act as a master.
In this script, Zaber X-RSW60C stage is programmed to send 2 electrical triggers
(one that will turn on after the stage has done a full rotation and another that
fire once every given interval to signal to the DMD to change its image projection)


### API
Over the terminal interface of the Zaber UI, you can set and configure a couple of triggers.
https://www.zaber.com/protocol-manual?device=X-RSW60A&peripheral=N%2FA&version=7.33&protocol=ASCII#topic_command_trigger

To print the current commands for a trigger do:

```
\trigger <number> print
```

Where number indentifies a specific trigger

Each trigger has one condition and can have up to two actions. The trigger needs to be enabled:

\trigger 1 enable

To reset a stage and remove all triggers:
```
/system restore
```

To fire a trigger, you also need to set an I/O output:
```
/trigger 1 action a io set do <number1> <number2>
```

Where number1 identifies the output channel
      number2 is the electrical signal (0 or 1)

Maximum step size is 384.000

### Speed
The "native speed" is in degrees/second

### Code 

port_id = input("Please enter port_id\n")

connection = Connection.open_serial_port(port_id)
device_list = connection.detect_devices() # get list of connected zaber devices
device = device_list[0]
axis = device.get_axis(1) # get axis of device
axis.home()

#set I/O toggle interval, set in microsteps
interval = 384000/1000

#Trigger 1 - Set digital output 1 == 1 when pos > 360°
connection.generic_command("trigger 1 when 1 pos >= 1536000") #trigger when position >= 360°
connection.generic_command('trigger 1 action a io set do 1 1') #set digital output 1 to 1
connection.generic_command("trigger 1 enable") #enable trigger

#Trigger 2 - toggle digital output 2 based on distance interval
connection.generic_command("trigger 2 when 1 dist {}".format(interval))
connection.generic_command("trigger 2 action a io set do 2 t")
connection.generic_command("trigger 2 enable")

# stop the stage
axis.stop()
pos_final = axis.get_position(unit=Units.ANGLE_DEGREES)
axis.home()
    








