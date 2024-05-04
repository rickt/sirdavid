# sirdavid
Have you ever wanted David Attenborough's voice to describe the contents of a webcam photo in pseudo-real time over a secure websocket? Why not indeed! 

index.html:
* takes a snapshot of the browser's webcam
* uploads it over secure websocket to a mini backend 

main.py:
* sets up a secure websocket listener
* looks for a .png sent over the websocket
* decodes the image, has it described in a snarky David Attenborough manner
* generates audio file using a custom ElevenLabs David Attenborough voice i created 
* plays the audio in the browser


