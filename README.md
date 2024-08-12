# Usage (old lab PC)
* Start **Anaconda Powershell Prompt**
* Use the base Python environment
* Call `python .\tvam_code.py --help` to see the help
* `python .\tvam_code.py --path 'D:\patterns_png_001'`

# Hardware
The stage gives two output triggers. One trigger is activated after one round, the second toggles in the speed of how many images we need per rotation.
The Arduino takes both inputs and does a digital read (microseconds delay, so quite fast). And the Arduino does the logical AND of both inputs and provides another output.
This is fed to the input of the DMD.
So the Arduino code is [here](arduino_io_board_code/arduino_io_board_code.ino). The python code to run the stage and prepare the DMD is [tvam_code.py](tvam_code.py).
The lasers are not triggered, they are just always on. But since the DMD is off by default, no light goes through the printing arm.


## Zaber
### Stage
We use the Zaber X-RSW60C stage.

One of them has the modified I/O output which allows the stage to act as a master.
In this script, Zaber X-RSW60C stage is programmed to send 2 electrical triggers
(one that will turn on after the stage has done a full rotation and another that
fire once every given interval to signal to the DMD to change its image projection)

### Appendix Zaber stage
The output of `.generic_command()` is returned in the array:

```
[device_address, axis_number, reply_flag, status, warning_flag, data, message_type]
```








