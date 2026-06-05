# Xela uSP44 Sensor Experiment

...

## Experimnet Pipeline

#### Collect Data
To collect data you need to:
1. Serial CAN Activatio
```bash
sudo killall slcand
sudo slcand -o -s8 -t hw -S 3000000 /dev/ttyUSB0 
sudo ip link set up can0 
```

2. Launche the server
```bash 
cd ~/.local/bin
./xela_server
```

3. In another terminal launch the recorder:
```bash 
cd ~/.local/bin
./xela_log -s 1:30t
```

4. The recoder are store bot as log and scv file in the ~ect/xela/CSV folder.
Copt the csv file inside this repository csv_records to use as beasilene for the different tools