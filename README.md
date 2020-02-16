# mackie-hui-osc
A python script to make the Macke Baby HUI interface work with the OSC protocol in Linux.
Notes: This was mostly tested with Ardour in Linux. It may or may not work with other DAWs, I haven't tried this on a Windows PC.
Required python modules: python-osc, python-rtmidi. 

Features:
  Motorized faders are fully functional.
  Most buttons are functional.
  LCD screen output is supported however I haven't assigned it any functions as of yet. 
  Signal lights illuminate when a track signal is present..
  
 Issues / TODO:
  I'm working on making a config file to make assigning functions easier and customizable.
  I'm working on cleaning up the code, it's a bit messy at the moment.
  The mute / solo lights are not functional yet.
  Various buttons have yet to be assigned.
  
