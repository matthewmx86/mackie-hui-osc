#!/usr/bin/env python
#!python

import argparse
import time
import os,sys,threading,string
import rtmidi
from multiprocessing import Process
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client

#Control surface output sniffer
def midi_listen():
    global msg_count; global chan_function; global bank_count; global function; global active_bank
    bank_count=8
    active_bank=0
    chan_function = {}
    function = {}
    defaults = { "name": '', "on": '',"off": '',"osc_msg": '' }
    #Channel functions
    chan_function["chan_vol"] = { "name": "chan_vol","osc_msg": "/strip/fader" }
    chan_function["pan_val"] = { "name": "pan_val","osc_msg": "/strip/pan_stereo_position" }
    chan_function["rec_ready"] = { "name": "rec_ready","on": "71", "off": "7", "osc_msg": "/strip/recenable" }
    chan_function["muted"] = { "name": "muted","on": "66", "off": "2", "osc_msg": "/strip/mute" }
    chan_function["solo"] = { "name": "solo","on": "67", "off": "3", "osc_msg": "/strip/solo" }

    function["rtz"] = { "name": "rtz","on": "64", "input1": "15","off": "0", "osc_msg": "/goto_start" }
    function["end"] = { "name": "end","on": "65", "input1": "15","off": "0", "osc_msg": "/goto_end" }
    function["stop"] = { "name": "stop","on": "67", "input1": "14","off": "0", "osc_msg": "/transport_stop" }
    function["play"] = { "name": "play","on": "68", "input1": "14","off": "0", "osc_msg": "/toggle_roll" }
    function["ffwd"] = { "name": "ffwd","on": "66", "input1": "14","off": "0", "osc_msg": "/ffwd" }
    function["rwnd"] = { "name": "rwnd","on": "65", "input1": "14","off": "0", "osc_msg": "/rewind" }
    function["rec_en"] = { "name": "rec_en","on": "69", "input1": "14","off": "0", "osc_msg": "/rec_enable_toggle" }
    function["edit"] = { "name": "edit","on": "64", "input1": "9","off": "0", "osc_msg": "/access_action/Window/show-mixer" }
    function["undo"] = { "name": "undo","on": "67", "input1": "8","off": "0", "osc_msg": "/undo" }
    function["marker"] = { "name": "undo","on": "69", "input1": "24","off": "0", "osc_msg": "/add_marker" }
    function["bankup"] = { "name": "bankup","on": "67", "input1": "10","off": "0", "osc_msg": "/bank_up" }
    function["bankdown"] = { "name": "bankdown","on": "65", "input1": "10","off": "0", "osc_msg": "/bank_down" }

    for i in range(bank_count):
        chan_function["solo"]["channel"+str(i+1)]=0
        chan_function["muted"]["channel"+str(i+1)]=0
        chan_function["rec_ready"]["channel"+str(i+1)]=0
        chan_function["pan_val"]["channel"+str(i+1)]=127

    send_msg("/set_surface/bank_size",8)
    #send_msg("/set_surface/send_page_size",8)
    msg_count = 0

    def filter(msg):
        global msg_count
        msg_count=msg_count+1
        input = str(msg).split()
        input[1] = input[1].split(",")[0]
        input[2] = input[2].split("]")[0]
        if msg_count == 1:
            global input0; global input1
            input0 = int(str(input[1]))
            input1 = int(str(input[2]))
            if 64 <= input0 <= 71:
                msg_count=0
                translate(input0,input1,-1,-1)
        elif msg_count == 2:
            global input2; global input3
            input2 = int(input[1])
            input3 = int(input[2])
            msg_count=0
            translate(input0,input1,input2,input3)
        return

    def translate(input0,input1,input2,input3):
        global chan_function; global function; global active_bank
        #print(str(input0)+"\n"+str(input1)+"\n"+str(input2)+"\n"+str(input3)+"\n\n")

        #Fader levels
        if 0 <= input0 <= 7 and 0 <= input1 <= 127 and 32 <= input2 <= 39:
            channel=(input0+1)+(bank_count*active_bank); volume=input1+input1+1
            if input3 == 64:
                print(volume)
                volume=volume+1
            volume=volume/254
            chan_function["chan_vol"]["channel"+str(channel)]=volume
            send_msg(chan_function["chan_vol"]["osc_msg"],channel,volume)

        #Pan levels
        elif 64 <= input0 <= 71 and input2 == -1 and input3 == -1:
            channel=(input0-63)+(bank_count*active_bank)
            pan_velocity=input1
            if 0 <= pan_velocity <=15:
                pan_velocity = -pan_velocity
            elif 65 <= pan_velocity <= 79:
                pan_velocity=pan_velocity-64
            chan_function["pan_val"]["channel"+str(channel)]=chan_function["pan_val"]["channel"+str(channel)]+pan_velocity
            if chan_function["pan_val"]["channel"+str(channel)] > 254:
                chan_function["pan_val"]["channel"+str(channel)]=254
            elif chan_function["pan_val"]["channel"+str(channel)] < 0:
                chan_function["pan_val"]["channel"+str(channel)]=0
            pan_level=chan_function["pan_val"]["channel"+str(channel)]/254
            send_msg(chan_function["pan_val"]["osc_msg"],channel,pan_level)

        #Center pan
        elif input0 == 15 and 0 <= input1 <= 7 and input2 == 47 and input3 == 65:
            channel=(input1+1)+(bank_count*active_bank)
            chan_function["pan_val"]["channel"+str(channel)]=127
            send_msg(chan_function["pan_val"]["osc_msg"],channel,0.5)

        #Channel functions
        elif input0 == 15 and 0 <= input1 <= 7 and input2 == 47 and 65 <= input3 <=71:
            channel=(input1+1)+(bank_count*active_bank)
            for i in chan_function:
                i = str(i)
                if i != "chan_vol" and i != "pan_val":
                    if input3 == int(chan_function[i]["on"]):
                        channel=(input1+1)+(bank_count*active_bank)
                        if chan_function[i]["channel"+str(channel)] == 0:
                            chan_function[i]["channel"+str(channel)]=1
                        else:
                            chan_function[i]["channel"+str(channel)]=0
                        send_msg(chan_function[i]["osc_msg"],channel,chan_function[i]["channel"+str(channel)])

        #General buttons
        elif input0 == 15 and input2 == 47 and 64 <= input3 <= 69:
            for i in function:
                i = str(i)
                if input3 == int(function[i]["on"]) and input1 == int(function[i]["input1"]):
                    if i == "bankdown":
                        active_bank=active_bank-1
                    elif i == "bankup":
                        active_bank=active_bank+1
                    if active_bank < 0:
                        active_bank=0
                    send_msg(str(function[i]["osc_msg"]),1)

        return

    midiIn = rtmidi.MidiIn()
    midiIn.open_port(1)
    while True:
        #reduce cpu usage, no noticable performance loss
        time.sleep(0.00001)
        msg = midiIn.get_message()
        if msg:
            filter(msg)
    midi_input()

    return

