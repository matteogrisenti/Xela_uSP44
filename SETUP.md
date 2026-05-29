# Xela uSP44 Setup Guide

This guide outlines the hardware setup, CAN bus activation, and software configuration required to get your Xela uSP44 system operational.

This guide is extracted from the official software and harduar manual of Xela. You can find them at this website [https://xela.lat-d5.com/](https://xela.lat-d5.com/).


## 1. Hardware setup
Connecting the components in the correct order ensures the module is powered and communicating properly.

- Plug the 8-pin wire extending from the Sensor Module directly into the microcontroller.  
- Connect the 4-pin connector on your CAN/DSUB9 cable to the microcontroller.  
- Plug the DSUB9 connector of that same cable into your CAN/USB Interface.  
- Connect the USB cable of the CAN/USB Interface into a USB port on your host PC.  
- Plug the second USB power cable into a PC port or a 5V USB wall adapter.  
- Both USB cables must be connected for the system to function correctly


## 2. Activating the CAN Bus
The VScom USB-CAN Plus operates as a Serial CAN device using socketcan on Linux. Most drivers are pre-installed in the Linux kernel.

#### Install Prerequisites
Ensure the can-utils package is installed on your system:

```bash
sudo apt update
sudo apt install can-utils
```

#### Activation Commands

Execute the following commands in your terminal to activate the serial CAN device:

```bash
sudo slcand -o -s8 -t hw -S 3000000 /dev/ttyUSB0 
sudo ip link set up can0 
```

*Note*: this activation commands need to be done any time we restart the computer. 

Note: Replace `/dev/ttyUSB0` with the actual device name assigned by your Ubuntu system (e.g., `/dev/ttyUSB1`). These commands must be executed every time the computer restarts.


## 3. Software Installation

#### Download and Extract
1. Go to [https://xela.lat-d5.com/](https://xela.lat-d5.com/) and download the last version of the software image 

2. Create the a dedicated storing directory:
   ```bash 
   mkdir -p ~/.local/bin 
   ```

3. Extract: Navigate to where you downloaded your file (e.g., your Downloads folder) and extract it to the folder you just created:
   ```bash 
   tar -xf your_filename.tar.xz -C ~/.local/bin  
   ```  
    *( Replace `your_filename.tar.xz` with the actual name of the file you downloaded )* 


#### Configure Permissions

The XELA software requires a specific configuration directory with read/write access for log writing.

1. Create Directory:
    ```bash 
    sudo mkdir -p /etc/xela
    ```
2. Set Permissions:
    ```Bash
    sudo chmod 777 /etc/xela
    ```

#### Server Configuration
Before you can run the software, we need to customise the server configuration file `Serv.init`. To do it we can both write it manually ( not raccomanded ) or using the xela provided tool `xela_config`. 

```bash
chmod +x ~/.local/bin/xela_*
cd ~/.local/bin
./xela_conf
```

Configure the following settings in the tool:
- `Bus Type`: *socketcan*
- `Channels:` *can0*
- `Sensor Settings` -> `Sensor` -> `ID`: the ID number found on your microcontroller.
- `Viz Setting`: Enable all options to ensure all captured features are displayed.

Select `Save and exit` to finalize the configuration.


## 4. Testing the System
To verify the installation, you will need to open two terminal windows.

Terminal 1 (Start the server):
```bash 
cd ~/.local/bin
./xela_server
```

Terminal 2 (Start the visualizer):
```bash 
cd ~/.local/bin
./xela_viz
```

