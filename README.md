# sirdavid
Have you ever wanted David Attenborough's voice to describe the contents of a webcam photo in pseudo-real time over a secure websocket? Why not indeed! 

## index.html:
* takes a snapshot of the browser's webcam
* uploads it over secure websocket to a mini backend 

## main.py:
* sets up a secure websocket listener
* looks for a .png sent over the websocket
* if an image arrives, saves it locally and in a GCP bucket
* decodes the image, has it described by OpenAI' <code>gpt4-vision-preview</code> model in a snarky David Attenborough manner
* generates audio file using a custom ElevenLabs David Attenborough voice i created 
* sends the URL of the audio file to the browser
* plays the audio in the browser

## Environment Variables:
You'll need to set:
* `ELEVENLABS_API_KEY` api key for [ElevenLabs](https://elevenlabs.io)
* `OPENAI_API_KEY` api key for OpenAI
* `SIRDAVID_BUCKET` name of GCP bucket to store images, text analyses & audio files
* `SIRDAVID_PORT` port for the websocket listener
* `SIRDAVID_SERVICEACCOUNT_JSON` path to [service account JSON](https://cloud.google.com/iam/docs/keys-create-delete) file for auth to GCP bucket
* `SIRDAVID_SSL_CERT` path to the SSL certificate for the secure websocket
* `SIRDAVID_SSL_KEY` path to the SSL key for the secure websocket certificate
* `SIRDAVID_VOICE` string containing the [voice ID](https://elevenlabs.io/docs/api-reference/get-voice) of the ElevenLabs voice

## Notes
* You will have to make your own ElevenLabs David Attenborough voice, as I can't share mine