def osc_listen():
    global dispatcher; global asci_out; global active_bank
    midiout = rtmidi.MidiOut()

    def midi(*data):
        note_on=[data[0],data[1],data[2]]
        if len(data) > 3:
            note_off=[data[0],data[1],data[3]]
        else:
            note_off=[data[0],data[1],0]
        #Only open port once
        try:
            global started
            started
        except:
            started = 0
            midiout.open_port(1)

        #Dont blank LCD output notes
        if data[0] == 176 and 98 <= data[1] <= 99 :
            note_off = note_on

        midiout.send_message(note_on)
        midiout.send_message(note_off)
        return

    def asci_out(msg,otype):
        asci_map=[" "]
        extended=['[','//',']','^','_','','null','"','*','*_',"null",'null',"'","null","null","null","<","null","-","null","/","0","1","2","3","4","5","6","7","8","9"]
        extended2=["null","null","null","null","null","null","."]
        # vel + 64 adds "." under output.
        for i in string.ascii_lowercase[:26:1]:
            asci_map.append(i)
        for i in extended:
            asci_map.append(i)

        for i in extended2:
            asci_map.append(i)

        if otype == "absolute":
            if msg[1] == 0:
                midi(176,99,asci_map.index(str(msg[0])))
            elif msg[1] == 1:
                midi(176,98,asci_map.index(str(msg[0])))

        if otype == "direct":
            midi(176,99,asci_map.index(str(msg[0])))
            midi(176,98,asci_map.index(str(msg[1])))

        if otype == "number":
            msg = int(msg)
            msg = str(msg)
            if int(msg) > 99:
                midi(176,99,asci_map.index(str("9")))
                midi(176,98,asci_map.index(str("9")))
            elif int(msg) < 10:
                midi(176,99,asci_map.index(str(" ")))
                midi(176,98,asci_map.index(str(msg[0])))
            else:
                midi(176,99,asci_map.index(str(msg[0])))
                midi(176,98,asci_map.index(str(msg[1])))

        if otype == "string":
            midi(176,98,0)
            midi(176,99,0)
            msg += " "+msg+" "+msg

            z=0
            for i in msg:
                i = str(i)
                conv = asci_map.index(i)
		        #print(i+" ->"+str(i))
                if z == 0:
                    z = 1
                    last = asci_map.index(i)
                    midi(176,98,conv)
                elif z == 1:
                    z = 2
                    midi(176,98,conv+64)
                    midi(176,99,last)
                    last = asci_map.index(i)
                elif z == 2:
                    z = 1
                    midi(176,98,conv)
                    midi(176,99,last+64,1)
                    last = asci_map.index(i)
                    time.sleep(0.5)
        return

    def feedback(position,channel,first_byte):
        global note_on; global note_off
        if position > 127:
            position = 127
        elif position < 0:
            position = 0
        position=int(position)
        channel=int(channel-1)
        if channel < 0:
            channel=8
        fader_midi_first_byte=first_byte
        midi(fader_midi_first_byte,channel,position,position)
        return

    def print_signal_handler(label, label2, channel, signal):
        channel=int(channel)
        feedback(int(signal),88+channel,160)
        return

    def print_volume_handler(*var):
        msg_recv(var[0],str(var[2])+" "+str(round(var[3],2)))
        channel=str(var).split()
        position=float(str(var).split(",")[3].split(")")[0])*100
        position=int(round(position/0.78,0))
        channel=int(channel[2].split(",")[0])
        #asci_out(str(channel),"number")
        feedback(position,channel,176)
        return

    def print_bankup_handler(label,avail):
        asci_out(str(avail+1),"number")
        msg_recv("Bank up available: ",str(avail))
        return

    def print_bankdown_handler(label,avail):
        asci_out(str(avail-1),"number")
        msg_recv("Bank down available: ",str(avail))
        return

    def print_heartbeat_handler(label,pulse):
        msg_recv(label,pulse)
        return

    def print_beat_handler(label,beat):
        #global active_bank
        #print(active_bank)
        beat = str(beat).split("|")[1]
        asci_out(str(beat[0])+str(beat[1]),"direct")
        msg_recv(label,beat)
        return

    def msg_recv(msg,val):
        print("OSC msg received on "+str(args.ip)+": "+str(msg)+" "+str(val))
        return

    dispatcher = dispatcher.Dispatcher()
    #dispatcher.map("/filter", print)
    dispatcher.map("/position/bbt", print_beat_handler)
    dispatcher.map("/heartbeat", print_heartbeat_handler)
    dispatcher.map("/bankup", print_bankup_handler)
    dispatcher.map("/bankdown", print_bankdown_handler)
    dispatcher.map("/strip/signal", print_signal_handler, "value")
    dispatcher.map("/strip/fader", print_volume_handler, "Volume")
    server = osc_server.ThreadingOSCUDPServer(
        ("127.0.0.1", 5005), dispatcher)
    print("Serving on {}".format(server.server_address))
    server.serve_forever()
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--port", type=int, default=3819,
        help="The port the OSC server is listening on")
    parser.add_argument("--bank-size", type=int, default=8,
        help="The number of channel strips")
    parser.add_argument("--command", type=str, default="/transport_stop",
        help="OSC parameter type")
    parser.add_argument("--value", type=str, default="1",
        help="OSC parameter value")
    parser.add_argument("--value2", type=str, default="",
        help="OSC parameter value2")
    args = parser.parse_args()

    if args.value2 != "":
        try:
            if float(args.value2) == int(args.value2):
                args.value2 = int(args.value2)
                args.value2 = int(args.value2)
        except:
            args.value2 = float(args.value2)
        try:
            if float(args.value) == int(args.value):
                args.value = int(args.value)
                args.value = int(args.value)
        except:
            args.value = float(args.value)
        client = udp_client.SimpleUDPClient(args.ip, args.port, args.value2)
        client.send_message(args.command, [args.value, args.value2])
    else:
        if float(args.value) == int(float(args.value)):
            args.value = int(args.value)
            print(args.value)
        client = udp_client.SimpleUDPClient(args.ip, args.port)
        client.send_message(args.command, args.value)

    def send_msg(*msg):
        object = msg[0]
        channel = msg[1]
        if len(msg) > 2:
            value0 = msg[2]
            client = udp_client.SimpleUDPClient(args.ip, args.port)
            client.send_message(object,[channel, value0])
            print("OSC msg sent to "+str(args.ip)+" "+str(args.port)+": "+object+" "+str(channel)+" "+str(value0))
        elif len(msg) <= 2:
            client = udp_client.SimpleUDPClient(args.ip, args.port)
            client.send_message(object,channel)
            print("OSC msg sent to "+str(args.ip)+" "+str(args.port)+": "+object+" "+str(channel))
        return

        #if int(channel) == 1:
        #    os.system("amixer set Master "+str(value0*100)+"% | 2&>/dev/null")

    t1 = Process(target=midi_listen)
    t2 = Process(target=osc_listen)
    t1.start()
    t2.start()

    def heartbeat(*pulse):
        timer = pulse[1]
        pulse = int(pulse[0])
        if pulse == 0:
            pulse = 1
        else:
            pulse = 0
        time.sleep(1)
        timer=int(timer)+1
        send_msg("/heartbeat",float(pulse))
        heartbeat(pulse,timer)
        return

    hb = threading.Thread(target=heartbeat,args="10")
    hb.start()
